"""Deep-offset pagination for SimulationEngine.list_simulations."""

from unittest.mock import AsyncMock

import pytest

from app.simulation.engine import SimulationEngine


@pytest.mark.asyncio
async def test_list_simulations_deep_offset_beyond_repo_page_cap():
    """offset+limit > 200 must still return the requested page, not an empty slice."""
    engine = SimulationEngine()
    engine.simulations.clear()

    # 250 DB rows; higher updated_at = newer (sort desc).
    db_rows = [
        {
            "id": f"sim-{i:03d}",
            "name": f"Sim {i}",
            "status": "completed",
            "updated_at": f"2024-01-01T00:00:00.{250 - i:06d}+00:00",
            "environment_type": "boardroom",
            "current_round": 0,
            "total_rounds": 10,
            "agent_count": 1,
            "created_at": "2024-01-01T00:00:00+00:00",
        }
        for i in range(250)
    ]
    db_rows_sorted = sorted(db_rows, key=lambda s: s["updated_at"], reverse=True)

    async def list_page(*, limit=50, offset=0):
        if limit is None:
            return db_rows_sorted, 250
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        return db_rows_sorted[offset : offset + limit], 250

    engine._repo.list_page = AsyncMock(side_effect=list_page)

    result = await engine.list_simulations(limit=50, offset=200)

    assert result["total"] == 250
    assert result["limit"] == 50
    assert result["offset"] == 200
    assert len(result["items"]) == 50
    assert result["items"][0]["id"] == db_rows_sorted[200]["id"]
    # Deep page must request uncapped fetch (limit=None), not a 200-row cap from offset 0.
    engine._repo.list_page.assert_awaited()
    assert engine._repo.list_page.await_args.kwargs.get("limit") is None
