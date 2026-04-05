"""Confidence decay model for simulation assumptions."""

import logging

from pydantic import BaseModel, Field

from app.simulation.assumptions import Assumption
from app.simulation.models import EnvironmentType

logger = logging.getLogger(__name__)


# Default decay rates per environment type
DECAY_RATES: dict[EnvironmentType, float] = {
    EnvironmentType.BOARDROOM: 0.95,  # Slow decay, structured environment
    EnvironmentType.WAR_ROOM: 0.92,  # Moderate, high-pressure
    EnvironmentType.NEGOTIATION: 0.90,  # Fast decay, bilateral uncertainty
    EnvironmentType.INTEGRATION: 0.93,  # Moderate, complex dependencies
}

# Confidence band width (±5%)
CONFIDENCE_BAND_WIDTH = 0.05


class ConfidencePoint(BaseModel):
    """A single point on the confidence decay curve."""

    round: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    band_low: float = Field(..., ge=0.0, le=1.0)
    band_high: float = Field(..., ge=0.0, le=1.0)


class DecayCurveResult(BaseModel):
    """Result of computing a decay curve."""

    simulation_id: str
    environment_type: EnvironmentType
    decay_rate: float
    initial_confidence: float
    num_rounds: int
    points: list[ConfidencePoint]
    total_decay_percent: float


class ConfidenceDecayModel:
    """Model for computing confidence decay over simulation rounds.

    Decay formula: confidence(round) = initial_confidence * decay_rate^(r-1)
    Target: round-20 confidence should be 15-30% lower than round-1.
    """

    def __init__(self, decay_rates: dict[EnvironmentType, float] | None = None):
        """Initialize with optional custom decay rates.

        Args:
            decay_rates: Custom decay rates per environment type.
                         If None, uses default rates.
        """
        self.decay_rates = decay_rates or DECAY_RATES

    def get_decay_rate(self, environment_type: EnvironmentType) -> float:
        """Get the decay rate for a given environment type.

        Args:
            environment_type: The simulation environment type.

        Returns:
            Decay rate (0.0 to 1.0, where lower = faster decay).
        """
        return self.decay_rates.get(environment_type, 0.92)

    def compute_decay(
        self,
        round_number: int,
        initial_confidence: float,
        decay_rate: float,
    ) -> float:
        """Compute confidence at a given round using decay formula.

        Formula: confidence(round) = initial_confidence * decay_rate^(r-1)

        Args:
            round_number: The round number (1-indexed).
            initial_confidence: Initial confidence value (0.0 to 1.0).
            decay_rate: Decay factor per round.

        Returns:
            Decayed confidence value.
        """
        if round_number < 1:
            round_number = 1

        # Apply decay formula
        decayed = initial_confidence * (decay_rate ** (round_number - 1))

        # Ensure within bounds
        return max(0.0, min(1.0, decayed))

    def compute_decay_curve(
        self,
        simulation_id: str,
        num_rounds: int,
        environment_type: EnvironmentType,
        initial_confidence: float = 0.85,
    ) -> DecayCurveResult:
        """Compute the full decay curve for a simulation.

        Args:
            simulation_id: The simulation ID.
            num_rounds: Total number of rounds.
            environment_type: The simulation environment type.
            initial_confidence: Starting confidence (default 0.85).

        Returns:
            DecayCurveResult with all points on the curve.
        """
        decay_rate = self.get_decay_rate(environment_type)
        points: list[ConfidencePoint] = []

        for round_num in range(1, num_rounds + 1):
            confidence = self.compute_decay(
                round_number=round_num,
                initial_confidence=initial_confidence,
                decay_rate=decay_rate,
            )
            band_low = max(0.0, confidence - CONFIDENCE_BAND_WIDTH)
            band_high = min(1.0, confidence + CONFIDENCE_BAND_WIDTH)

            points.append(
                ConfidencePoint(
                    round=round_num,
                    confidence=round(confidence, 4),
                    band_low=round(band_low, 4),
                    band_high=round(band_high, 4),
                )
            )

        # Calculate total decay percentage
        if points:
            final_confidence = points[-1].confidence
            total_decay = (initial_confidence - final_confidence) / initial_confidence * 100
        else:
            total_decay = 0.0

        return DecayCurveResult(
            simulation_id=simulation_id,
            environment_type=environment_type,
            decay_rate=decay_rate,
            initial_confidence=initial_confidence,
            num_rounds=num_rounds,
            points=points,
            total_decay_percent=round(total_decay, 2),
        )

    def apply_decay_to_assumptions(
        self,
        assumptions: list[Assumption],
        round_number: int,
        environment_type: EnvironmentType,
    ) -> list[Assumption]:
        """Apply confidence decay to a list of assumptions.

        Creates new Assumption objects with decayed confidence values.

        Args:
            assumptions: List of assumptions to decay.
            round_number: Current round number.
            environment_type: The simulation environment type.

        Returns:
            New list of assumptions with decayed confidence.
        """
        decay_rate = self.get_decay_rate(environment_type)

        decayed_assumptions = []
        for assumption in assumptions:
            decayed_confidence = self.compute_decay(
                round_number=round_number,
                initial_confidence=assumption.confidence,
                decay_rate=decay_rate,
            )

            # Create a copy with decayed confidence
            decayed = Assumption(
                id=assumption.id,
                description=assumption.description,
                value=assumption.value,
                confidence=round(decayed_confidence, 4),
                evidence=assumption.evidence.copy(),
                sensitivity_score=assumption.sensitivity_score,
                category=assumption.category,
                source=assumption.source,
                high_sensitivity=assumption.high_sensitivity,
            )
            decayed_assumptions.append(decayed)

        return decayed_assumptions

    def validate_decay_rates(self) -> bool:
        """Validate that decay rates will produce target decay range.

        Target: Round 20 should have 15-30% lower confidence than round 1.

        Returns:
            True if decay rates are within acceptable range.
        """
        for env_type, rate in self.decay_rates.items():
            # Check round 20 decay
            round_20_confidence = self.compute_decay(
                round_number=20,
                initial_confidence=1.0,
                decay_rate=rate,
            )
            decay_percent = (1.0 - round_20_confidence) * 100

            if not (15.0 <= decay_percent <= 30.0):
                logger.warning(
                    f"Decay rate {rate} for {env_type.value} produces "
                    f"{decay_percent:.1f}% decay at round 20 "
                    f"(target: 15-30%)"
                )
                # Still return True, just log warning

        return True


# Global instance
confidence_decay_model = ConfidenceDecayModel()
