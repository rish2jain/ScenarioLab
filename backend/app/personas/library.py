"""Persona library manager for consulting archetypes."""

import asyncio
import logging
from typing import Any

from app.api_integrations.database import (
    custom_persona_repo,
    ensure_tables,
)
from app.personas.archetypes import (
    CONSULTING_ARCHETYPES,
    PLAYBOOK_ROLE_MAPPING,
    ArchetypeDefinition,
    GovernanceStyle,
)

logger = logging.getLogger(__name__)


class PersonaLibrary:
    """Manages consulting persona archetypes and custom personas."""

    def __init__(self):
        self._archetypes = CONSULTING_ARCHETYPES
        self._custom_personas: dict[str, ArchetypeDefinition] = {}
        self._playbook_mappings = PLAYBOOK_ROLE_MAPPING
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_loaded(self) -> None:
        """Ensure custom personas are loaded from database."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            try:
                await ensure_tables()
                personas = await custom_persona_repo.list_all()
                for persona_data in personas:
                    persona = ArchetypeDefinition(**persona_data)
                    self._custom_personas[persona.id] = persona
                self._initialized = True
                logger.info(f"Loaded {len(self._custom_personas)} custom personas " f"from database")
            except Exception as e:
                logger.warning(f"Failed to load custom personas from DB: {e}")

    def get_all_archetypes(self) -> list[ArchetypeDefinition]:
        """Get all available archetype definitions."""
        return list(self._archetypes.values())

    def get_archetype(self, archetype_id: str) -> ArchetypeDefinition | None:
        """Get a single archetype by ID."""
        return self._archetypes.get(archetype_id)

    def create_custom_persona(self, base_archetype_id: str, overrides: dict[str, Any]) -> ArchetypeDefinition:
        """Create a customized persona from a base archetype.

        Args:
            base_archetype_id: The ID of the base archetype
            overrides: Dictionary of fields to override

        Returns:
            A new customized ArchetypeDefinition

        Raises:
            ValueError: If base archetype not found
        """
        base = self.get_archetype(base_archetype_id)
        if not base:
            raise ValueError(f"Archetype not found: {base_archetype_id}")

        # Create a copy of base archetype data
        persona_data = base.model_dump()

        # Apply overrides
        for key, value in overrides.items():
            if key in persona_data:
                persona_data[key] = value

        # Generate a unique ID for the custom persona
        custom_id = overrides.get("id", f"{base_archetype_id}_custom")
        persona_data["id"] = custom_id

        custom_persona = ArchetypeDefinition(**persona_data)
        self._custom_personas[custom_id] = custom_persona

        # Persist to database (async fire-and-forget)
        asyncio.create_task(custom_persona_repo.save(custom_id, custom_persona.model_dump()))

        logger.info(f"Created custom persona: {custom_id} from {base_archetype_id}")
        return custom_persona

    def get_roster_for_playbook(self, playbook_id: str) -> list[dict[str, Any]]:
        """Get recommended persona roster for a playbook.

        Args:
            playbook_id: The playbook identifier

        Returns:
            List of roster entries with role, archetype, and customization
        """
        # Map playbook IDs to their typical rosters
        playbook_rosters: dict[str, list[dict]] = {
            "mna-culture-clash": [
                {"role": "Acquirer CEO", "archetype_id": "ceo", "count": 1},
                {"role": "Target CEO", "archetype_id": "ceo", "count": 1},
                {"role": "CFO", "archetype_id": "cfo", "count": 1},
                {"role": "HR Head", "archetype_id": "hr_head", "count": 1},
                {"role": "Strategy VP", "archetype_id": "strategy_vp", "count": 1},
                {"role": "Integration PMO", "archetype_id": "operations_head", "count": 1},
            ],
            "regulatory-shock-test": [
                {"role": "CEO", "archetype_id": "ceo", "count": 1},
                {"role": "General Counsel", "archetype_id": "general_counsel", "count": 1},
                {"role": "CRO", "archetype_id": "cro", "count": 1},
                {"role": "Chief Compliance Officer", "archetype_id": "general_counsel", "count": 1},
                {"role": "Regulator", "archetype_id": "regulator", "count": 1},
                {"role": "Board Member", "archetype_id": "board_member", "count": 1},
            ],
            "competitive-response": [
                {"role": "CEO", "archetype_id": "ceo", "count": 1},
                {"role": "Strategy VP", "archetype_id": "strategy_vp", "count": 1},
                {
                    "role": "Competitor Executive",
                    "archetype_id": "competitor_exec",
                    "count": 1,
                },
                {"role": "Market Analysts", "archetype_id": "competitor_exec", "count": 1},
                {"role": "Operations Head", "archetype_id": "operations_head", "count": 1},
                {"role": "CFO", "archetype_id": "cfo", "count": 1},
            ],
            "boardroom-rehearsal": [
                {
                    "role": "Board Chair",
                    "archetype_id": "board_member",
                    "count": 1,
                    "customization": {"governance_style": GovernanceStyle.CHAIR},
                },
                {
                    "role": "Independent Director",
                    "archetype_id": "board_member",
                    "count": 2,
                    "customization": {"governance_style": GovernanceStyle.INDEPENDENT},
                },
                {"role": "Activist Director", "archetype_id": "activist_investor", "count": 1},
                {"role": "CEO", "archetype_id": "ceo", "count": 1},
                {"role": "CFO", "archetype_id": "cfo", "count": 1},
                {"role": "General Counsel", "archetype_id": "general_counsel", "count": 1},
            ],
        }

        roster = playbook_rosters.get(playbook_id, [])

        # Validate power dynamics
        self._validate_roster_power_dynamics(roster)

        return roster

    def _validate_roster_power_dynamics(self, roster: list[dict]) -> bool:
        """Validate that a roster has realistic power dynamics.

        Args:
            roster: List of roster entries

        Returns:
            True if valid, raises ValueError otherwise
        """
        if not roster:
            return True

        # Count high-authority personas
        high_authority_count = 0
        total_count = 0

        for entry in roster:
            archetype_id = entry.get("archetype_id", "")
            count = entry.get("count", 1)
            total_count += count

            archetype = self.get_archetype(archetype_id)
            if archetype and archetype.authority_level >= 9:
                high_authority_count += count

        # Check that not all personas are authority 10
        if high_authority_count == total_count and total_count > 0:
            logger.warning("Roster has unrealistic power dynamics: all high authority")
            raise ValueError(
                "Roster validation failed: Cannot have all personas with authority >= 9. "
                "Include a mix of authority levels for realistic dynamics."
            )

        # Check for reasonable distribution
        if total_count > 0 and high_authority_count / total_count > 0.5:
            logger.warning("Roster has many high-authority personas")

        return True

    def resolve_playbook_role(self, role_name: str) -> tuple[str, dict] | None:
        """Resolve a playbook-specific role to a core archetype.

        Args:
            role_name: The playbook-specific role name

        Returns:
            Tuple of (archetype_id, customization_dict) or None
        """
        return self._playbook_mappings.get(role_name)

    def get_archetype_ids(self) -> list[str]:
        """Get list of all archetype IDs."""
        return list(self._archetypes.keys())

    def remove_custom_persona_from_cache(self, persona_id: str) -> None:
        """Drop cached custom persona if present (after DB delete or reconcile)."""
        self._custom_personas.pop(persona_id, None)


# Global library instance
persona_library = PersonaLibrary()


# Convenience functions
def get_all_archetypes() -> list[ArchetypeDefinition]:
    """Get all available archetype definitions."""
    return persona_library.get_all_archetypes()


def get_archetype(archetype_id: str) -> ArchetypeDefinition | None:
    """Get a single archetype by ID."""
    return persona_library.get_archetype(archetype_id)


def create_custom_persona(base_archetype_id: str, overrides: dict[str, Any]) -> ArchetypeDefinition:
    """Create a customized persona from a base archetype."""
    return persona_library.create_custom_persona(base_archetype_id, overrides)


def get_roster_for_playbook(playbook_id: str) -> list[dict[str, Any]]:
    """Get recommended persona roster for a playbook."""
    return persona_library.get_roster_for_playbook(playbook_id)
