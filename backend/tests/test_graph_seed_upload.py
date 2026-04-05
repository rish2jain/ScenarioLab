"""Tests for seed upload (deferred entity extraction)."""

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app import main as main_module
from app.db.seeds import SeedRepository
from app.graph import router as graph_router
from app.graph.router import get_neo4j_client, get_seed_processor
from app.main import app


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
