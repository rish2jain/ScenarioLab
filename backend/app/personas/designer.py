"""Custom Persona Designer for creating tailored agent personas."""

import asyncio
import json
import logging
import math
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api_integrations.database import (
    custom_persona_repo,
    ensure_tables,
)
from app.llm.factory import get_llm_provider
from app.personas.interview_extractor import ExtractedPersona, InterviewExtractor
from app.personas.library import persona_library
from app.research.service import research_service

logger = logging.getLogger(__name__)


class ResearchRefreshError(Exception):
    """Raised when refresh-research could not obtain new external evidence."""

    def __init__(
        self,
        message: str,
        *,
        retry_after: str | None = None,
        retry_after_seconds: int | None = None,
        upstream_headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.retry_after_seconds = retry_after_seconds
        self.upstream_headers = upstream_headers or {}


class CustomPersonaDeleteOutcome(str, Enum):
    """Result of attempting to delete a custom persona."""

    DELETED = "deleted"
    NOT_FOUND_IN_MEMORY = "not_found_in_memory"


def _has_research_results(res: dict[str, Any]) -> bool:
    """True if autoresearch returned usable evidence (raw hits or non-empty synthesis)."""
    raw = res.get("raw_results") or []
    if isinstance(raw, list) and len(raw) > 0:
        return True
    syn = res.get("synthesis")
    if isinstance(syn, str) and syn.strip():
        return True
    if isinstance(syn, dict) and len(syn) > 0:
        return True
    return False


_PERSIST_MAX_ATTEMPTS = 5
_PERSIST_BASE_DELAY_S = 0.1


def _is_transient_db_error(exc: BaseException) -> bool:
    """True for errors that may succeed on retry (e.g. SQLite busy/locked)."""
    if isinstance(exc, sqlite3.OperationalError):
        return True
    if isinstance(exc, sqlite3.DatabaseError):
        return True
    if type(exc).__name__ == "OperationalError":
        return True
    msg = str(exc).lower()
    if "database is locked" in msg or "busy" in msg:
        return True
    if "unable to open database file" in msg or "disk i/o error" in msg:
        return True
    if re.search(r"\blocked\b", msg):
        return True
    return False


async def _persist_custom_persona(persona_id: str, data: dict[str, Any]) -> None:
    """Persist custom persona to DB with retries; raises if all attempts fail."""
    for attempt in range(_PERSIST_MAX_ATTEMPTS):
        try:
            await custom_persona_repo.save(persona_id, data)
            return
        except Exception as e:
            if _is_transient_db_error(e) and attempt < _PERSIST_MAX_ATTEMPTS - 1:
                delay = _PERSIST_BASE_DELAY_S * (2**attempt)
                logger.warning(
                    "Transient error persisting custom persona %s " "(attempt %s/%s): %s; retrying in %.2fs",
                    persona_id,
                    attempt + 1,
                    _PERSIST_MAX_ATTEMPTS,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            logger.exception(
                "Failed to persist custom persona %s to database",
                persona_id,
            )
            raise


async def _delete_custom_persona(persona_id: str) -> bool:
    """Delete from DB with retries.

    Returns:
        ``True`` if ``DELETE`` removed at least one row, ``False`` if no row matched.

    Raises:
        Exception: On non-transient DB errors, or if transient errors persist after
        all retries. Do **not** interpret exceptions as "not found"; they indicate
        the delete did not complete.
    """
    for attempt in range(_PERSIST_MAX_ATTEMPTS):
        try:
            return await custom_persona_repo.delete(persona_id)
        except Exception as e:
            if _is_transient_db_error(e) and attempt < _PERSIST_MAX_ATTEMPTS - 1:
                delay = _PERSIST_BASE_DELAY_S * (2**attempt)
                logger.warning(
                    "Transient error deleting custom persona %s " "(attempt %s/%s): %s; retrying in %.2fs",
                    persona_id,
                    attempt + 1,
                    _PERSIST_MAX_ATTEMPTS,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            logger.exception(
                "Failed to delete custom persona %s from database",
                persona_id,
            )
            raise


def summarize_synthesis_dict(syn: dict[str, Any], max_chars: int = 4000) -> str:
    """Serialize a synthesis dict to JSON capped at max_chars for evidence_summary."""

    def _shrink(
        obj: Any,
        max_str: int,
        max_list: int,
        max_dict_keys: int,
        depth: int = 0,
    ) -> Any:
        if depth > 40:
            return "<truncated>"
        if isinstance(obj, dict):
            out: dict[str, Any] = {}
            for i, (k, v) in enumerate(obj.items()):
                if i >= max_dict_keys:
                    out["_truncated"] = "<truncated>"
                    break
                sk = str(k)
                if len(sk) > min(max_str, 200):
                    sk = sk[:200] + "<truncated>"
                out[sk] = _shrink(v, max_str, max_list, max_dict_keys, depth + 1)
            return out
        if isinstance(obj, list):
            if len(obj) > max_list:
                return [_shrink(x, max_str, max_list, max_dict_keys, depth + 1) for x in obj[:max_list]] + [
                    "<truncated>"
                ]
            return [_shrink(x, max_str, max_list, max_dict_keys, depth + 1) for x in obj]
        if isinstance(obj, str):
            if len(obj) > max_str:
                return obj[:max_str] + "<truncated>"
            return obj
        if isinstance(obj, (int, float, bool)) or obj is None:
            return obj
        if isinstance(obj, (tuple, set)):
            return _shrink(list(obj), max_str, max_list, max_dict_keys, depth + 1)
        text = str(obj)
        return text[:max_str] + ("<truncated>" if len(text) > max_str else "")

    ms, ml, mk = 800, 40, 30
    for _ in range(24):
        candidate = _shrink(syn, ms, ml, mk)
        text = json.dumps(candidate, ensure_ascii=False)
        if len(text) <= max_chars:
            return text
        ms = max(48, ms // 2)
        ml = max(2, ml // 2)
        mk = max(2, mk // 2)

    raw = json.dumps(syn, ensure_ascii=False)
    lo, hi = 0, len(raw)
    best = json.dumps({"_truncated": True, "preview": ""}, ensure_ascii=False)
    while lo <= hi:
        mid = (lo + hi + 1) // 2
        preview = raw[:mid]
        fb = json.dumps({"_truncated": True, "preview": preview}, ensure_ascii=False)
        if len(fb) <= max_chars:
            best = fb
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _persona_public_dump(persona: "CustomPersonaConfig") -> dict[str, Any]:
    """Serialize persona for API responses and JSON DB storage (ISO-8601 datetimes)."""
    return persona.model_dump(mode="json")


class Citation(BaseModel):
    """Structured evidence reference for a designer persona."""

    model_config = ConfigDict(extra="ignore")

    source: str = ""
    url: str = ""
    note: str = ""
    retrieved_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_keys(cls, data: Any) -> Any:
        if data is None:
            return {}
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if out.get("source") in (None, "") and out.get("title"):
            out["source"] = out.get("title") or ""
        if out.get("note") in (None, "") and out.get("snippet") is not None:
            out["note"] = out.get("snippet") or ""
        return out


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
    evidence_summary: str = ""
    citations: list[Citation] = Field(default_factory=list)
    last_researched_at: datetime | None = None
    evidence_pack_id: str = ""

    @field_validator("last_researched_at", mode="before")
    @classmethod
    def _parse_last_researched_at(cls, v: Any) -> datetime | None:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            if s.endswith("Z") and not s.endswith("+00:00"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        raise TypeError("last_researched_at must be datetime, ISO string, or empty")


class CoherenceWarning(BaseModel):
    """A coherence warning for persona attributes."""

    attribute: str
    message: str
    severity: str  # "warning" or "info"


def _refresh_merge_differs_from_snapshot(snapshot: CustomPersonaConfig, merged: CustomPersonaConfig) -> bool:
    """True if refresh merge produced different stored fields than ``snapshot``.

    Compares the post-merge persona to the pre-merge snapshot so we only bump
    ``last_researched_at`` when persisted evidence/traits actually change (avoids
    drift between predicted vs applied merge, e.g. behavioral axioms ordering).
    """
    if merged.evidence_summary != snapshot.evidence_summary:
        return True
    if merged.citations != snapshot.citations:
        return True
    if merged.risk_tolerance != snapshot.risk_tolerance:
        return True
    if merged.information_bias != snapshot.information_bias:
        return True
    if merged.decision_speed != snapshot.decision_speed:
        return True
    if merged.authority_level != snapshot.authority_level:
        return True
    if not math.isclose(
        merged.coalition_tendencies,
        snapshot.coalition_tendencies,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        return True
    if list(merged.incentive_structure) != list(snapshot.incentive_structure):
        return True
    if list(merged.behavioral_axioms) != list(snapshot.behavioral_axioms):
        return True
    return False


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
                logger.info(f"Loaded {len(self._personas)} designer personas " f"from database")
            except Exception as e:
                logger.warning(f"Failed to load designer personas from DB: {e}")

    async def create_custom_persona(self, config: dict[str, Any]) -> dict[str, Any]:
        """Create a custom persona from configuration.

        Args:
            config: Dictionary with persona attributes

        Returns:
            Created persona configuration
        """
        await self._ensure_loaded()

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
            evidence_summary=config.get("evidence_summary", ""),
            citations=config.get("citations") or [],
            last_researched_at=config.get("last_researched_at"),
            evidence_pack_id=config.get("evidence_pack_id", ""),
        )

        await _persist_custom_persona(persona.id, _persona_public_dump(persona))
        self._personas[persona.id] = persona

        logger.info(f"Created custom persona: {persona.id} - {persona.name}")

        return _persona_public_dump(persona)

    def _validate_attributes(self, config: dict[str, Any]) -> None:
        """Validate persona attribute ranges.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ValueError: If attributes are out of valid range
        """
        authority = config.get("authority_level")
        if authority is not None and not (1 <= authority <= 10):
            raise ValueError(f"authority_level must be 1-10, got {authority}")

        coalition = config.get("coalition_tendencies")
        if coalition is not None and not (0.0 <= coalition <= 1.0):
            raise ValueError(f"coalition_tendencies must be 0.0-1.0, got {coalition}")

        valid_risk = ["conservative", "moderate", "aggressive"]
        risk = config.get("risk_tolerance")
        if risk and risk not in valid_risk:
            raise ValueError(f"risk_tolerance must be one of {valid_risk}, got {risk}")

        valid_bias = ["qualitative", "quantitative", "balanced"]
        bias = config.get("information_bias")
        if bias and bias not in valid_bias:
            raise ValueError(f"information_bias must be one of {valid_bias}, got {bias}")

        valid_speed = ["fast", "moderate", "slow"]
        speed = config.get("decision_speed")
        if speed and speed not in valid_speed:
            raise ValueError(f"decision_speed must be one of {valid_speed}, got {speed}")

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
                "High authority with low coalition tendency may create " "isolated decision-making patterns."
            )

        if authority <= 3 and coalition > 0.7:
            warnings.append(
                "Low authority with high coalition tendency may create " "overly dependent behavior patterns."
            )

        # Check incentive alignment
        incentives = config.get("incentive_structure", [])
        if len(incentives) > 3:
            warnings.append(f"Many incentives ({len(incentives)}) " f"may dilute behavioral focus.")

        # Check behavioral axioms count
        axioms = config.get("behavioral_axioms", [])
        if len(axioms) < 2:
            warnings.append("Consider adding more behavioral axioms for richer behavior.")
        elif len(axioms) > 5:
            warnings.append("Many behavioral axioms may create conflicting guidance.")

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
            f"You are {name}, a {role} in a strategic " f"consulting war-game simulation.",
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
        prompt_parts.append(f"AUTHORITY LEVEL: {authority}/10 - {auth_desc}")

        # Add risk tolerance description
        if risk == "aggressive":
            risk_desc = "Embraces risk for strategic advantage."
        elif risk == "moderate":
            risk_desc = "Balances risk and reward."
        else:
            risk_desc = "Avoids unnecessary risk."
        prompt_parts.append(f"RISK TOLERANCE: {risk.title()} - {risk_desc}")

        # Add information bias description
        if bias == "quantitative":
            bias_desc = "Prefers data and metrics."
        elif bias == "qualitative":
            bias_desc = "Values stories and experience."
        else:
            bias_desc = "Integrates multiple information types."
        prompt_parts.append(f"INFORMATION BIAS: {bias.title()} - {bias_desc}")

        # Add decision speed description
        if speed == "fast":
            speed_desc = "Decides quickly with conviction."
        elif speed == "slow":
            speed_desc = "Takes time to deliberate."
        else:
            speed_desc = "Balances speed with thoroughness."
        prompt_parts.append(f"DECISION SPEED: {speed.title()} - {speed_desc}")

        if coalition >= 0.7:
            prompt_parts.append("COALITION STYLE: Actively builds alliances.")
        elif coalition <= 0.3:
            prompt_parts.append("COALITION STYLE: Works independently.")
        else:
            prompt_parts.append("COALITION STYLE: Open to collaboration when beneficial.")

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

        ev = config.get("evidence_summary", "")
        if ev:
            prompt_parts.append("")
            prompt_parts.append("EXTERNAL RESEARCH (cite only facts grounded here):\n" + ev)

        return "\n".join(prompt_parts)

    async def list_custom_personas(self) -> list[dict[str, Any]]:
        """List all custom personas.

        Returns:
            List of persona configurations
        """
        await self._ensure_loaded()
        return [_persona_public_dump(p) for p in self._personas.values()]

    async def get_custom_persona(self, persona_id: str) -> dict[str, Any] | None:
        """Get a custom persona by ID.

        Args:
            persona_id: The persona ID

        Returns:
            Persona configuration or None if not found
        """
        await self._ensure_loaded()
        persona = self._personas.get(persona_id)
        return _persona_public_dump(persona) if persona else None

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

        snapshot = persona.model_copy(deep=True)
        try:
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
                "evidence_summary",
            ]
            if any(field in updates for field in prompt_fields):
                persona.system_prompt = self._generate_system_prompt(persona.model_dump())

            logger.info(f"Updated custom persona: {persona_id}")

            await _persist_custom_persona(persona_id, _persona_public_dump(persona))

            return _persona_public_dump(persona)
        except Exception:
            self._personas[persona_id] = snapshot
            raise

    async def refresh_research_for_persona(
        self,
        persona_id: str,
    ) -> dict[str, Any] | None:
        """Re-fetch web research and merge evidence fields for a designer persona.

        Interview extraction uses ``allow_fallback=False`` so failed research does not
        replace stored traits with generic description-based defaults.

        If merged evidence and traits match what was already stored, returns without
        updating ``last_researched_at`` or persisting (no-op refresh).

        Raises:
            ResearchRefreshError: If the research service fails or returns no usable
                results (so we do not update timestamps or persist).
        """
        await self._ensure_loaded()
        persona = self._personas.get(persona_id)
        if not persona:
            return None

        try:
            res = await research_service.research_executive(persona.name, company="", role=persona.role)
        except Exception as e:
            logger.warning("refresh research service failed: %s", e)
            raise ResearchRefreshError("Research service failed; no evidence was refreshed.") from e

        if not isinstance(res, dict) or not _has_research_results(res):
            raise ResearchRefreshError("No research results returned. Check API keys (e.g. Tavily) and connectivity.")

        raw = res.get("raw_results") or []
        cites = [
            Citation(
                source=r.get("title", "") or "",
                url=r.get("url", "") or "",
                note=(r.get("content") or "")[:400],
                retrieved_at=None,
            )
            for r in raw[:10]
            if isinstance(r, dict)
        ]
        syn = res.get("synthesis") or {}
        if isinstance(syn, str):
            summary = syn[:4000] if len(syn) > 4000 else syn
        elif isinstance(syn, dict):
            summary = summarize_synthesis_dict(syn)
        else:
            text = str(syn)
            summary = text[:4000] if len(text) > 4000 else text

        researched: ExtractedPersona | None = None
        try:
            llm = get_llm_provider()
            extractor = InterviewExtractor(llm_provider=llm)
            researched = await extractor.research_persona(
                persona.name,
                company="",
                role=persona.role,
                allow_fallback=False,
            )
        except Exception as e:
            logger.warning("refresh research interview_extractor failed: %s", e)

        snapshot = persona.model_copy(deep=True)
        try:
            persona.evidence_summary = summary or persona.evidence_summary
            persona.citations = cites or persona.citations
            if researched:
                persona.risk_tolerance = researched.risk_tolerance
                persona.information_bias = researched.information_bias
                persona.decision_speed = researched.decision_speed
                persona.authority_level = researched.authority_level
                persona.coalition_tendencies = researched.coalition_tendencies
                persona.incentive_structure = researched.incentive_structure
                persona.behavioral_axioms = list(
                    dict.fromkeys(list(persona.behavioral_axioms) + list(researched.behavioral_axioms))
                )[:8]

            if not _refresh_merge_differs_from_snapshot(snapshot, persona):
                self._personas[persona_id] = snapshot
                return _persona_public_dump(snapshot)

            persona.last_researched_at = datetime.now(timezone.utc)
            persona.system_prompt = self._generate_system_prompt(persona.model_dump())
            await _persist_custom_persona(persona_id, _persona_public_dump(persona))
            return _persona_public_dump(persona)
        except Exception:
            self._personas[persona_id] = snapshot
            raise

    async def delete_custom_persona(self, persona_id: str) -> CustomPersonaDeleteOutcome:
        """Delete a custom persona.

        Args:
            persona_id: The persona ID

        Returns:
            :attr:`CustomPersonaDeleteOutcome.DELETED` if the persona was removed from
            the designer cache (and ``persona_library`` cache). The DB ``DELETE`` may
            remove a row or match none (already gone / desync); either way the in-memory
            copy is dropped so list/get cannot show a ghost.
            :attr:`CustomPersonaDeleteOutcome.NOT_FOUND_IN_MEMORY` if this designer
            has no such persona loaded.

        Raises:
            Exception: If the database delete fails after retries (distinct from
            not-found-in-memory, which returns without raising).
        """
        await self._ensure_loaded()
        if persona_id not in self._personas:
            logger.debug(
                "Delete custom persona %s: id not in loaded personas",
                persona_id,
            )
            return CustomPersonaDeleteOutcome.NOT_FOUND_IN_MEMORY

        db_deleted = await _delete_custom_persona(persona_id)
        if not db_deleted:
            logger.warning(
                "Delete custom persona %s: DELETE matched no DB row while persona "
                "was still in memory (possible cache/DB mismatch); reconciling caches",
                persona_id,
            )

        del self._personas[persona_id]
        persona_library.remove_custom_persona_from_cache(persona_id)
        logger.info("Deleted custom persona: %s", persona_id)
        return CustomPersonaDeleteOutcome.DELETED


# Global instance
persona_designer = PersonaDesigner()
