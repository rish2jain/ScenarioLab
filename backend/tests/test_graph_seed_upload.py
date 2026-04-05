"""Tests for seed upload (deferred entity extraction)."""

import time

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app import main as main_module
from app.db.seeds import SeedRepository
from app.graph import router as graph_router
from app.graph.router import (
    _pending_upload_client_keys,
    get_neo4j_client,
    get_seed_processor,
    reset_pending_upload_client_keys_for_tests,
)
from app.graph.seed_processor import (
    SeedGraphCleanupError,
    SeedProcessor,
    is_seed_graph_tombstoned,
    reset_seed_graph_tombstones_for_tests,
)
from app.main import app


@pytest.fixture(autouse=True)
def _reset_seed_graph_tombstones() -> None:
    reset_seed_graph_tombstones_for_tests()
    reset_pending_upload_client_keys_for_tests()
    yield
    reset_seed_graph_tombstones_for_tests()
    reset_pending_upload_client_keys_for_tests()


async def cleanup_created_seed(sid: str) -> None:
    """Remove seed from in-memory graph store and SQLite (test teardown)."""
    get_seed_processor().get_store().pop(sid, None)
    await SeedRepository().delete(sid)


def test_graph_router_neo4j_matches_main_lifespan():
    """Router must use the connected client from startup, not an unconnected singleton."""
    with TestClient(app):
        assert get_neo4j_client() is main_module.neo4j_client


