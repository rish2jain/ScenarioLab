"""FastAPI router for graph operations."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.graph.entity_extractor import EntityExtractor
from app.graph.graphiti_service import (
    get_graphiti,
    search_simulation_graph,
)
from app.graph.graphrag import GraphRAG
from app.graph.neo4j_client import (
    Neo4jClient,
    get_application_neo4j_client,
    is_application_neo4j_registered,
)
from app.graph.seed_processor import (
    SeedGraphCleanupError,
    SeedMaterial,
    SeedProcessor,
    is_seed_graph_tombstoned,
)
from app.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["graph"])

# Global instances (initialized on first use)
_seed_processor: Optional[SeedProcessor] = None
_entity_extractor: Optional[EntityExtractor] = None
_graphrag: Optional[GraphRAG] = None


# Serialize entity extraction per seed so duplicate background tasks (retry while
# running, stuck processing re-queue) do not corrupt Neo4j or double-charge LLM.
@dataclass
class _SeedExtractionLockEntry:
    """Per-seed lock plus last activity time for TTL eviction."""

    lock: asyncio.Lock
    last_used: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        self.last_used = time.monotonic()


_seed_extraction_locks: dict[str, _SeedExtractionLockEntry] = {}
_seed_extraction_locks_guard = asyncio.Lock()
_seed_extraction_cleanup_task: asyncio.Task[None] | None = None

# Maps ``X-Client-Upload-Id`` -> (server seed id, monotonic registered time).
# The key stays after a **successful** upload until the client POSTs ack-client-id (or TTL
# evicts the map entry without deleting the seed) so cancel-by-client-id still works if the
# browser aborts while reading the response body.
_pending_upload_client_keys: dict[str, tuple[str, float]] = {}
_MAX_CLIENT_UPLOAD_ID_LEN = 512
_PENDING_UPLOAD_CLIENT_KEY_TTL_SECONDS = 900.0

# During seed graph extraction, ``is_seed_graph_tombstoned`` is polled every N items
# instead of each Neo4j write to reduce overhead on large extractions.
_SEED_GRAPH_TOMBSTONE_CHECK_EVERY = 10


def _register_pending_upload_client_key(client_key: str, seed_id: str) -> None:
    if client_key:
        _pending_upload_client_keys[client_key] = (seed_id, time.monotonic())


def _pop_pending_upload_client_key(client_key: str) -> None:
    if client_key:
        _pending_upload_client_keys.pop(client_key, None)


def _evict_stale_pending_upload_client_keys() -> None:
    now = time.monotonic()
    stale = [
        k
        for k, (_, t0) in list(_pending_upload_client_keys.items())
        if now - t0 > _PENDING_UPLOAD_CLIENT_KEY_TTL_SECONDS
    ]
    for k in stale:
        _pending_upload_client_keys.pop(k, None)
    if stale:
        logger.debug("Evicted %d stale pending upload client key(s)", len(stale))


def reset_pending_upload_client_keys_for_tests() -> None:
    _pending_upload_client_keys.clear()


_neo4j_unregistered_logged: bool = False


async def _seed_extraction_locks_cleanup_loop() -> None:
    """Periodically drop idle lock entries older than the configured TTL."""
    while True:
        await asyncio.sleep(settings.graph_seed_extraction_lock_cleanup_interval_seconds)
        try:
            ttl = settings.graph_seed_extraction_lock_ttl_seconds
            now = time.monotonic()
            async with _seed_extraction_locks_guard:
                stale_ids: list[str] = []
                for sid, entry in list(_seed_extraction_locks.items()):
                    if now - entry.last_used <= ttl:
                        continue
                    if entry.lock.locked():
                        continue
                    stale_ids.append(sid)
                for sid in stale_ids:
                    del _seed_extraction_locks[sid]
                if stale_ids:
                    logger.debug(
                        "Evicted %d stale seed extraction lock(s) (TTL=%ss)",
                        len(stale_ids),
                        ttl,
                    )
            _evict_stale_pending_upload_client_keys()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("seed extraction lock cleanup iteration failed")


def start_seed_extraction_lock_cleanup_task() -> None:
    """Start background TTL eviction (idempotent). Call from app lifespan startup."""
    global _seed_extraction_cleanup_task  # noqa: PLW0603
    if _seed_extraction_cleanup_task is not None and not _seed_extraction_cleanup_task.done():
        return
    _seed_extraction_cleanup_task = asyncio.create_task(_seed_extraction_locks_cleanup_loop())


async def stop_seed_extraction_lock_cleanup_task() -> None:
    """Cancel background TTL eviction. Call from app lifespan shutdown."""
    global _seed_extraction_cleanup_task  # noqa: PLW0603
    t = _seed_extraction_cleanup_task
    if t is None:
        return
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass
    _seed_extraction_cleanup_task = None


async def _get_seed_extraction_lock(seed_id: str) -> asyncio.Lock:
    async with _seed_extraction_locks_guard:
        entry = _seed_extraction_locks.get(seed_id)
        if entry is None:
            entry = _SeedExtractionLockEntry(lock=asyncio.Lock())
            _seed_extraction_locks[seed_id] = entry
        entry.touch()
        return entry.lock


async def _release_seed_extraction_lock(seed_id: str) -> None:
    """Refresh last-used time after extraction finishes.

    Called from the ``finally`` of :func:`_run_entity_extraction_for_seed` after
    ``async with lock`` completes. Stale entries are removed by
    :func:`_seed_extraction_locks_cleanup_loop` when idle past the configured TTL.
    """
    async with _seed_extraction_locks_guard:
        entry = _seed_extraction_locks.get(seed_id)
        if entry is None:
            return
        entry.touch()


async def _purge_seed_extraction_lock(seed_id: str) -> None:
    """Remove per-seed extraction lock state when the seed is deleted."""
    async with _seed_extraction_locks_guard:
        _seed_extraction_locks.pop(seed_id, None)


def get_neo4j_client() -> Neo4jClient | None:
    """Return the Neo4j client connected at app startup.

    ``main`` registers the pool via :func:`register_application_neo4j_client`.
    When the app lifespan has not run (e.g. isolated imports), return ``None``;
    do not construct an unregistered :class:`Neo4jClient` without ``connect()``.
    """
    if is_application_neo4j_registered():
        return get_application_neo4j_client()
    global _neo4j_unregistered_logged
    if not _neo4j_unregistered_logged:
        logger.warning(
            "Neo4j application client is not registered (app lifespan did not run "
            "or register_application_neo4j_client was not called); returning None. "
            "Graph features require a connected client from startup."
        )
        _neo4j_unregistered_logged = True
    return None


def get_seed_processor() -> SeedProcessor:
    """Get or create seed processor singleton."""
    global _seed_processor
    if _seed_processor is None:
        _seed_processor = SeedProcessor()
    return _seed_processor


def get_entity_extractor() -> EntityExtractor:
    """Get or create entity extractor singleton."""
    global _entity_extractor
    if _entity_extractor is None:
        llm = get_llm_provider()
        _entity_extractor = EntityExtractor(llm)
    return _entity_extractor


def reset_graphrag_cache() -> None:
    """Drop cached :class:`GraphRAG` (e.g. Neo4j closed or app lifespan ended).

    The singleton must not outlive its :class:`~app.graph.neo4j_client.Neo4jClient`:
    after ``close()`` the client is disconnected and must not be reused.
    """
    global _graphrag
    _graphrag = None


def get_graphrag() -> GraphRAG:
    """Get or create GraphRAG singleton tied to the current app Neo4j client."""
    global _graphrag
    neo4j = get_neo4j_client()
    if _graphrag is not None:
        if neo4j is None or _graphrag.db is not neo4j or not neo4j.is_connected:
            _graphrag = None
    if _graphrag is None:
        if neo4j is None or not neo4j.is_connected:
            raise HTTPException(
                status_code=503,
                detail="Neo4j is not available; graph query requires Neo4j.",
            )
        llm = get_llm_provider()
        _graphrag = GraphRAG(neo4j, llm)
    return _graphrag


# Request/Response models


class SeedResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    status: str
    entity_count: int
    relationship_count: int
    error_message: Optional[str] = None


class SeedListResponse(BaseModel):
    seeds: list[SeedResponse]


class CancelUploadByClientIdRequest(BaseModel):
    client_upload_id: str = Field(..., min_length=1, max_length=512)


class CancelUploadByClientIdResponse(BaseModel):
    ok: bool
    deleted: bool


class AckUploadClientIdRequest(BaseModel):
    client_upload_id: str = Field(..., min_length=1, max_length=512)


class AckUploadClientIdResponse(BaseModel):
    ok: bool


class SkippedSeedEntry(BaseModel):
    """Seed skipped by POST /seeds/process (e.g. already graph-complete)."""

    id: str
    reason: str


class SeedProcessResponse(BaseModel):
    """Batch process/retry: ``processed`` (retries/other), ``requeued`` (stuck processing), ``skipped``."""

    processed: list[SeedResponse]
    requeued: list[SeedResponse] = Field(default_factory=list)
    skipped: list[SkippedSeedEntry] = Field(default_factory=list)
    count: int
    not_found: list[str] = Field(default_factory=list)


class GraphQueryRequest(BaseModel):
    question: str
    seed_id: Optional[str] = None
    max_depth: int = 2


class GraphQueryResponse(BaseModel):
    query: str
    entities: list[dict]
    relationships: list[dict]
    context: str


class GraphDataResponse(BaseModel):
    nodes: list[dict]
    relationships: list[dict]


class TemporalMemoryStatusResponse(BaseModel):
    """Graphiti temporal graph status (local Neo4j partition)."""

    graphiti_enabled: bool
    graphiti_ready: bool
    neo4j_graphiti_database: str
    message: str


class TemporalSearchRequest(BaseModel):
    simulation_id: str
    query: str
    limit: int = 8


class TemporalSearchResponse(BaseModel):
    simulation_id: str
    query: str
    facts: list[dict]


class SeedProcessRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    file_ids: list[str] = Field(
        ...,
        alias="fileIds",
        min_length=1,
        max_length=100,
    )


def _to_seed_response(seed: SeedMaterial) -> SeedResponse:
    return SeedResponse(
        id=seed.id,
        filename=seed.filename,
        content_type=seed.content_type,
        status=seed.status,
        entity_count=seed.entity_count,
        relationship_count=seed.relationship_count,
        error_message=seed.error_message,
    )


async def _abandon_seed_graph_writes_if_tombstoned(seed_id: str, neo4j: Neo4jClient) -> bool:
    """If the seed was deleted, clear this seed's Neo4j slice and return True (stop writing)."""
    if not is_seed_graph_tombstoned(seed_id):
        return False
    try:
        await neo4j.clear_graph(seed_id)
    except Exception:
        logger.exception("clear_graph after tombstone for seed %s", seed_id)
    logger.info("Stopped seed graph write (seed deleted): %s", seed_id)
    return True


