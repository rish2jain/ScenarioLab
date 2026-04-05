"""Graphiti temporal context graph (replaces Zep Cloud stub).

Uses a dedicated Neo4j database name (``neo4j_graphiti_database``) when set to
avoid colliding with ScenarioLab seed ``Entity`` nodes in the default DB.
Defaults to ``neo4j`` for single-DB dev; set ``NEO4J_GRAPHITI_DATABASE=graphiti``
and ``CREATE DATABASE graphiti`` when you want isolation.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.config import settings

if TYPE_CHECKING:
    from graphiti_core import Graphiti

logger = logging.getLogger(__name__)

_graphiti: Graphiti | None = None
_graphiti_lock = asyncio.Lock()

# Ingest is scheduled with ``create_task``; without coordination, a task can finish
# *after* ``delete_simulation_graph`` clears Neo4j and re-insert episodes for a
# deleted simulation. Tombstones + pending-task cancel/reap close that race.
_graphiti_tombstoned_group_ids: set[str] = set()
_pending_graphiti_ingest_tasks: dict[str, set[asyncio.Task]] = {}


def reset_graphiti_ingest_coordination_for_tests() -> None:
    """Clear tombstones and pending-task registry (pytest isolation)."""
    _graphiti_tombstoned_group_ids.clear()
    _pending_graphiti_ingest_tasks.clear()


def _tombstone_group_id(group_id: str) -> None:
    _graphiti_tombstoned_group_ids.add(group_id)


def _is_group_id_tombstoned(group_id: str) -> bool:
    return group_id in _graphiti_tombstoned_group_ids


def _register_pending_ingest_task(group_id: str, task: asyncio.Task) -> None:
    _pending_graphiti_ingest_tasks.setdefault(group_id, set()).add(task)


def _unregister_pending_ingest_task(group_id: str, task: asyncio.Task) -> None:
    pending = _pending_graphiti_ingest_tasks.get(group_id)
    if pending is None:
        return
    pending.discard(task)
    if not pending:
        _pending_graphiti_ingest_tasks.pop(group_id, None)


async def _cancel_pending_graphiti_ingests(group_id: str) -> None:
    """Cancel background ingest tasks for this simulation; wait until they exit."""
    tasks = list(_pending_graphiti_ingest_tasks.pop(group_id, set()))
    for t in tasks:
        if not t.done():
            t.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def get_graphiti() -> Graphiti | None:
    """Return the process-global Graphiti instance if startup succeeded."""
    return _graphiti


def _graphiti_openai_key() -> str:
    """API key for Graphiti's default OpenAI LLM + embedder."""
    if settings.graphiti_openai_api_key.strip():
        return settings.graphiti_openai_api_key.strip()
    if settings.llm_provider.lower() == "openai" and settings.llm_api_key.strip():
        return settings.llm_api_key.strip()
    return os.environ.get("OPENAI_API_KEY", "").strip()


async def start_graphiti() -> None:
    """Initialize Graphiti when ``graphiti_enabled`` and prerequisites are met."""
    global _graphiti  # noqa: PLW0603
    if not settings.graphiti_enabled:
        logger.info("Graphiti disabled (GRAPHITI_ENABLED=false)")
        return

    key = _graphiti_openai_key()
    if not key:
        logger.warning(
            "Graphiti enabled but no OpenAI API key: set GRAPHITI_OPENAI_API_KEY "
            "or LLM_PROVIDER=openai with LLM_API_KEY, or OPENAI_API_KEY"
        )
        return

    async with _graphiti_lock:
        if _graphiti is not None:
            return
        try:
            from graphiti_core import Graphiti
            from graphiti_core.driver.neo4j_driver import Neo4jDriver

            # Ensure Graphiti's default OpenAI clients see a key (only if unset).
            os.environ.setdefault("OPENAI_API_KEY", key)

            driver = Neo4jDriver(
                settings.neo4j_uri,
                settings.neo4j_user,
                settings.neo4j_password,
                database=settings.neo4j_graphiti_database,
            )
            client = Graphiti(graph_driver=driver, max_coroutines=settings.graphiti_max_coroutines)
            await client.build_indices_and_constraints(delete_existing=False)
            _graphiti = client
            logger.info(
                "Graphiti initialized (Neo4j database=%s)",
                settings.neo4j_graphiti_database,
            )
        except Exception:
            logger.exception("Graphiti startup failed; temporal graph disabled")
            _graphiti = None


async def stop_graphiti() -> None:
    """Close Graphiti / Neo4j driver on shutdown."""
    global _graphiti  # noqa: PLW0603
    async with _graphiti_lock:
        if _graphiti is None:
            return
        try:
            await _graphiti.close()
        except Exception:
            logger.exception("Graphiti shutdown error")
        finally:
            _graphiti = None


def format_round_episode_body(
    simulation_name: str,
    simulation_id: str,
    round_state: Any,
) -> str:
    """Build plain-text episode body from a completed round."""
    lines = [
        f"Simulation: {simulation_name or simulation_id}",
        f"Simulation ID: {simulation_id}",
        f"Round: {round_state.round_number}",
        f"Phase at end: {round_state.phase}",
        "",
        "Messages:",
    ]
    for m in round_state.messages:
        who = f"{m.agent_name} ({m.agent_role})"
        lines.append(f"- [{m.phase}] {who}: {m.content}")
    if round_state.decisions:
        lines.extend(["", "Decisions:", *[str(d) for d in round_state.decisions]])
    return "\n".join(lines)


