"""Custom persona delete outcomes: distinguish not-in-memory vs DB no-op."""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.personas.designer import (
    CustomPersonaConfig,
    CustomPersonaDeleteOutcome,
    PersonaDesigner,
)


@pytest.mark.asyncio
async def test_delete_not_found_in_memory():
    designer = PersonaDesigner()
    designer._initialized = True
    out = await designer.delete_custom_persona("nonexistent-id")
    assert out is CustomPersonaDeleteOutcome.NOT_FOUND_IN_MEMORY


@pytest.mark.asyncio
async def test_delete_not_found_in_database_warns_desync(caplog):
    designer = PersonaDesigner()
    designer._initialized = True
    designer._personas["pid"] = CustomPersonaConfig(
        id="pid",
        name="Test",
        role="Role",
    )
    with caplog.at_level(logging.WARNING):
        with patch(
            "app.personas.designer._delete_custom_persona",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch("app.personas.designer.persona_library.remove_custom_persona_from_cache") as rm:
                out = await designer.delete_custom_persona("pid")
    assert out is CustomPersonaDeleteOutcome.DELETED
    assert "pid" not in designer._personas
    rm.assert_called_once_with("pid")
    assert "DELETE matched no DB row" in caplog.text
    assert "reconciling caches" in caplog.text


@pytest.mark.asyncio
async def test_delete_deleted():
    designer = PersonaDesigner()
    designer._initialized = True
    designer._personas["pid"] = CustomPersonaConfig(
        id="pid",
        name="Test",
        role="Role",
    )
    with patch(
        "app.personas.designer._delete_custom_persona",
        new_callable=AsyncMock,
        return_value=True,
    ):
        with patch("app.personas.designer.persona_library.remove_custom_persona_from_cache") as rm:
            out = await designer.delete_custom_persona("pid")
    assert out is CustomPersonaDeleteOutcome.DELETED
    assert "pid" not in designer._personas
    rm.assert_called_once_with("pid")