async def _run_entity_extraction_for_seed(seed_id: str) -> None:
    """Chunk text, extract entities via LLM, write to Neo4j, persist seed counts.

    Runs after the HTTP response so long-running CLI/API LLM calls do not hit
    reverse-proxy or dev-server timeouts (e.g. Next.js rewrites closing the
    connection with ECONNRESET).
    """
    processor = get_seed_processor()
    neo4j = get_neo4j_client()

    if neo4j is None or not neo4j.is_connected:
        await processor.update_seed(
            seed_id,
            status="failed",
            error_message=(
                "Neo4j is not connected; seed graph extraction requires Neo4j. "
                "Start Neo4j and restart the backend, then use Process seeds to retry."
            ),
        )
        return

    lock = await _get_seed_extraction_lock(seed_id)
    try:
        async with lock:
            seed = await processor.get_seed(seed_id)
            if seed is None:
                logger.warning("Entity extraction skipped: seed %s not found", seed_id)
                return
            if seed.status == "processed":
                logger.info("Entity extraction skipped (already processed): seed %s", seed_id)
                return
            if seed.status != "processing":
                logger.warning(
                    "Entity extraction skipped: seed %s has status %s",
                    seed_id,
                    seed.status,
                )
                return
            if not seed.processed_content:
                await processor.update_seed(
                    seed_id,
                    status="failed",
                    error_message="No processed content for entity extraction",
                )
                return

            if await _abandon_seed_graph_writes_if_tombstoned(seed_id, neo4j):
                return

            try:
                extractor = get_entity_extractor()
                # Remove any partial graph from a previous failed run so retries do not duplicate nodes.
                await neo4j.clear_graph(seed_id)
                if await _abandon_seed_graph_writes_if_tombstoned(seed_id, neo4j):
                    return

                chunks = await processor.chunk_content(seed.processed_content, chunk_size=3000, overlap=300)
                extraction_result = await extractor.extract_from_chunks(chunks)

                still = await processor.get_seed(seed_id)
                if still is None or still.status != "processing":
                    logger.info(
                        "Entity extraction abandoned after LLM for seed %s "
                        "(deleted or status changed; skipping Neo4j write)",
                        seed_id,
                    )
                    return

                for idx, entity in enumerate(extraction_result.entities):
                    if idx % _SEED_GRAPH_TOMBSTONE_CHECK_EVERY == 0:
                        if await _abandon_seed_graph_writes_if_tombstoned(seed_id, neo4j):
                            return
                    node_props = {
                        **entity.properties,
                        "id": entity.id,
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "description": entity.description,
                        "seed_id": seed.id,
                    }
                    await neo4j.create_node("Entity", node_props)

                if await _abandon_seed_graph_writes_if_tombstoned(seed_id, neo4j):
                    return

                for idx, rel in enumerate(extraction_result.relationships):
                    if idx % _SEED_GRAPH_TOMBSTONE_CHECK_EVERY == 0:
                        if await _abandon_seed_graph_writes_if_tombstoned(seed_id, neo4j):
                            return
                    rel_props = {
                        **rel.properties,
                        "id": rel.id,
                        "relationship_type": rel.relationship_type,
                        "description": rel.description,
                        "weight": rel.weight,
                    }
                    await neo4j.create_relationship(
                        from_id=rel.source_entity_id,
                        to_id=rel.target_entity_id,
                        rel_type=rel.relationship_type.upper(),
                        properties=rel_props,
                    )

                if await _abandon_seed_graph_writes_if_tombstoned(seed_id, neo4j):
                    return

                final = await processor.get_seed(seed_id)
                if final is None or final.status != "processing":
                    logger.info(
                        "Entity extraction abandoned before persist for seed %s " "(deleted or status changed)",
                        seed_id,
                    )
                    return

                await processor.update_seed(
                    seed_id,
                    status="processed",
                    entity_count=len(extraction_result.entities),
                    relationship_count=len(extraction_result.relationships),
                    error_message=None,
                )

                logger.info(
                    "Built graph for seed %s: %s entities, %s relationships",
                    seed_id,
                    len(extraction_result.entities),
                    len(extraction_result.relationships),
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("Entity extraction failed for seed %s", seed_id)
                await processor.update_seed(seed_id, status="failed", error_message=str(e))
    finally:
        await _release_seed_extraction_lock(seed_id)


async def _cleanup_seed_on_disconnect(processor: SeedProcessor, seed_id: str, client_key: str) -> None:
    """Best-effort delete when the client disconnects; clear pending upload key."""
    try:
        await processor.delete_seed(seed_id)
    except SeedGraphCleanupError:
        logger.exception(
            "Disconnect cleanup: Neo4j clear failed for seed %s (seed kept)",
            seed_id,
        )
    _pop_pending_upload_client_key(client_key)


# Endpoints


@router.post("/seeds/upload", response_model=SeedResponse)
async def upload_seed_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload seed material file, process it, extract entities, build graph."""
    processor = get_seed_processor()

    # Read file content
    content = await file.read()
    if await request.is_disconnected():
        logger.info(
            "Seed upload discarded after read (client disconnected): %s",
            file.filename,
        )
        raise HTTPException(status_code=499, detail="Client closed connection")

    content_type = file.content_type or "text/plain"

    logger.info(f"Uploading file: {file.filename} ({content_type})")

    seed = await processor.process_file(file.filename, content, content_type)

    raw_key = (request.headers.get("x-client-upload-id") or "").strip()
    client_key = raw_key[:_MAX_CLIENT_UPLOAD_ID_LEN] if raw_key else ""
    if client_key:
        _register_pending_upload_client_key(client_key, seed.id)

    if await request.is_disconnected():
        await _cleanup_seed_on_disconnect(processor, seed.id, client_key)
        raise HTTPException(status_code=499, detail="Client closed connection")

    if seed.status == "failed":
        _pop_pending_upload_client_key(client_key)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process file: {seed.error_message}",
        )

    if seed.status == "processed" and seed.processed_content:
        updated = await processor.update_seed(seed.id, status="processing")
        if updated is None:
            logger.info(
                "Seed %s disappeared during upload (likely client cancel)",
                seed.id,
            )
            _pop_pending_upload_client_key(client_key)
            raise HTTPException(status_code=499, detail="Client closed connection")
        seed = updated
        background_tasks.add_task(_run_entity_extraction_for_seed, seed.id)

    if await request.is_disconnected():
        await _cleanup_seed_on_disconnect(processor, seed.id, client_key)
        raise HTTPException(status_code=499, detail="Client closed connection")

    return _to_seed_response(seed)


@router.post("/seeds/upload/ack-client-id", response_model=AckUploadClientIdResponse)
async def ack_upload_client_id(body: AckUploadClientIdRequest):
    """Drop the pending client key after the client read a successful upload response."""
    key = body.client_upload_id.strip()[:_MAX_CLIENT_UPLOAD_ID_LEN]
    _pop_pending_upload_client_key(key)
    return AckUploadClientIdResponse(ok=True)


@router.post("/seeds/upload/cancel-by-client-id", response_model=CancelUploadByClientIdResponse)
async def cancel_upload_by_client_id(body: CancelUploadByClientIdRequest):
    """Best-effort delete when the client aborted before reading the upload response."""
    key = body.client_upload_id.strip()[:_MAX_CLIENT_UPLOAD_ID_LEN]
    entry = _pending_upload_client_keys.pop(key, None)
    if entry is None:
        return CancelUploadByClientIdResponse(ok=True, deleted=False)
    seed_id = entry[0]
    processor = get_seed_processor()
    try:
        deleted = await processor.delete_seed(seed_id)
    except SeedGraphCleanupError:
        logger.exception(
            "cancel-by-client-id: Neo4j clear failed for seed %s (seed kept)",
            seed_id,
        )
        deleted = False
    return CancelUploadByClientIdResponse(ok=True, deleted=deleted)


@router.get("/seeds", response_model=SeedListResponse)
async def list_seeds():
    """List all uploaded seeds."""
    processor = get_seed_processor()
    seeds = await processor.list_seeds()

    return SeedListResponse(seeds=[_to_seed_response(s) for s in seeds])


@router.get("/seeds/{seed_id}", response_model=SeedResponse)
async def get_seed(seed_id: str):
    """Get seed material info and processing status."""
    processor = get_seed_processor()
    seed = await processor.get_seed(seed_id)

    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    return _to_seed_response(seed)


@router.delete("/seeds/{seed_id}")
async def delete_seed(seed_id: str):
    """Delete a single seed material."""
    processor = get_seed_processor()
    try:
        deleted = await processor.delete_seed(seed_id)
    except SeedGraphCleanupError as e:
        raise HTTPException(
            status_code=503,
            detail="Graph database cleanup failed; seed was not deleted. Retry shortly.",
        ) from e
    if not deleted:
        raise HTTPException(status_code=404, detail="Seed not found")
    await _purge_seed_extraction_lock(seed_id)
    return {"ok": True, "id": seed_id}


class SeedDeleteBatchRequest(BaseModel):
    """Request body for batch seed deletion."""

    ids: list[str]


@router.post("/seeds/delete-batch")
async def delete_seeds_batch(request: SeedDeleteBatchRequest):
    """Delete multiple seed materials at once."""
    processor = get_seed_processor()
    deleted: list[str] = []
    not_found: list[str] = []
    graph_cleanup_failed: list[str] = []
    for seed_id in request.ids:
        try:
            ok = await processor.delete_seed(seed_id)
        except SeedGraphCleanupError:
            logger.exception("Batch delete: Neo4j clear failed for seed %s", seed_id)
            graph_cleanup_failed.append(seed_id)
            continue
        if ok:
            deleted.append(seed_id)
            await _purge_seed_extraction_lock(seed_id)
        else:
            not_found.append(seed_id)
    return {
        "deleted": deleted,
        "not_found": not_found,
        "graph_cleanup_failed": graph_cleanup_failed,
    }


@router.post("/seeds/process", response_model=SeedProcessResponse)
async def process_uploaded_seeds(
    request: SeedProcessRequest,
    background_tasks: BackgroundTasks,
) -> SeedProcessResponse:
    """Compatibility endpoint for frontend seed processing flow.

    Seed uploads run file parsing on ``/seeds/upload`` and defer graph extraction.
    If extraction failed (status ``failed``) but text content exists, this route
    resets the seed to ``processing`` and re-runs entity extraction — this is
    the retry path for \"Process seeds\" after a graph build failure.

    If a seed is stuck in ``processing`` (lost background task, crash before the
    extraction try block, server restart), the same route re-queues extraction
    without changing status so the user can recover without re-uploading; those
    rows appear in ``requeued`` (pre-task snapshot) so clients know the outcome
    is still pending.

    Seeds already ``processed`` are returned in ``skipped`` with reason
    ``already_processed`` and are not listed in ``processed``.

    Seeds stuck in ``processing`` with no extractable text yet are returned in
    ``skipped`` with reason ``processing_no_text`` (not ``processed``).
    """
    processor = get_seed_processor()
    processed: list[SeedResponse] = []
    requeued: list[SeedResponse] = []
    skipped: list[SkippedSeedEntry] = []
    not_found: list[str] = []
    seeds = await asyncio.gather(*(processor.get_seed(seed_id) for seed_id in request.file_ids))

    for seed_id, seed in zip(request.file_ids, seeds):
        if seed is None:
            not_found.append(seed_id)
            continue

        has_text = (seed.processed_content and seed.processed_content.strip()) or (
            seed.raw_content and seed.raw_content.strip()
        )

        if seed.status == "processed":
            skipped.append(SkippedSeedEntry(id=seed_id, reason="already_processed"))
            continue

        if seed.status == "failed" and has_text:
            retry_updates: dict = {"status": "processing", "error_message": None}
            # No usable processed text yet, but raw upload text exists (promote raw to processed).
            has_only_raw_content = not (seed.processed_content or "").strip() and (seed.raw_content or "").strip()
            if has_only_raw_content:
                retry_updates["processed_content"] = seed.raw_content
            updated = await processor.update_seed(seed_id, **retry_updates)
            if updated is not None:
                seed = updated
                background_tasks.add_task(_run_entity_extraction_for_seed, seed_id)
            processed.append(_to_seed_response(seed))
            continue

        if seed.status == "processing" and has_text:
            background_tasks.add_task(_run_entity_extraction_for_seed, seed_id)
            requeued.append(_to_seed_response(seed))
            continue

        if seed.status == "processing" and not has_text:
            logger.info(
                "Skipping process for seed %s: status=processing but no text yet",
                seed_id,
            )
            skipped.append(SkippedSeedEntry(id=seed_id, reason="processing_no_text"))
            continue

        processed.append(_to_seed_response(seed))

    return SeedProcessResponse(
        processed=processed,
        requeued=requeued,
        skipped=skipped,
        count=len(processed) + len(requeued) + len(skipped),
        not_found=not_found,
    )


@router.get("/seeds/{seed_id}/graph", response_model=GraphDataResponse)
async def get_seed_graph(seed_id: str):
    """Get the knowledge graph for a seed (nodes + relationships)."""
    neo4j = get_neo4j_client()
    if neo4j is None or not neo4j.is_connected:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is not available; graph data requires Neo4j.",
        )
    processor = get_seed_processor()

    # Verify seed exists
    seed = await processor.get_seed(seed_id)
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    # Query Neo4j for entities with this seed_id
    entity_query = """
    MATCH (n {seed_id: $seed_id})
    RETURN n
    """
    entity_results = await neo4j.execute_query(entity_query, {"seed_id": seed_id})
    nodes = [dict(r["n"]) for r in entity_results]

    # Get relationships between these nodes
    node_ids = [n.get("id") for n in nodes]
    if node_ids:
        rel_query = """
        MATCH (a)-[r]->(b)
        WHERE a.id IN $node_ids AND b.id IN $node_ids
        RETURN r, startNode(r) as start, endNode(r) as end
        """
        rel_results = await neo4j.execute_query(rel_query, {"node_ids": node_ids})
        relationships = []
        for record in rel_results:
            rel = dict(record["r"])
            rel["source_entity_id"] = record["start"].get("id")
            rel["target_entity_id"] = record["end"].get("id")
            relationships.append(rel)
    else:
        relationships = []

    return GraphDataResponse(
        nodes=nodes,
        relationships=relationships,
    )


@router.post("/graph/query", response_model=GraphQueryResponse)
async def query_graph(request: GraphQueryRequest):
    """Query the graph with natural language (GraphRAG)."""
    graphrag = get_graphrag()

    try:
        result = await graphrag.query(
            question=request.question,
            seed_id=request.seed_id,
            max_depth=request.max_depth,
        )

        return GraphQueryResponse(
            query=result.query,
            entities=result.entities,
            relationships=result.relationships,
            context=result.context,
        )
    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/graph/temporal-memory-status", response_model=TemporalMemoryStatusResponse)
async def temporal_memory_status() -> TemporalMemoryStatusResponse:
    """Graphiti adapter status (enabled flag + client initialized at startup)."""
    g = get_graphiti()
    ready = g is not None
    if not settings.graphiti_enabled:
        msg = "Graphiti disabled. Set GRAPHITI_ENABLED=true and OpenAI credentials for Graphiti."
    elif not ready:
        msg = "Graphiti not initialized (missing OpenAI key, Neo4j error, or startup failure). " "See logs."
    else:
        msg = "Graphiti ready"
    return TemporalMemoryStatusResponse(
        graphiti_enabled=settings.graphiti_enabled,
        graphiti_ready=ready,
        neo4j_graphiti_database=settings.neo4j_graphiti_database,
        message=msg,
    )


@router.post("/graph/temporal/search", response_model=TemporalSearchResponse)
async def temporal_graph_search(request: TemporalSearchRequest) -> TemporalSearchResponse:
    """Hybrid search over Graphiti facts scoped to ``simulation_id`` (group_id)."""
    if not settings.graphiti_enabled or get_graphiti() is None:
        raise HTTPException(
            status_code=503,
            detail="Graphiti is not available",
        )
    facts = await search_simulation_graph(
        request.simulation_id,
        request.query,
        limit=max(1, min(request.limit, 25)),
    )
    return TemporalSearchResponse(
        simulation_id=request.simulation_id,
        query=request.query,
        facts=facts,
    )
