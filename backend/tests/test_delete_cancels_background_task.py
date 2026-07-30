"""DELETE /api/simulations/{id} must cancel the in-flight background task."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.simulation import router as sim_router


@pytest.mark.asyncio
async def test_delete_cancels_background_task_before_engine_delete():
    sim_id = "sim-delete-cancel"

    async def _never_finishes() -> None:
        await asyncio.sleep(3600)

    task = asyncio.create_task(_never_finishes())
    sim_router._background_tasks[sim_id] = task

    try:
        with patch(
            "app.simulation.router.simulation_engine.delete_simulation",
            new=AsyncMock(return_value=True),
        ) as delete_mock:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.delete(f"/api/simulations/{sim_id}")

        assert r.status_code == 200
        assert r.json()["status"] == "deleted"
        delete_mock.assert_awaited_once_with(sim_id)
        assert task.cancelled() or task.done()
        assert sim_id not in sim_router._background_tasks
    finally:
        if not task.done():
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        sim_router._background_tasks.pop(sim_id, None)
