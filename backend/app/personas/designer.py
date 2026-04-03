"""Custom Persona Designer for creating tailored agent personas."""

import asyncio
import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.api_integrations.database import (
    custom_persona_repo,
    ensure_tables,
)

logger = logging.getLogger(__name__)


class CustomPersonaConfig(BaseModel):
    """Configuration for a custom persona."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str
    description: str = ""
    authority_level: int = Field(5, ge=1, le=10)
    risk_tolerance: str = "moderate"
    information_bias: str = "balanced"
    decision_speed: str = "moderate"
    coalition_tendencies: float = Field(0.5, ge=0.0, le=1.0)
    incentive_structure: list[str] = []
    behavioral_axioms: list[str] = []
    system_prompt: str = ""


class CoherenceWarning(BaseModel):
    """A coherence warning for persona attributes."""

    attribute: str
    message: str
    severity: str  # "warning" or "info"


class PersonaDesigner:
    """Designer for creating custom persona configurations."""

    def __init__(self):
        self._personas: dict[str, CustomPersonaConfig] = {}
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
                    persona = CustomPersonaConfig(**persona_data)
                    self._personas[persona.id] = persona
                self._initialized = True
                logger.info(
                    f"Loaded {len(self._personas)} designer personas "
                    f"from database"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load designer personas from DB: {e}"
                )

    def create_custom_persona(self, config: dict[str, Any]) -> dict[str, Any]:
        """Create a custom persona from configuration.

        Args:
            config: Dictionary with persona attributes

        Returns:
            Created persona configuration
        """
        # Validate attribute ranges
        self._validate_attributes(config)

        # Generate system prompt from attributes
        system_prompt = self._generate_system_prompt(config)

        persona = CustomPersonaConfig(
            id=config.get("id", str(uuid.uuid4())),
            name=config.get("name", "Custom Persona"),
            role=config.get("role", "Custom Role"),
            description=config.get("description", ""),
            authority_level=config.get("authority_level", 5),
            risk_tolerance=config.get("risk_tolerance", "moderate"),
            information_bias=config.get("information_bias", "balanced"),
            decision_speed=config.get("decision_speed", "moderate"),
            coalition_tendencies=config.get("coalition_tendencies", 0.5),
            incentive_structure=config.get("incentive_structure", []),
            behavioral_axioms=config.get("behavioral_axioms", []),
            system_prompt=system_prompt,
        )

        self._personas[persona.id] = persona

        # Persist to database (async fire-and-forget)
        asyncio.create_task(
            custom_persona_repo.save(persona.id, persona.model_dump())
        )

        logger.info(f"Created custom persona: {persona.id} - {persona.name}")

        return persona.model_dump()

    def _validate_attributes(self, config: dict[str, Any]) -> None:
        """Validate persona attribute ranges.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ValueError: If attributes are out of valid range
        """
        authority = config.get("authority_level")
        if authority is not None and not (1 <= authority <= 10):
            raise ValueError(
                f"authority_level must be 1-10, got {authority}"
            )

        coalition = config.get("coalition_tendencies")
        if coalition is not None and not (0.0 <= coalition <= 1.0):
            raise ValueError(
                f"coalition_tendencies must be 0.0-1.0, got {coalition}"
            )

        valid_risk = ["conservative", "moderate", "aggressive"]
        risk = config.get("risk_tolerance")
        if risk and risk not in valid_risk:
            raise ValueError(
                f"risk_tolerance must be one of {valid_risk}, got {risk}"
            )

        valid_bias = ["qualitative", "quantitative", "balanced"]
        bias = config.get("information_bias")
        if bias and bias not in valid_bias:
            raise ValueError(
                f"information_bias must be one of {valid_bias}, got {bias}"
            )

        valid_speed = ["fast", "moderate", "slow"]
        speed = config.get("decision_speed")
        if speed and speed not in valid_speed:
            raise ValueError(
                f"decision_speed must be one of {valid_speed}, got {speed}"
            )

    def validate_coherence(self, config: dict[str, Any]) -> list[str]:
        """Check for coherence issues in persona configuration.

        Args:
            config: Configuration dictionary to check

        Returns:
            List of warning messages
        """
        warnings = []

        # Check risk/decision speed combinations
        risk = config.get("risk_tolerance", "moderate")
        speed = config.get("decision_speed", "moderate")

        if risk == "aggressive" and speed == "slow":
            warnings.append(
                "Unusual combination: aggressive risk tolerance with slow "
                "decision speed may create indecisive behavior."
            )

        if risk == "conservative" and speed == "fast":
            warnings.append(
                "Unusual combination: conservative risk tolerance with fast "
                "decision speed may create impulsive risk-averse behavior."
            )

        # Check authority/coalition combinations
        authority = config.get("authority_level", 5)
        coalition = config.get("coalition_tendencies", 0.5)

        if authority >= 9 and coalition < 0.3:
            warnings.append(
                "High authority with low coalition tendency may create "
                "isolated decision-making patterns."
            )

        if authority <= 3 and coalition > 0.7:
            warnings.append(
                "Low authority with high coalition tendency may create "
                "overly dependent behavior patterns."
            )

        # Check incentive alignment
        incentives = config.get("incentive_structure", [])
        if len(incentives) > 3:
            warnings.append(
                f"Many incentives ({len(incentives)}) "
                f"may dilute behavioral focus."
            )

        # Check behavioral axioms count
        axioms = config.get("behavioral_axioms", [])
        if len(axioms) < 2:
            warnings.append(
                "Consider adding more behavioral axioms for richer behavior."
            )
        elif len(axioms) > 5:
            warnings.append(
                "Many behavioral axioms may create conflicting guidance."
            )

        return warnings

    def _generate_system_prompt(self, config: dict[str, Any]) -> str:
        """Generate a system prompt from persona attributes.

        Args:
            config: Persona configuration

        Returns:
            Generated system prompt string
        """
        name = config.get("name", "Custom Persona")
        role = config.get("role", "Custom Role")
        description = config.get("description", "")
        authority = config.get("authority_level", 5)
        risk = config.get("risk_tolerance", "moderate")
        bias = config.get("information_bias", "balanced")
        speed = config.get("decision_speed", "moderate")
        coalition = config.get("coalition_tendencies", 0.5)
        incentives = config.get("incentive_structure", [])
        axioms = config.get("behavioral_axioms", [])

        prompt_parts = [
            f"You are {name}, a {role} in a strategic "
            f"consulting war-game simulation.",
            "",
            f"ROLE: {role}",
        ]

        # Add authority level description
        if authority >= 7:
            auth_desc = "High decision-making authority."
        elif authority >= 4:
            auth_desc = "Moderate influence."
        else:
            auth_desc = "Limited formal authority."
        prompt_parts.append(
            f"AUTHORITY LEVEL: {authority}/10 - {auth_desc}"
        )

        # Add risk tolerance description
        if risk == "aggressive":
            risk_desc = "Embraces risk for strategic advantage."
        elif risk == "moderate":
            risk_desc = "Balances risk and reward."
        else:
            risk_desc = "Avoids unnecessary risk."
        prompt_parts.append(
            f"RISK TOLERANCE: {risk.title()} - {risk_desc}"
        )

        # Add information bias description
        if bias == "quantitative":
            bias_desc = "Prefers data and metrics."
        elif bias == "qualitative":
            bias_desc = "Values stories and experience."
        else:
            bias_desc = "Integrates multiple information types."
        prompt_parts.append(
            f"INFORMATION BIAS: {bias.title()} - {bias_desc}"
        )

        # Add decision speed description
        if speed == "fast":
            speed_desc = "Decides quickly with conviction."
        elif speed == "slow":
            speed_desc = "Takes time to deliberate."
        else:
            speed_desc = "Balances speed with thoroughness."
        prompt_parts.append(
            f"DECISION SPEED: {speed.title()} - {speed_desc}"
        )

        if coalition >= 0.7:
            prompt_parts.append(
                "COALITION STYLE: Actively builds alliances."
            )
        elif coalition <= 0.3:
            prompt_parts.append(
                "COALITION STYLE: Works independently."
            )
        else:
            prompt_parts.append(
                "COALITION STYLE: Open to collaboration when beneficial."
            )

        if incentives:
            prompt_parts.append("")
            prompt_parts.append("INCENTIVES:")
            for inc in incentives:
                prompt_parts.append(f"- {inc}")

        if axioms:
            prompt_parts.append("")
            prompt_parts.append("BEHAVIORAL AXIOMS:")
            for axiom in axioms:
                prompt_parts.append(f"- {axiom}")

        if description:
            prompt_parts.append("")
            prompt_parts.append(f"CONTEXT: {description}")

        return "\n".join(prompt_parts)

    async def list_custom_personas(self) -> list[dict[str, Any]]:
        """List all custom personas.

        Returns:
            List of persona configurations
        """
        await self._ensure_loaded()
        return [p.model_dump() for p in self._personas.values()]

    async def get_custom_persona(
        self, persona_id: str
    ) -> dict[str, Any] | None:
        """Get a custom persona by ID.

        Args:
            persona_id: The persona ID

        Returns:
            Persona configuration or None if not found
        """
        await self._ensure_loaded()
        persona = self._personas.get(persona_id)
        return persona.model_dump() if persona else None

    async def update_custom_persona(
        self,
        persona_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update a custom persona.

        Args:
            persona_id: The persona ID
            updates: Dictionary of fields to update

        Returns:
            Updated persona configuration or None if not found
        """
        await self._ensure_loaded()
        persona = self._personas.get(persona_id)
        if not persona:
            return None

        # Validate updates
        self._validate_attributes(updates)

        # Update fields
        for key, value in updates.items():
            if hasattr(persona, key):
                setattr(persona, key, value)

        # Regenerate system prompt if relevant fields changed
        prompt_fields = [
            "name",
            "role",
            "description",
            "authority_level",
            "risk_tolerance",
            "information_bias",
            "decision_speed",
            "coalition_tendencies",
            "incentive_structure",
            "behavioral_axioms",
        ]
        if any(field in updates for field in prompt_fields):
            persona.system_prompt = self._generate_system_prompt(
                persona.model_dump()
            )

        logger.info(f"Updated custom persona: {persona_id}")

        # Persist to database (async fire-and-forget)
        asyncio.create_task(
            custom_persona_repo.save(persona_id, persona.model_dump())
        )

        return persona.model_dump()

    async def delete_custom_persona(self, persona_id: str) -> bool:
        """Delete a custom persona.

        Args:
            persona_id: The persona ID

        Returns:
            True if deleted, False if not found
        """
        await self._ensure_loaded()
        if persona_id in self._personas:
            del self._personas[persona_id]
            # Delete from database (async fire-and-forget)
            asyncio.create_task(custom_persona_repo.delete(persona_id))
            logger.info(f"Deleted custom persona: {persona_id}")
            return True
        return False


# Global instance
persona_designer = PersonaDesigner()