def test_upload_seed_returns_processing_and_defers_extraction(
    monkeypatch: pytest.MonkeyPatch,
):
    async def noop_extraction(_seed_id: str) -> None:
        return None

    monkeypatch.setattr(
        graph_router,
        "_run_entity_extraction_for_seed",
        noop_extraction,
    )

    files = {
        "file": ("note.md", b"# Hello\n\nShort seed text.", "text/markdown"),
    }
    with TestClient(app) as client:
        response = client.post("/api/seeds/upload", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processing"
    assert body["id"]


def test_list_seeds_includes_uploaded_seed(monkeypatch: pytest.MonkeyPatch):
    async def noop_extraction(_seed_id: str) -> None:
        return None

    monkeypatch.setattr(
        graph_router,
        "_run_entity_extraction_for_seed",
        noop_extraction,
    )

    files = {
        "file": ("listed.md", b"# Seed\n\ntext.", "text/markdown"),
    }
    with TestClient(app) as client:
        up = client.post("/api/seeds/upload", files=files)
        assert up.status_code == 200
        seed_id = up.json()["id"]

        listed = client.get("/api/seeds")
        assert listed.status_code == 200
        seeds = listed.json()["seeds"]
        assert any(s["id"] == seed_id for s in seeds)


@pytest.mark.asyncio
async def test_process_seeds_requeues_failed_extraction(
    monkeypatch: pytest.MonkeyPatch,
):
    """POST /api/seeds/process must re-run graph extraction for status=failed seeds."""

    async def noop_extraction(_seed_id: str) -> None:
        return None

    monkeypatch.setattr(
        graph_router,
        "_run_entity_extraction_for_seed",
        noop_extraction,
    )

    files = {
        "file": ("retry.md", b"# Retry\n\ntext.", "text/markdown"),
    }
    recorded: list[str] = []
    seed_id: str | None = None

    async def capture_retry(sid: str) -> None:
        recorded.append(sid)

    async with app.router.lifespan_context(app):
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                up = await client.post("/api/seeds/upload", files=files)
                assert up.status_code == 200
                seed_id = up.json()["id"]

                async def mark_failed() -> None:
                    await get_seed_processor().update_seed(
                        seed_id,
                        status="failed",
                        error_message="simulated extraction failure",
                    )

                await mark_failed()

                monkeypatch.setattr(
                    graph_router,
                    "_run_entity_extraction_for_seed",
                    capture_retry,
                )

                resp = await client.post("/api/seeds/process", json={"fileIds": [seed_id]})

            assert resp.status_code == 200
            body = resp.json()
            assert seed_id not in body.get("not_found", [])
            assert body.get("requeued") == []
            assert body.get("skipped") == []
            rows = {s["id"]: s for s in body["processed"]}
            assert rows[seed_id]["status"] == "processing"
            assert recorded == [seed_id]
        finally:
            if seed_id is not None:
                await cleanup_created_seed(seed_id)


@pytest.mark.asyncio
async def test_process_seeds_requeues_stuck_processing(
    monkeypatch: pytest.MonkeyPatch,
):
    """POST /api/seeds/process must re-queue extraction when status is still processing."""

    async def noop_extraction(_seed_id: str) -> None:
        return None

    monkeypatch.setattr(
        graph_router,
        "_run_entity_extraction_for_seed",
        noop_extraction,
    )
    recorded: list[str] = []

    async def capture_retry(sid: str) -> None:
        recorded.append(sid)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            up = await client.post(
                "/api/seeds/upload",
                files={
                    "file": (
                        "stuck.md",
                        b"# stuck\n\ntext.",
                        "text/markdown",
                    )
                },
            )
            assert up.status_code == 200
            seed_id = up.json()["id"]
            assert up.json()["status"] == "processing"

            monkeypatch.setattr(
                graph_router,
                "_run_entity_extraction_for_seed",
                capture_retry,
            )

            resp = await client.post("/api/seeds/process", json={"fileIds": [seed_id]})

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("processed") == []
        assert seed_id not in body.get("not_found", [])
        requeued = {s["id"]: s for s in body.get("requeued", [])}
        assert requeued[seed_id]["status"] == "processing"
        assert body.get("skipped") == []
        assert recorded == [seed_id]
        await cleanup_created_seed(seed_id)


@pytest.mark.asyncio
async def test_process_seeds_skips_already_processed(
    monkeypatch: pytest.MonkeyPatch,
):
    """POST /api/seeds/process must not re-enqueue seeds already processed."""

    async def noop_extraction(_seed_id: str) -> None:
        return None

    monkeypatch.setattr(
        graph_router,
        "_run_entity_extraction_for_seed",
        noop_extraction,
    )

    files = {
        "file": ("done.md", b"# Done\n\ntext.", "text/markdown"),
    }
    seed_id: str | None = None

    async with app.router.lifespan_context(app):
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                up = await client.post("/api/seeds/upload", files=files)
                assert up.status_code == 200
                seed_id = up.json()["id"]
                await get_seed_processor().update_seed(
                    seed_id,
                    status="processed",
                    entity_count=1,
                    relationship_count=0,
                )

                resp = await client.post("/api/seeds/process", json={"fileIds": [seed_id]})

            assert resp.status_code == 200
            body = resp.json()
            assert body.get("processed") == []
            assert body.get("requeued") == []
            skipped = body.get("skipped", [])
            assert any(s["id"] == seed_id and s["reason"] == "already_processed" for s in skipped)
        finally:
            if seed_id is not None:
                await cleanup_created_seed(seed_id)


@pytest.mark.asyncio
async def test_delete_seed_clears_neo4j_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deleting a seed must call Neo4j clear_graph for that seed_id when a client exists."""
    cleared: list[str] = []

    class MockNeo4j:
        is_connected = True

        async def clear_graph(self, seed_id: str) -> None:
            cleared.append(seed_id)

    monkeypatch.setattr(
        "app.graph.seed_processor.get_application_neo4j_client",
        lambda: MockNeo4j(),
    )

    async with app.router.lifespan_context(app):
        proc = SeedProcessor()
        seed = await proc.process_file("delme.md", b"# t\n", "text/markdown")
        sid = seed.id
        ok = await proc.delete_seed(sid)
        assert ok is True
        assert cleared == [sid]


@pytest.mark.asyncio
async def test_delete_seed_tombstones_graph_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: delete must tombstone before Neo4j clear so extraction cannot resurrect nodes."""

    class MockNeo4j:
        is_connected = True

        async def clear_graph(self, _seed_id: str) -> None:
            return None

    monkeypatch.setattr(
        "app.graph.seed_processor.get_application_neo4j_client",
        lambda: MockNeo4j(),
    )

    async with app.router.lifespan_context(app):
        proc = SeedProcessor()
        seed = await proc.process_file("tomb.md", b"# t\n", "text/markdown")
        sid = seed.id
        assert not is_seed_graph_tombstoned(sid)
        ok = await proc.delete_seed(sid)
        assert ok is True
        assert is_seed_graph_tombstoned(sid)


@pytest.mark.asyncio
async def test_delete_nonexistent_seed_no_tombstone(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ghost seed IDs must not register a graph tombstone (unbounded leak)."""

    class MockNeo4j:
        is_connected = True

        async def clear_graph(self, _seed_id: str) -> None:
            return None

    monkeypatch.setattr(
        "app.graph.seed_processor.get_application_neo4j_client",
        lambda: MockNeo4j(),
    )

    async with app.router.lifespan_context(app):
        proc = SeedProcessor()
        ghost = "00000000-0000-0000-0000-000000000099"
        assert not is_seed_graph_tombstoned(ghost)
        ok = await proc.delete_seed(ghost)
        assert ok is False
        assert not is_seed_graph_tombstoned(ghost)


@pytest.mark.asyncio
async def test_delete_seed_aborts_when_neo4j_clear_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """If Neo4j cleanup fails, the seed must remain in storage (no false success)."""

    class MockNeo4j:
        is_connected = True

        async def clear_graph(self, _seed_id: str) -> None:
            raise RuntimeError("neo4j unavailable")

    monkeypatch.setattr(
        "app.graph.seed_processor.get_application_neo4j_client",
        lambda: MockNeo4j(),
    )

    async with app.router.lifespan_context(app):
        proc = SeedProcessor()
        seed = await proc.process_file("keep.md", b"# t\n", "text/markdown")
        sid = seed.id
        with pytest.raises(SeedGraphCleanupError):
            await proc.delete_seed(sid)
        assert await proc.get_seed(sid) is not None
        assert not is_seed_graph_tombstoned(sid)
        await cleanup_created_seed(sid)


def test_delete_seed_route_503_when_neo4j_clear_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """DELETE /api/seeds/{id} must not report ok when graph cleanup fails."""

    class MockNeo4j:
        is_connected = True

        async def clear_graph(self, _seed_id: str) -> None:
            raise RuntimeError("neo4j unavailable")

    monkeypatch.setattr(
        "app.graph.seed_processor.get_application_neo4j_client",
        lambda: MockNeo4j(),
    )

    async def noop_extraction(_seed_id: str) -> None:
        return None

    monkeypatch.setattr(graph_router, "_run_entity_extraction_for_seed", noop_extraction)

    import asyncio

    with TestClient(app) as client:
        up = client.post(
            "/api/seeds/upload",
            files={"file": ("keep503.md", b"# k\n", "text/markdown")},
        )
        assert up.status_code == 200
        sid = up.json()["id"]
        d = client.delete(f"/api/seeds/{sid}")
        assert d.status_code == 503
        detail = d.json().get("detail", "")
        assert "Graph database cleanup" in str(detail)
        asyncio.run(cleanup_created_seed(sid))


@pytest.mark.asyncio
async def test_cancel_upload_by_client_id_deletes_pending_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /seeds/upload/cancel-by-client-id removes a seed while the upload key is pending."""

    async def noop_extraction(_seed_id: str) -> None:
        return None

    monkeypatch.setattr(
        graph_router,
        "_run_entity_extraction_for_seed",
        noop_extraction,
    )

    with TestClient(app) as client:
        up = client.post(
            "/api/seeds/upload",
            files={"file": ("cancel.md", b"# c\n", "text/markdown")},
        )
        assert up.status_code == 200
        sid = up.json()["id"]

    key = "file-manual-pending-key"
    _pending_upload_client_keys[key] = (sid, time.monotonic())

    with TestClient(app) as client:
        cancel = client.post(
            "/api/seeds/upload/cancel-by-client-id",
            json={"client_upload_id": key},
        )
        assert cancel.status_code == 200
        assert cancel.json() == {"ok": True, "deleted": True}
        assert await SeedRepository().get(sid) is None

    assert key not in _pending_upload_client_keys


def test_upload_x_client_upload_id_cleared_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful upload must drop the client key so cancel is a no-op afterward."""

    async def noop_extraction(_seed_id: str) -> None:
        return None

    monkeypatch.setattr(
        graph_router,
        "_run_entity_extraction_for_seed",
        noop_extraction,
    )

    client_key = "file-header-cleared-test"
    with TestClient(app) as client:
        up = client.post(
            "/api/seeds/upload",
            files={"file": ("hdr.md", b"# h\n", "text/markdown")},
            headers={"X-Client-Upload-Id": client_key},
        )
        assert up.status_code == 200
        seed_id = up.json()["id"]

    assert client_key in _pending_upload_client_keys

    with TestClient(app) as client:
        ack = client.post(
            "/api/seeds/upload/ack-client-id",
            json={"client_upload_id": client_key},
        )
        assert ack.status_code == 200
        assert client_key not in _pending_upload_client_keys

        cancel = client.post(
            "/api/seeds/upload/cancel-by-client-id",
            json={"client_upload_id": client_key},
        )
        assert cancel.status_code == 200
        assert cancel.json()["deleted"] is False
        del_resp = client.delete(f"/api/seeds/{seed_id}")
        assert del_resp.status_code == 200


@pytest.mark.asyncio
async def test_legacy_xls_rejected() -> None:
    async with app.router.lifespan_context(app):
        proc = SeedProcessor()
        seed = await proc.process_file("legacy.xls", b"\xd0\xcf\x11\xe0", "application/vnd.ms-excel")
        assert seed.status == "failed"
        assert seed.error_message is not None
        assert "Legacy Excel" in seed.error_message
        await SeedRepository().delete(seed.id)


@pytest.mark.asyncio
async def test_legacy_ppt_rejected() -> None:
    async with app.router.lifespan_context(app):
        proc = SeedProcessor()
        seed = await proc.process_file("legacy.ppt", b"\xd0\xcf\x11\xe0", "application/vnd.ms-powerpoint")
        assert seed.status == "failed"
        assert seed.error_message is not None
        assert "Legacy PowerPoint" in seed.error_message
        await SeedRepository().delete(seed.id)