async def ingest_round_episode(
    simulation_id: str,
    simulation_name: str,
    round_number: int,
    round_state: Any,
) -> None:
    """Add one Graphiti episode for a completed round (``group_id`` = simulation id)."""
    if _is_group_id_tombstoned(simulation_id):
        logger.debug("Graphiti ingest skipped (tombstoned): %s", simulation_id)
        return
    g = get_graphiti()
    if g is None:
        return
    from graphiti_core.nodes import EpisodeType

    body = format_round_episode_body(simulation_name, simulation_id, round_state)
    name = f"sim-{simulation_id}-round-{round_number}"
    if _is_group_id_tombstoned(simulation_id):
        logger.debug("Graphiti ingest skipped before add_episode (tombstoned): %s", simulation_id)
        return
    await g.add_episode(
        name=name,
        episode_body=body,
        source_description="scenariolab_simulation_round",
        reference_time=datetime.now(timezone.utc),
        source=EpisodeType.text,
        group_id=simulation_id,
    )
    logger.info("Graphiti episode ingested: %s", name)


def schedule_round_episode_ingest(
    simulation_id: str,
    simulation_name: str,
    round_number: int,
    round_state: Any,
) -> None:
    """Fire-and-forget ingestion so the simulation loop is not blocked by LLM work."""
    if not settings.graphiti_enabled:
        return
    if _is_group_id_tombstoned(simulation_id):
        return

    async def _run_wrapper() -> None:
        task = asyncio.current_task()
        assert task is not None
        _register_pending_ingest_task(simulation_id, task)
        try:
            await ingest_round_episode(simulation_id, simulation_name, round_number, round_state)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Graphiti ingest failed for simulation %s round %s",
                simulation_id,
                round_number,
            )
        finally:
            _unregister_pending_ingest_task(simulation_id, task)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run_wrapper())
    except RuntimeError:
        logger.warning(
            "schedule_round_episode_ingest: no running event loop; "
            "running Graphiti ingest in a daemon thread (asyncio.run)",
        )

        def _thread_target() -> None:
            try:
                asyncio.run(_run_wrapper())
            except Exception:
                logger.exception("Graphiti ingest failed in background thread")

        threading.Thread(
            target=_thread_target,
            daemon=True,
            name="graphiti-ingest",
        ).start()


def _driver_is_neo4j(driver: Any) -> bool:
    """True when Graphiti's driver is Neo4j (``GraphProvider.NEO4J`` or ``\"neo4j\"``)."""
    p = getattr(driver, "provider", None)
    if p is None:
        return False
    tag = getattr(p, "value", p)
    return str(tag).lower() == "neo4j"


async def _delete_neo4j_saga_nodes_by_group_id(driver: Any, group_id: str, batch_size: int = 100) -> None:
    """Delete Saga nodes Graphiti's ``Node.delete_by_group_id`` omits on Neo4j.

    Upstream Cypher only matches ``Entity|Episodic|Community``; each simulation
    partition also has ``Saga`` nodes keyed by ``group_id`` (see graphiti_core).
    """
    if not _driver_is_neo4j(driver):
        return
    query = """
            MATCH (n:Saga {group_id: $group_id})
            CALL (n) {
                DETACH DELETE n
            } IN TRANSACTIONS OF $batch_size ROWS
            """
    params = {"group_id": group_id, "batch_size": batch_size}
    execute_query = getattr(driver, "execute_query", None)
    if execute_query is None or not asyncio.iscoroutinefunction(execute_query):
        logger.warning(
            "_delete_neo4j_saga_nodes_by_group_id: Neo4j driver missing async execute_query; "
            "skipping Saga node cleanup for group_id=%s",
            group_id,
        )
        return
    await driver.execute_query(query, params=params)


async def delete_simulation_graph(simulation_id: str) -> None:
    """Remove all Graphiti nodes/edges for ``group_id`` == simulation id."""
    # Tombstone first so new ingests skip; cancel in-flight tasks before Neo4j delete.
    _tombstone_group_id(simulation_id)
    await _cancel_pending_graphiti_ingests(simulation_id)

    g = get_graphiti()
    if g is None:
        return
    try:
        from graphiti_core.nodes import Node

        await Node.delete_by_group_id(g.driver, simulation_id, batch_size=100)
        await _delete_neo4j_saga_nodes_by_group_id(g.driver, simulation_id, batch_size=100)
        logger.info("Graphiti deleted group_id=%s", simulation_id)
    except Exception:
        logger.exception("Graphiti delete_by_group_id failed for %s", simulation_id)


async def search_simulation_graph(simulation_id: str, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Hybrid search scoped to one simulation partition."""
    g = get_graphiti()
    if g is None:
        return []
    edges = await g.search(query, group_ids=[simulation_id], num_results=limit)
    out: list[dict[str, Any]] = []
    for e in edges:
        out.append(
            {
                "uuid": getattr(e, "uuid", None),
                "fact": getattr(e, "fact", None) or str(e),
                "valid_at": getattr(e, "valid_at", None),
                "invalid_at": getattr(e, "invalid_at", None),
            }
        )
    return out


async def graphiti_context_snippet(simulation_id: str, query_hint: str) -> str:
    """Short bullet list for agent prompts (when injection is enabled)."""
    if not query_hint.strip():
        return ""
    facts = await search_simulation_graph(simulation_id, query_hint, limit=5)
    if not facts:
        return ""
    lines = ["--- Temporal graph context (Graphiti, this simulation) ---"]
    for f in facts:
        fact = f.get("fact") or ""
        if fact:
            lines.append(f"- {fact}")
    return "\n".join(lines)
