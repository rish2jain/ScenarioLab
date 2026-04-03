"""Playbook manager for loading and managing simulation templates."""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Path to templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


class AgentRosterEntry(BaseModel):
    """An entry in the playbook agent roster."""
    role: str
    archetype_id: str
    count: int = 1
    customization: dict[str, Any] = Field(default_factory=dict)


class SeedMaterialTemplate(BaseModel):
    """Template for required and optional seed materials."""
    required: list[str]
    optional: list[str]


class VisibilityRules(BaseModel):
    """Visibility rules for the simulation environment."""
    information_asymmetry: bool = False


class EnvironmentConfig(BaseModel):
    """Environment configuration for the simulation."""
    visibility_rules: dict[str, Any] = Field(default_factory=dict)
    decision_mechanism: str = ""
    escalation_trigger: str = ""
    time_pressure: str = ""
    coalition_dynamics: str = ""
    governance_constraints: str = ""


class PlaybookConfig(BaseModel):
    """Complete playbook configuration."""
    id: str
    name: str
    description: str
    category: str
    typical_duration_rounds: list[int]
    estimated_time_minutes: int
    environment: str
    agent_roster: list[AgentRosterEntry]
    round_structure: list[str]
    seed_material_template: SeedMaterialTemplate
    expected_deliverables: list[str]
    environment_config: EnvironmentConfig

    @field_validator("typical_duration_rounds")
    @classmethod
    def validate_duration_rounds(cls, v: list[int]) -> list[int]:
        """Validate that duration rounds has min and max."""
        if len(v) != 2:
            raise ValueError("typical_duration_rounds must have exactly 2 values [min, max]")
        if v[0] > v[1]:
            raise ValueError("First value (min) must be <= second value (max)")
        return v


class PlaybookSummary(BaseModel):
    """Summary of a playbook for listing."""
    id: str
    name: str
    description: str
    category: str
    estimated_time_minutes: int
    environment: str
    agent_count: int = 0
    min_rounds: int = 0
    max_rounds: int = 0
    icon: str = "Building2"


class PlaybookManager:
    """Manages playbook templates and configurations."""

    def __init__(self):
        self._playbooks: dict[str, PlaybookConfig] = {}
        self._load_playbooks()

    def _load_playbooks(self) -> None:
        """Load all playbook JSON files from templates directory."""
        if not TEMPLATES_DIR.exists():
            logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")
            return

        for json_file in TEMPLATES_DIR.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                playbook = PlaybookConfig(**data)
                self._playbooks[playbook.id] = playbook
                logger.info(f"Loaded playbook: {playbook.id} - {playbook.name}")
            except Exception as e:
                logger.error(f"Failed to load playbook {json_file}: {e}")

    def load_playbooks(self) -> dict[str, PlaybookConfig]:
        """Reload and return all playbooks.

        Returns:
            Dictionary of playbook_id -> PlaybookConfig
        """
        self._playbooks.clear()
        self._load_playbooks()
        return self._playbooks

    def get_playbook(self, playbook_id: str) -> PlaybookConfig | None:
        """Get a single playbook by ID.

        Args:
            playbook_id: The playbook identifier

        Returns:
            PlaybookConfig or None if not found
        """
        return self._playbooks.get(playbook_id)

    # Map environment type to icon name for UI
    _ICON_MAP: dict[str, str] = {
        "integration": "Building2",
        "compliance": "ShieldAlert",
        "competitive": "Swords",
        "boardroom": "Users",
    }

    def get_all_playbooks(self) -> list[PlaybookSummary]:
        """Get summary of all playbooks.

        Returns:
            List of playbook summaries
        """
        return [
            PlaybookSummary(
                id=p.id,
                name=p.name,
                description=p.description,
                category=p.category,
                estimated_time_minutes=p.estimated_time_minutes,
                environment=p.environment,
                agent_count=sum(e.count for e in p.agent_roster),
                min_rounds=p.typical_duration_rounds[0],
                max_rounds=p.typical_duration_rounds[1],
                icon=self._ICON_MAP.get(p.environment, "Building2"),
            )
            for p in self._playbooks.values()
        ]

    def validate_playbook_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a playbook configuration.

        Args:
            config: Dictionary containing playbook configuration

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        try:
            PlaybookConfig(**config)
        except Exception as e:
            errors.append(str(e))
            return False, errors

        # Additional validation
        playbook_id = config.get("id", "")
        if not playbook_id:
            errors.append("Playbook ID is required")

        # Check agent roster has realistic power dynamics
        roster = config.get("agent_roster", [])
        high_authority_count = 0
        for entry in roster:
            # This is a simplified check - in practice, you'd check against archetypes
            if entry.get("archetype_id") in ["ceo", "cfo", "board_member"]:
                high_authority_count += entry.get("count", 1)

        total_count = sum(e.get("count", 1) for e in roster)
        if total_count > 0 and high_authority_count == total_count:
            errors.append("Roster has unrealistic power dynamics: all high authority")

        return len(errors) == 0, errors

    def prefill_roster(self, playbook_id: str) -> list[AgentRosterEntry] | None:
        """Generate default agent roster from playbook template.

        Args:
            playbook_id: The playbook identifier

        Returns:
            List of roster entries or None if playbook not found
        """
        playbook = self.get_playbook(playbook_id)
        if not playbook:
            return None
        return playbook.agent_roster

    def get_playbook_ids(self) -> list[str]:
        """Get list of all playbook IDs."""
        return list(self._playbooks.keys())

    def get_playbooks_by_category(self, category: str) -> list[PlaybookConfig]:
        """Get all playbooks in a specific category.

        Args:
            category: The category to filter by

        Returns:
            List of matching playbooks
        """
        return [p for p in self._playbooks.values() if p.category == category]


# Global manager instance
playbook_manager = PlaybookManager()


# Convenience functions
def load_playbooks() -> dict[str, PlaybookConfig]:
    """Reload and return all playbooks."""
    return playbook_manager.load_playbooks()


def get_playbook(playbook_id: str) -> PlaybookConfig | None:
    """Get a single playbook by ID."""
    return playbook_manager.get_playbook(playbook_id)


def get_all_playbooks() -> list[PlaybookSummary]:
    """Get summary of all playbooks."""
    return playbook_manager.get_all_playbooks()


def validate_playbook_config(config: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a playbook configuration."""
    return playbook_manager.validate_playbook_config(config)


def prefill_roster(playbook_id: str) -> list[AgentRosterEntry] | None:
    """Generate default agent roster from playbook template."""
    return playbook_manager.prefill_roster(playbook_id)
