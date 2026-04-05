"""Main simulation orchestrator."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.database import SimulationRepository
from app.graph.seed_processor import SeedProcessor
from app.llm.factory import get_llm_provider as _get_llm_provider
from app.llm.factory import get_local_llm_provider
from app.llm.inference_router import InferenceRouter
from app.personas.library import get_archetype
from app.simulation.agent import SimulationAgent
from app.simulation.audit_trail import AuditEventType, audit_manager
from app.simulation.environments import get_environment
from app.simulation.memory_manager import SimulationMemoryManager
from app.simulation.models import (
    AgentConfig,
    RoundState,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)
from app.simulation.objectives import (
    format_simulation_objective_for_prompt,
    stop_conditions_met,
)
from app.simulation.turn_rules import TurnManager
from app.simulation.visibility import VisibilityManager

logger = logging.getLogger(__name__)


def _wizard_bool(params: dict, key: str) -> bool:
    """Coerce wizard JSON booleans (or legacy strings) to bool."""
    v = params.get(key)
    if v is True:
        return True
    if isinstance(v, str) and v.lower() in ("1", "true", "yes"):
        return True
    return False


def _wizard_model_override(params: dict | None) -> str | None:
    if not params:
        return None
    m = params.get("model")
    if isinstance(m, str) and m.strip():
        return m.strip()
    return None


def _wizard_inference_params(params: dict | None) -> tuple[str, int]:
    """Resolve inference_mode and hybrid_cloud_rounds from wizard params or settings."""
    p = params or {}
    raw_mode = p.get("inference_mode")
    if raw_mode is None or (isinstance(raw_mode, str) and not str(raw_mode).strip()):
        mode = (settings.inference_mode or "cloud").strip().lower()
    else:
        mode = str(raw_mode).strip().lower()
    cr_raw = p.get("hybrid_cloud_rounds", settings.hybrid_cloud_rounds)
    try:
        cr = int(cr_raw)
    except (TypeError, ValueError):
        cr = int(settings.hybrid_cloud_rounds)
    return mode, max(0, cr)


class SimulationEngine:
    """Main simulation orchestrator."""

    def __init__(self):
        self.simulations: dict[str, SimulationState] = {}  # In-memory store
        self.running_tasks: dict[str, bool] = {}  # Track running simulations
        self._agents: dict[str, list[SimulationAgent]] = {}  # sim_id -> agents
        self._memory_managers: dict[str, SimulationMemoryManager] = {}
        self._repo = SimulationRepository()
        self._lock = asyncio.Lock()  # Protects dict mutations from races

    def get_agent_router(
        self, sim_id: str, agent_index: int = 0
    ) -> InferenceRouter | None:
        """Return the inference router for a runtime agent, or None if missing."""
        agents = self._agents.get(sim_id)
        if not agents:
            return None
        if agent_index < 0 or agent_index >= len(agents):
            return None
        return agents[agent_index].router

    async def create_simulation(
        self,
        config: SimulationConfig,
        graph_memory_manager=None,
        *,
        inference_router: InferenceRouter | None = None,
    ) -> SimulationState:
        """Create a new simulation from config."""
        # Ensure config has ID
        if not config.id:
            config.id = str(uuid.uuid4())

        logger.info(f"Creating simulation: {config.name} ({config.id})")

        if len(config.agents) > settings.simulation_max_agents:
            raise ValueError(
                f"Too many agents ({len(config.agents)}); "
                f"max is {settings.simulation_max_agents}"
            )

        # Auto-parse objective server-side when description exists but
        # parsedObjective was not supplied by the client.
        await self._ensure_parsed_objective(config)

        # Load seed documents and build context
        seed_context = await self._load_seed_context(config)
        external_research = self._build_external_research_context(config)

        # Initialize agents from config + archetypes
        agents = await self._initialize_agents(
            config.agents,
            seed_context=seed_context,
            external_research_context=external_research,
            simulation_config=config,
            inference_router=inference_router,
        )

        # Create simulation state
        sim_state = SimulationState(
            config=config,
            status=SimulationStatus.READY,
            agents=[agent.state for agent in agents],
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Store simulation in memory and persist to DB
        async with self._lock:
            self.simulations[config.id] = sim_state
            self._agents[config.id] = agents
        try:
            await self._repo.save(sim_state)
            self._memory_managers[config.id] = SimulationMemoryManager(
                graph_memory_manager
            )
        except BaseException:
            try:
                await self.delete_simulation(config.id)
            except Exception:
                logger.exception(
                    "Cleanup after failed create_simulation for %s left partial state",
                    config.id,
                )
            raise

        logger.info(
            f"Simulation {config.id} created with {len(agents)} agents"
        )
        return sim_state

    async def _ensure_parsed_objective(
        self,
        config: SimulationConfig,
    ) -> None:
        """Auto-parse the simulation objective if not already parsed.

        When the user provides a description but the frontend did not
        round-trip a ``parsedObjective``, parse it server-side so that
        agents always receive structured objective context.  Non-fatal:
        failures are logged but do not block simulation creation.
        """
        desc = (config.description or "").strip()
        if not desc:
            return

        params = config.parameters
        if (params.get("parsedObjective")
                or params.get("parsed_objective")):
            return  # already parsed by the client

        try:
            from app.simulation.objectives import parse_simulation_objective

            parsed = await parse_simulation_objective(desc)
            # Store as dict so format_simulation_objective_for_prompt picks it up
            config.parameters = {
                **params,
                "parsedObjective": parsed.model_dump(),
            }
            logger.info(
                "Auto-parsed objective for simulation %s: %s",
                config.id,
                parsed.summary[:100] if parsed.summary else "(no summary)",
            )
        except Exception:
            logger.exception(
                "Auto-parse objective failed for %s; agents will still "
                "receive the raw description",
                config.id,
            )

    async def _load_seed_context(
        self,
        config: SimulationConfig,
    ) -> str:
        """Load and combine seed document content for a simulation.

        Resolves seed_ids (and legacy seed_id) into a single
        context string that gets injected into agent prompts.
        """
        all_ids: list[str] = list(config.seed_ids)
        if config.seed_id and config.seed_id not in all_ids:
            all_ids.append(config.seed_id)

        if not all_ids:
            # Fall back to inline seed_material in parameters
            material = config.parameters.get("seed_material", "")
            if not isinstance(material, str):
                return ""
            ext = _wizard_bool(config.parameters or {}, "extended_seed_context")
            cap = 100_000 if ext else 24_000
            return material[:cap]

        processor = SeedProcessor()
        parts: list[str] = []
        ext = _wizard_bool(config.parameters or {}, "extended_seed_context")
        cap = 100_000 if ext else 24_000

        for seed_id in all_ids:
            seed = await processor.get_seed(seed_id)
            if seed is None:
                logger.warning(f"Seed {seed_id} not found, skipping")
                continue

            content = seed.processed_content or seed.raw_content
            if content:
                if len(content) > cap:
                    note = "\n\n[TRUNCATED]"
                    content = content[: max(0, cap - len(note))] + note
                header = f"--- Document: {seed.filename} ---"
                parts.append(f"{header}\n{content}")

        if not parts:
            return config.parameters.get("seed_material", "")

        return "\n\n".join(parts)

    def _build_external_research_context(self, config: SimulationConfig) -> str:
        """Format preflight evidence packs or inline research string."""
        params = config.parameters or {}
        direct = params.get("external_research_context")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        packs = params.get("preflight_evidence_packs")
        if not packs or not isinstance(packs, list):
            return ""
        lines: list[str] = [
            "=== EXTERNAL RESEARCH (ground claims in this section) ===",
        ]

        for i, p in enumerate(packs[:20], 1):
            if not isinstance(p, dict):
                continue
            name = p.get("entity_name", f"entity_{i}")
            syn = p.get("synthesis")
            if isinstance(syn, dict):
                json_str = json.dumps(syn, indent=2)
                if len(json_str) > 2500:
                    marker = " ... (truncated)"
                    syn_s = json_str[: max(0, 2500 - len(marker))] + marker
                else:
                    syn_s = json_str
            else:
                syn_s = str(syn)[:2500]
            lines.append(f"\n--- {name} ---\n{syn_s}")
            cites = p.get("citations") or []
            if isinstance(cites, list) and cites:
                lines.append("Sources:")
                for c in cites[:5]:
                    if isinstance(c, dict):
                        t = c.get("title") or c.get("source", "")
                        u = c.get("url", "")
                        lines.append(f"  - {t} {u}")
        return "\n".join(lines)

    async def _initialize_agents(
        self,
        agent_configs: list[AgentConfig],
        seed_context: str = "",
        external_research_context: str = "",
        *,
        simulation_config: SimulationConfig | None = None,
        inference_router: InferenceRouter | None = None,
    ) -> list[SimulationAgent]:
        """Initialize simulation agents from configurations."""
        agents = []
        mo = _wizard_model_override(
            simulation_config.parameters if simulation_config else None
        )
        params = simulation_config.parameters if simulation_config else None
        mode, cloud_rounds = _wizard_inference_params(params)

        if inference_router is not None:
            router = inference_router
        else:
            cloud = _get_llm_provider(model_override=mo)
            # Wizard `parameters.model` is the cloud model only — do not pass it to
            # the local tier (would send e.g. gpt-4o to Ollama). Local uses LOCAL_LLM_*.
            local = get_local_llm_provider()
            router = await InferenceRouter.create(
                cloud, local, mode, cloud_rounds
            )

        for config in agent_configs:
            # Get archetype
            archetype = get_archetype(config.archetype_id)
            if not archetype:
                logger.warning(
                    f"Archetype not found: {config.archetype_id}"
                )
                continue

            base_cust = dict(config.customization)
            if simulation_config is not None:
                ob = format_simulation_objective_for_prompt(
                    simulation_config.description,
                    simulation_config.parameters,
                )
                if ob:
                    existing = (base_cust.get("context") or "").strip()
                    base_cust["context"] = (
                        f"{existing}\n\n{ob}" if existing else ob
                    )

            # Inject seed + external research into agent customization
            extra: dict = {}
            if seed_context:
                extra["seed_context"] = seed_context
            if external_research_context:
                extra["external_research_context"] = external_research_context
            if extra:
                base_cust = {**base_cust, **extra}
            config = AgentConfig(
                id=config.id,
                name=config.name,
                archetype_id=config.archetype_id,
                customization=base_cust,
            )

            # Create agent
            agent = SimulationAgent(
                config=config,
                archetype=archetype,
                inference_router=router,
                memory_manager=None,  # Will be set up later
            )

            agents.append(agent)

        return agents

    def _bind_runtime_agents_to_simulation_state(
        self,
        sim_state: SimulationState,
        agents: list[SimulationAgent],
    ) -> None:
        """Single source of truth: SimulationAgent.state, exposed via sim_state.agents.

        After ``SimulationRepository.get``, ``sim_state.agents`` holds persisted
        stances/history while new :class:`SimulationAgent` instances start from
        defaults. Visibility/TurnManager use ``sim_state.agents``; phases use
        ``SimulationAgent`` — without this merge, resumed runs see stale
        positions in routing and fresh (wrong) prompts for stance-aware LLM
        turns, and the next save can drop updated stances.
        """
        if not agents:
            return
        persisted_by_id = {a.id: a for a in sim_state.agents}
        for agent in agents:
            p = persisted_by_id.get(agent.id)
            if p is None:
                continue
            agent.state.current_stance = p.current_stance
            agent.state.coalition_members = list(p.coalition_members)
            agent.state.vote_history = [dict(v) for v in p.vote_history]
        sim_state.agents = [a.state for a in agents]

    def _restore_hybrid_exemplars_after_rehydrate(
        self,
        sim_state: SimulationState,
        agents: list[SimulationAgent],
    ) -> None:
        """Reload hybrid cloud priming exemplars after DB reload (pause/resume, new process).

        In-memory routers lose :attr:`InferenceRouter._exemplars` when agents are
        recreated; :attr:`SimulationState.hybrid_exemplar_snapshot` restores them.
        """
        if not agents:
            return
        router = agents[0].router
        if router.mode != "hybrid" or router.local is None:
            return
        snap = sim_state.hybrid_exemplar_snapshot
        if snap:
            router.restore_exemplars(snap)
            return
        # Legacy saves without snapshot: rebuild from the cloud priming round only.
        _, cloud_rounds = _wizard_inference_params(sim_state.config.parameters)
        if cloud_rounds <= 0:
            return
        round_state = next(
            (r for r in sim_state.rounds if r.round_number == cloud_rounds),
            None,
        )
        if round_state is None:
            return
        paused_right_after_priming = len(sim_state.rounds) == cloud_rounds
        for agent in agents:
            ams = [
                m for m in round_state.messages if m.agent_id == agent.id
            ]
            stance: str | None = None
            if paused_right_after_priming:
                persisted = next(
                    (a for a in sim_state.agents if a.id == agent.id),
                    None,
                )
                if persisted is not None and persisted.current_stance:
                    stance = persisted.current_stance
            router.store_exemplar(agent.id, ams, stance_text=stance)
        sim_state.hybrid_exemplar_snapshot = router.snapshot_exemplars()

    async def run_simulation(
        self,
        simulation_id: str,
        on_message=None,
    ):
        """Run the full simulation loop."""
        loaded_from_repo = False
        sim_state = self.simulations.get(simulation_id)
        if not sim_state:
            loaded_from_repo = True
            # Try loading from DB and hydrating into memory
            sim_state = await self._repo.get(simulation_id)
            if sim_state:
                # Rehydrate agents from the saved config so that
                # self._agents[simulation_id] is always populated.
                rehydrated_agents = None
                if simulation_id not in self._agents:
                    seed_context = await self._load_seed_context(sim_state.config)
                    ext = self._build_external_research_context(sim_state.config)
                    rehydrated_agents = await self._initialize_agents(
                        sim_state.config.agents,
                        seed_context=seed_context,
                        external_research_context=ext,
                        simulation_config=sim_state.config,
                    )

                async with self._lock:
                    if (
                        rehydrated_agents is not None
                        and simulation_id not in self._agents
                    ):
                        self._agents[simulation_id] = rehydrated_agents

                    if simulation_id not in self._memory_managers:
                        self._memory_managers[simulation_id] = (
                            SimulationMemoryManager(None)
                        )

                    self.simulations[simulation_id] = sim_state
            else:
                raise ValueError(f"Simulation not found: {simulation_id}")

        if (
            self.running_tasks.get(simulation_id)
            and sim_state.status == SimulationStatus.RUNNING
        ):
            raise ValueError("Simulation is already running")

        # Mark as running
        sim_state.status = SimulationStatus.RUNNING
        self.running_tasks[simulation_id] = True

        # Audit: simulation started
        try:
            await audit_manager.log_event(
                simulation_id=simulation_id,
                event_type=AuditEventType.SIMULATION_START,
                actor="system",
                details={
                    "total_rounds": sim_state.config.total_rounds,
                    "agent_count": len(sim_state.agents),
                },
            )
        except Exception:
            logger.debug("audit log_event (start) failed", exc_info=True)

        agents = self._agents.get(simulation_id, [])
        if loaded_from_repo and agents:
            self._bind_runtime_agents_to_simulation_state(sim_state, agents)
            self._restore_hybrid_exemplars_after_rehydrate(sim_state, agents)
        memory_manager = self._memory_managers.get(simulation_id)

        # Set up environment
        env_class = get_environment(sim_state.config.environment_type)
        environment = env_class()
        setattr(environment, "_sim_config", sim_state.config)
        environment._memory_manager = memory_manager

        # Set up visibility and turn managers
        visibility = VisibilityManager(sim_state.config.environment_type)
        visibility.register_agents(sim_state.agents)

        turn_manager = TurnManager(
            sim_state.config.environment_type,
            sim_state.agents,
        )

        logger.info(f"Starting simulation {simulation_id}")

        try:
            # Determine start_round to support resuming paused simulations correctly
            start_round = len(sim_state.rounds) + 1

            # Run rounds
            for round_num in range(start_round, sim_state.config.total_rounds + 1):
                if not self.running_tasks.get(simulation_id):
                    # stop_simulation sets CANCELLED; pause_simulation sets PAUSED.
                    # Do not overwrite CANCELLED with PAUSED (user abort vs pause).
                    if sim_state.status == SimulationStatus.CANCELLED:
                        sim_state.updated_at = datetime.now(timezone.utc).isoformat()
                        await self._repo.save(sim_state)
                        return
                    logger.info(f"Simulation {simulation_id} paused")
                    sim_state.status = SimulationStatus.PAUSED
                    sim_state.updated_at = datetime.now(timezone.utc).isoformat()
                    # PAUSED + rounds; complements pause_simulation's save on races.
                    await self._repo.save(sim_state)
                    return

                sim_state.current_round = round_num
                logger.info(f"Round {round_num} starting")

                # Run a round (optional wall-clock cap per round)
                timeout_s = settings.simulation_round_timeout_seconds
                if timeout_s and timeout_s > 0:
                    try:
                        await asyncio.wait_for(
                            self._run_round(
                                sim_state=sim_state,
                                round_number=round_num,
                                environment=environment,
                                agents=agents,
                                visibility=visibility,
                                turn_manager=turn_manager,
                                on_message=on_message,
                            ),
                            timeout=float(timeout_s),
                        )
                    except TimeoutError:
                        logger.error(
                            "Simulation %s round %s exceeded %ss timeout",
                            simulation_id,
                            round_num,
                            timeout_s,
                        )
                        raise RuntimeError(
                            f"Round {round_num} timed out after {timeout_s}s"
                        ) from None
                else:
                    await self._run_round(
                        sim_state=sim_state,
                        round_number=round_num,
                        environment=environment,
                        agents=agents,
                        visibility=visibility,
                        turn_manager=turn_manager,
                        on_message=on_message,
                    )

                # Record memories after round
                if memory_manager:
                    for round_state in sim_state.rounds:
                        if round_state.round_number == round_num:
                            await memory_manager.record_round(
                                simulation_id=simulation_id,
                                round_state=round_state,
                                agents=agents,
                            )

                # Update agent stances; hybrid cloud priming exemplars → snapshot for resume
                round_state = next(
                    (r for r in sim_state.rounds if r.round_number == round_num),
                    None,
                )
                if round_state is not None:
                    for agent in agents:
                        await agent.update_stance(
                            round_state.messages,
                            round_number=round_num,
                        )
                    if agents:
                        router = agents[0].router
                        if (
                            router.mode == "hybrid"
                            and router.local is not None
                            and round_num == router.cloud_rounds
                        ):
                            for agent in agents:
                                ams = [
                                    m
                                    for m in round_state.messages
                                    if m.agent_id == agent.id
                                ]
                                router.store_exemplar(
                                    agent.id,
                                    ams,
                                    stance_text=agent.state.current_stance,
                                )
                            sim_state.hybrid_exemplar_snapshot = (
                                router.snapshot_exemplars()
                            )

                # Persist the same AgentState objects the runtime agents mutate
                sim_state.agents = [a.state for a in agents]

                # Always persist after each round; gating on running_tasks skipped the
                # save when pause raced, losing the last round from DB before resume.
                await self._repo.save(sim_state)

                if stop_conditions_met(
                    sim_state.config.parameters, sim_state.rounds
                ):
                    logger.info(
                        "Simulation %s: stop conditions met after round %s",
                        simulation_id,
                        round_num,
                    )
                    break

                # Small delay between rounds
                await asyncio.sleep(0.1)

            # Natural finish only if still running — stop_simulation may have set CANCELLED
            # during the last round; never overwrite that with COMPLETED.
            if sim_state.status != SimulationStatus.RUNNING:
                sim_state.updated_at = datetime.now(timezone.utc).isoformat()
                await self._repo.save(sim_state)
                return

            # Rounds done — compile results and generate post-run artifacts
            sim_state.results_summary = await self._compile_results(sim_state)

            # Signal that report generation is in progress
            sim_state.status = SimulationStatus.GENERATING_REPORT
            sim_state.updated_at = datetime.now(timezone.utc).isoformat()
            await self._repo.save(sim_state)

            # Run MC first so report can reference variance data
            await self._maybe_run_inline_monte_carlo(sim_state)
            await self._maybe_post_run_artifacts(sim_state)

            # Now truly complete
            sim_state.status = SimulationStatus.COMPLETED
            await self._repo.save(sim_state)
            logger.info(f"Simulation {simulation_id} completed")

            # Audit: simulation completed
            try:
                await audit_manager.log_event(
                    simulation_id=simulation_id,
                    event_type=AuditEventType.SIMULATION_COMPLETE,
                    actor="system",
                    details={
                        "rounds_completed": sim_state.current_round,
                        "agent_count": len(sim_state.agents),
                    },
                )
            except Exception:
                logger.debug("audit log_event (complete) failed", exc_info=True)

        except Exception as e:
            logger.error(f"Simulation {simulation_id} failed: {e}")
            sim_state.status = SimulationStatus.FAILED
            sim_state.results_summary = {"error": str(e)}
            await self._repo.save(sim_state)

        finally:
            self.running_tasks[simulation_id] = False

    async def _run_round(
        self,
        sim_state: SimulationState,
        round_number: int,
        environment,
        agents: list[SimulationAgent],
        visibility: VisibilityManager,
        turn_manager: TurnManager,
        on_message=None,
    ):
        """Run a single round."""
        # Create round state using the passed environment instance
        first_phase = environment.get_first_phase()
        round_state = RoundState(
            round_number=round_number,
            phase=first_phase,
        )

        # Run each phase in the round
        current_phase = first_phase
        while current_phase:
            sim_state.current_phase = current_phase

            # Run the phase
            round_state = await environment.run_phase(
                phase=current_phase,
                round_number=round_number,
                agents=agents,
                visibility=visibility,
                turn_manager=turn_manager,
                round_state=round_state,
            )

            # Send messages via callback
            if on_message:
                for msg in round_state.messages:
                    if (msg.round_number == round_number
                            and msg.phase == current_phase):
                        await on_message(msg)

            # Move to next phase
            current_phase = environment.get_next_phase(current_phase)

            # Small delay between phases
            await asyncio.sleep(0.05)

        # Evaluate round
        round_evaluation = await environment.evaluate_round(round_state)
        round_state.decisions.append({"evaluation": round_evaluation})

        # Store round state
        sim_state.rounds.append(round_state)
        sim_state.updated_at = datetime.now(timezone.utc).isoformat()

        # Audit: round completed
        try:
            await audit_manager.log_event(
                simulation_id=sim_state.config.id,
                event_type=AuditEventType.AGENT_DECISION,
                actor="system",
                details={
                    "round": round_number,
                    "messages": len(round_state.messages),
                    "decisions": len(round_state.decisions),
                },
            )
        except Exception:
            logger.debug("audit log_event (round) failed", exc_info=True)

    async def _compile_results(self, sim_state: SimulationState) -> dict:
        """Compile final results summary."""
        results = {
            "simulation_id": sim_state.config.id,
            "name": sim_state.config.name,
            "total_rounds": sim_state.current_round,
            "total_messages": sum(len(r.messages) for r in sim_state.rounds),
            "environment": sim_state.config.environment_type.value,
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "archetype": a.archetype_id,
                    "final_stance": a.current_stance,
                }
                for a in sim_state.agents
            ],
            "rounds": [],
        }

        # Summarize each round
        for round_state in sim_state.rounds:
            round_summary = {
                "round_number": round_state.round_number,
                "phase": round_state.phase,
                "message_count": len(round_state.messages),
                "decisions": round_state.decisions,
            }
            results["rounds"].append(round_summary)

        return results

    async def _maybe_post_run_artifacts(self, sim_state: SimulationState) -> None:
        """Honor wizard flags: analytics and/or consulting report after completion."""
        params = sim_state.config.parameters or {}
        rs = dict(sim_state.results_summary or {})
        mo = _wizard_model_override(params)

        if _wizard_bool(params, "include_post_run_analytics"):
            try:
                from app.analytics.analytics_agent import AnalyticsAgent

                aa = AnalyticsAgent(
                    llm_provider=_get_llm_provider(model_override=mo),
                )
                metrics = await aa.analyze_simulation(sim_state)
                rs["post_run_analytics"] = metrics.model_dump(mode="json")
            except Exception as e:
                logger.exception(
                    "Post-run analytics failed for %s",
                    sim_state.config.id,
                )
                rs["post_run_analytics"] = {"error": str(e)}

        if _wizard_bool(params, "include_post_run_report"):
            try:
                from app.reports.report_agent import ReportAgent

                ra = ReportAgent(
                    _get_llm_provider(model_override=mo),
                    sim_state,
                )
                report = await ra.generate_full_report()
                rs["post_run_report"] = report.model_dump(mode="json")
            except Exception as e:
                logger.exception(
                    "Post-run report failed for %s",
                    sim_state.config.id,
                )
                rs["post_run_report"] = {"error": str(e)}

        sim_state.results_summary = rs

    async def _maybe_run_inline_monte_carlo(self, primary: SimulationState) -> None:
        """When wizard enables MC, run statistical batch after the primary sim."""
        params = primary.config.parameters or {}
        if not _wizard_bool(params, "inline_monte_carlo"):
            return
        requested = int(params.get("monte_carlo_iterations") or 1)
        if requested <= 1:
            return
        cap = settings.inline_monte_carlo_max_iterations
        effective = min(requested, cap)
        if requested > cap:
            logger.warning(
                "Inline Monte Carlo iterations capped from %s to %s "
                "(inline_monte_carlo_max_iterations=%s)",
                requested,
                effective,
                cap,
            )
        n = effective
        base = primary.config.model_copy(deep=True)
        np = dict(base.parameters or {})
        np.pop("inline_monte_carlo", None)
        np["include_post_run_report"] = False
        np["include_post_run_analytics"] = False
        np["monte_carlo_iterations"] = 1
        base.parameters = np
        try:
            from app.simulation.monte_carlo import MonteCarloConfig, MonteCarloRunner

            runner = MonteCarloRunner(self)
            result = await runner.run(
                MonteCarloConfig(base_config=base, iterations=n)
            )
            rs = dict(primary.results_summary or {})
            mc_out = result.model_dump(mode="json")
            mc_out["requested_iterations"] = requested
            mc_out["effective_iterations"] = n
            mc_out["iterations_capped"] = requested > cap
            rs["inline_monte_carlo"] = mc_out
            primary.results_summary = rs
        except Exception as e:
            logger.exception(
                "Inline Monte Carlo failed for %s",
                primary.config.id,
            )
            rs = dict(primary.results_summary or {})
            rs["inline_monte_carlo"] = {"error": str(e)}
            primary.results_summary = rs

    async def pause_simulation(self, simulation_id: str):
        """Pause a running simulation."""
        if simulation_id in self.running_tasks:
            self.running_tasks[simulation_id] = False
        # Immediately update status to PAUSED so the frontend sees it right away
        sim_state = self.simulations.get(simulation_id)
        if sim_state and sim_state.status == SimulationStatus.RUNNING:
            sim_state.status = SimulationStatus.PAUSED
            sim_state.updated_at = datetime.now(timezone.utc).isoformat()
            await self._repo.save(sim_state)
        logger.info(f"Simulation {simulation_id} paused")
        try:
            await audit_manager.log_event(
                simulation_id=simulation_id,
                event_type=AuditEventType.SIMULATION_PAUSE,
                actor="user",
                details={"round": sim_state.current_round if sim_state else 0},
            )
        except Exception:
            logger.debug("audit log_event (pause) failed", exc_info=True)

    async def stop_simulation(self, simulation_id: str) -> bool:
        """Stop a running simulation and mark it cancelled (user abort).

        Natural completion (all rounds) is only set inside ``run_simulation`` as
        COMPLETED. A user stop is never COMPLETED — partial progress stays in
        ``rounds`` / ``results_summary`` but status is CANCELLED.
        """
        sim_state = self.simulations.get(simulation_id)
        if not sim_state:
            sim_state = await self._repo.get(simulation_id)
            if not sim_state:
                return False
            async with self._lock:
                self.simulations[simulation_id] = sim_state

        # Stop the background task if running
        if self.running_tasks.get(simulation_id):
            self.running_tasks[simulation_id] = False

        if sim_state.status in (
            SimulationStatus.COMPLETED,
            SimulationStatus.FAILED,
            SimulationStatus.CANCELLED,
        ):
            logger.info(
                "Simulation %s already terminal (%s); stop is a no-op",
                simulation_id,
                sim_state.status,
            )
            return True

        sim_state.updated_at = datetime.now(timezone.utc).isoformat()

        sim_state.status = SimulationStatus.CANCELLED
        if not sim_state.results_summary:
            if sim_state.rounds:
                sim_state.results_summary = await self._compile_results(sim_state)
            else:
                sim_state.results_summary = {}
        logger.info(
            "Simulation %s stopped by user; marked cancelled (rounds=%s)",
            simulation_id,
            len(sim_state.rounds),
        )

        await self._repo.save(sim_state)
        return True

    async def resume_simulation(self, simulation_id: str):
        """Resume a paused simulation."""
        sim_state = self.simulations.get(simulation_id)
        if not sim_state:
            raise ValueError(f"Simulation not found: {simulation_id}")

        if sim_state.status != SimulationStatus.PAUSED:
            raise ValueError("Simulation is not paused")

        # Resume from current round
        logger.info(f"Resuming simulation {simulation_id}")
        await self.run_simulation(simulation_id)

    async def get_simulation(
        self, simulation_id: str
    ) -> SimulationState | None:
        """Get simulation state (in-memory first, then DB fallback)."""
        in_memory = self.simulations.get(simulation_id)
        if in_memory is not None:
            return in_memory
        return await self._repo.get(simulation_id)

    async def list_simulations(self) -> list[dict]:
        """List all simulations (merge in-memory running + DB stored)."""
        # Build in-memory summaries keyed by id
        in_memory: dict[str, dict] = {}
        for sim_id, sim_state in self.simulations.items():
            in_memory[sim_id] = {
                "id": sim_id,
                "name": sim_state.config.name,
                "status": sim_state.status.value,
                "environment_type": sim_state.config.environment_type.value,
                "current_round": sim_state.current_round,
                "total_rounds": sim_state.config.total_rounds,
                "agent_count": len(sim_state.agents),
                "created_at": sim_state.created_at,
                "updated_at": sim_state.updated_at,
            }

        # Fetch DB records, preferring in-memory versions for running sims
        db_summaries = await self._repo.list_all()
        merged: dict[str, dict] = {}
        for summary in db_summaries:
            sid = summary["id"]
            merged[sid] = in_memory.pop(sid, summary)

        # Add any in-memory-only entries (shouldn't happen, but be safe)
        merged.update(in_memory)

        return list(merged.values())

    async def delete_simulation(self, simulation_id: str) -> bool:
        """Delete a simulation from memory and database."""
        in_memory = simulation_id in self.simulations
        db_deleted = await self._repo.delete(simulation_id)

        if not in_memory and not db_deleted:
            return False

        # Stop if running
        if self.running_tasks.get(simulation_id):
            self.running_tasks[simulation_id] = False

        # Clean up memory
        memory_manager = self._memory_managers.get(simulation_id)
        if memory_manager:
            try:
                await memory_manager.clear_memories(simulation_id)
            except Exception:
                logger.exception(
                    "clear_memories failed during delete for %s; continuing cleanup",
                    simulation_id,
                )

        # Remove from in-memory storage (under lock)
        async with self._lock:
            self.simulations.pop(simulation_id, None)
            self._agents.pop(simulation_id, None)
            self._memory_managers.pop(simulation_id, None)
            self.running_tasks.pop(simulation_id, None)

        logger.info(f"Deleted simulation {simulation_id}")
        return True


# Global engine instance
simulation_engine = SimulationEngine()
