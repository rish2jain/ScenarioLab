"""Main simulation orchestrator."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.database import SimulationRepository
from app.graph.seed_processor import SeedProcessor
from app.llm.factory import get_llm_provider
from app.personas.library import get_archetype
from app.simulation.agent import SimulationAgent
from app.simulation.environments import get_environment
from app.simulation.memory_manager import SimulationMemoryManager
from app.simulation.models import (
    AgentConfig,
    RoundState,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)
from app.simulation.turn_rules import TurnManager
from app.simulation.visibility import VisibilityManager

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Main simulation orchestrator."""

    def __init__(self):
        self.simulations: dict[str, SimulationState] = {}  # In-memory store
        self.running_tasks: dict[str, bool] = {}  # Track running simulations
        self._agents: dict[str, list[SimulationAgent]] = {}  # sim_id -> agents
        self._memory_managers: dict[str, SimulationMemoryManager] = {}
        self._repo = SimulationRepository()
        self._lock = asyncio.Lock()  # Protects dict mutations from races

    async def create_simulation(
        self,
        config: SimulationConfig,
        graph_memory_manager=None,
    ) -> SimulationState:
        """Create a new simulation from config."""
        # Ensure config has ID
        if not config.id:
            config.id = str(uuid.uuid4())

        logger.info(f"Creating simulation: {config.name} ({config.id})")

        # Load seed documents and build context
        seed_context = await self._load_seed_context(config)

        # Initialize agents from config + archetypes
        agents = await self._initialize_agents(
            config.agents, seed_context=seed_context
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
        await self._repo.save(sim_state)

        # Initialize memory manager
        self._memory_managers[config.id] = SimulationMemoryManager(
            graph_memory_manager
        )

        logger.info(
            f"Simulation {config.id} created with {len(agents)} agents"
        )
        return sim_state

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
            return config.parameters.get("seed_material", "")

        processor = SeedProcessor()
        parts: list[str] = []

        for seed_id in all_ids:
            seed = await processor.get_seed(seed_id)
            if seed is None:
                logger.warning(f"Seed {seed_id} not found, skipping")
                continue

            content = seed.processed_content or seed.raw_content
            if content:
                header = f"--- Document: {seed.filename} ---"
                parts.append(f"{header}\n{content}")

        if not parts:
            return config.parameters.get("seed_material", "")

        return "\n\n".join(parts)

    async def _initialize_agents(
        self,
        agent_configs: list[AgentConfig],
        seed_context: str = "",
    ) -> list[SimulationAgent]:
        """Initialize simulation agents from configurations."""
        agents = []
        llm_provider = get_llm_provider()

        for config in agent_configs:
            # Get archetype
            archetype = get_archetype(config.archetype_id)
            if not archetype:
                logger.warning(
                    f"Archetype not found: {config.archetype_id}"
                )
                continue

            # Inject seed context into agent customization
            if seed_context:
                config = AgentConfig(
                    id=config.id,
                    name=config.name,
                    archetype_id=config.archetype_id,
                    customization={
                        **config.customization,
                        "seed_context": seed_context,
                    },
                )

            # Create agent
            agent = SimulationAgent(
                config=config,
                archetype=archetype,
                llm_provider=llm_provider,
                memory_manager=None,  # Will be set up later
            )

            agents.append(agent)

        return agents

    async def run_simulation(
        self,
        simulation_id: str,
        on_message=None,
    ):
        """Run the full simulation loop."""
        sim_state = self.simulations.get(simulation_id)
        if not sim_state:
            raise ValueError(f"Simulation not found: {simulation_id}")

        if sim_state.status == SimulationStatus.RUNNING:
            raise ValueError("Simulation is already running")

        # Mark as running
        sim_state.status = SimulationStatus.RUNNING
        self.running_tasks[simulation_id] = True

        agents = self._agents.get(simulation_id, [])
        memory_manager = self._memory_managers.get(simulation_id)

        # Set up environment
        env_class = get_environment(sim_state.config.environment_type)
        environment = env_class()

        # Set up visibility and turn managers
        visibility = VisibilityManager(sim_state.config.environment_type)
        visibility.register_agents(sim_state.agents)

        turn_manager = TurnManager(
            sim_state.config.environment_type,
            sim_state.agents,
        )

        logger.info(f"Starting simulation {simulation_id}")

        try:
            # Run rounds
            for round_num in range(1, sim_state.config.total_rounds + 1):
                if not self.running_tasks.get(simulation_id):
                    logger.info(f"Simulation {simulation_id} paused")
                    sim_state.status = SimulationStatus.PAUSED
                    return

                sim_state.current_round = round_num
                logger.info(f"Round {round_num} starting")

                # Run a round
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

                # Update agent stances
                for agent in agents:
                    for round_state in sim_state.rounds:
                        if round_state.round_number == round_num:
                            await agent.update_stance(round_state.messages)

                # Persist state after each round
                await self._repo.save(sim_state)

                # Small delay between rounds
                await asyncio.sleep(0.1)

            # Simulation complete
            sim_state.status = SimulationStatus.COMPLETED
            sim_state.results_summary = await self._compile_results(sim_state)
            await self._repo.save(sim_state)
            logger.info(f"Simulation {simulation_id} completed")

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

    async def pause_simulation(self, simulation_id: str):
        """Pause a running simulation."""
        if simulation_id in self.running_tasks:
            self.running_tasks[simulation_id] = False
            logger.info(f"Simulation {simulation_id} pause requested")

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
            await memory_manager.clear_memories(simulation_id)

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
