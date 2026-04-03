"""Gamification scoring layer for simulations."""

import asyncio
import logging
from datetime import datetime

from pydantic import BaseModel, Field

from app.api_integrations.database import (
    ensure_tables,
    gamification_repo,
)

logger = logging.getLogger(__name__)


class TeamScore(BaseModel):
    """Score for a single team."""

    team_id: str
    team_name: str
    members: list[str]  # Agent IDs
    total_score: float
    score_breakdown: dict  # {metric: score}
    rank: int


class GamificationConfig(BaseModel):
    """Configuration for gamification."""

    enabled: bool = False
    team_count: int = 2
    teams: list[dict] = Field(default_factory=list)
    scoring_weights: dict = Field(default_factory=lambda: {
        "consensus_points": 1.0,
        "speed_bonus": 0.5,
        "risk_reduction": 0.8,
    })


class Leaderboard(BaseModel):
    """Leaderboard for a simulation."""

    simulation_id: str
    round_number: int
    teams: list[TeamScore]
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class GamificationEngine:
    """Computes gamification scores for simulations."""

    def __init__(self):
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_loaded(self) -> None:
        """Ensure database tables are initialized."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            try:
                await ensure_tables()
                self._initialized = True
            except Exception as e:
                logger.warning(
                    f"Failed to initialize gamification DB: {e}"
                )

    async def compute_scores(
        self,
        simulation_state,
        config: GamificationConfig,
    ) -> Leaderboard:
        """Compute team scores based on simulation events.

        Args:
            simulation_state: The simulation state
            config: Gamification configuration

        Returns:
            Leaderboard with team scores
        """
        await self._ensure_loaded()
        if not config.enabled or not config.teams:
            return Leaderboard(
                simulation_id=simulation_state.config.id if simulation_state else "",
                round_number=simulation_state.current_round if simulation_state else 0,
                teams=[],
            )

        simulation_id = simulation_state.config.id
        current_round = simulation_state.current_round

        team_scores = []

        for team_config in config.teams:
            team_id = team_config.get("id", "")
            team_name = team_config.get("name", f"Team {team_id}")
            member_ids = team_config.get("member_ids", [])

            # Calculate scores
            breakdown = await self._calculate_team_metrics(
                team_id,
                member_ids,
                simulation_state,
                config.scoring_weights,
            )

            total_score = sum(breakdown.values())

            team_scores.append(
                TeamScore(
                    team_id=team_id,
                    team_name=team_name,
                    members=member_ids,
                    total_score=total_score,
                    score_breakdown=breakdown,
                    rank=0,  # Will be set after sorting
                )
            )

        # Sort by total score and assign ranks
        team_scores.sort(key=lambda x: x.total_score, reverse=True)
        for i, team in enumerate(team_scores):
            team.rank = i + 1

        leaderboard = Leaderboard(
            simulation_id=simulation_id,
            round_number=current_round,
            teams=team_scores,
        )

        # Save to database
        asyncio.create_task(
            self._save_leaderboard(simulation_id, leaderboard)
        )

        return leaderboard

    async def _save_leaderboard(
        self, simulation_id: str, leaderboard: Leaderboard
    ) -> None:
        """Save leaderboard to database."""
        try:
            scores = {
                team.team_id: {
                    "total_score": team.total_score,
                    "score_breakdown": team.score_breakdown,
                    "rank": team.rank,
                }
                for team in leaderboard.teams
            }
            leaderboard_data = leaderboard.model_dump()
            await gamification_repo.save_scores(
                simulation_id, scores, leaderboard_data
            )
        except Exception as e:
            logger.warning(f"Failed to save leaderboard to DB: {e}")

    async def _calculate_team_metrics(
        self,
        team_id: str,
        member_ids: list[str],
        simulation_state,
        weights: dict,
    ) -> dict:
        """Calculate metrics for a team.

        Args:
            team_id: Team identifier
            member_ids: List of agent IDs in the team
            simulation_state: Simulation state
            weights: Scoring weights

        Returns:
            Dictionary of metric scores
        """
        breakdown = {}

        # Consensus points - team members voting together
        consensus_score = self._calculate_consensus_score(
            member_ids, simulation_state
        )
        breakdown["consensus_points"] = consensus_score * weights.get(
            "consensus_points", 1.0
        )

        # Speed bonus - early agreement
        speed_score = self._calculate_speed_score(member_ids, simulation_state)
        breakdown["speed_bonus"] = speed_score * weights.get("speed_bonus", 0.5)

        # Risk reduction - conservative decisions
        risk_score = self._calculate_risk_score(member_ids, simulation_state)
        breakdown["risk_reduction"] = risk_score * weights.get(
            "risk_reduction", 0.8
        )

        # Coalition strength
        coalition_score = self._calculate_coalition_score(
            member_ids, simulation_state
        )
        breakdown["coalition_strength"] = coalition_score * weights.get(
            "coalition_strength", 0.6
        )

        # Message quality (engagement)
        engagement_score = self._calculate_engagement_score(
            member_ids, simulation_state
        )
        breakdown["engagement"] = engagement_score * weights.get(
            "engagement", 0.4
        )

        return breakdown

    def _calculate_consensus_score(
        self, member_ids: list[str], simulation_state
    ) -> float:
        """Calculate consensus score based on aligned votes."""
        if not simulation_state or not simulation_state.rounds:
            return 0.0

        consensus_count = 0
        total_votes = 0

        for round_state in simulation_state.rounds:
            # Get votes from team members
            team_votes = []
            for msg in round_state.messages:
                if msg.agent_id in member_ids and msg.message_type == "vote":
                    # Extract vote from content
                    content_lower = msg.content.lower()
                    if "for" in content_lower:
                        team_votes.append("for")
                    elif "against" in content_lower:
                        team_votes.append("against")
                    elif "abstain" in content_lower:
                        team_votes.append("abstain")

            if len(team_votes) >= 2:
                total_votes += 1
                # Check if all votes are the same
                if len(set(team_votes)) == 1:
                    consensus_count += 1

        return consensus_count / total_votes if total_votes > 0 else 0.0

    def _calculate_speed_score(
        self, member_ids: list[str], simulation_state
    ) -> float:
        """Calculate speed score based on early agreement."""
        if not simulation_state or not simulation_state.rounds:
            return 0.0

        # Check if team reached consensus in early rounds
        for i, round_state in enumerate(simulation_state.rounds[:3]):
            team_messages = [
                msg for msg in round_state.messages
                if msg.agent_id in member_ids
            ]

            # Check for agreement indicators
            agreement_count = 0
            for msg in team_messages:
                content_lower = msg.content.lower()
                if any(word in content_lower for word in ["agree", "support", "yes"]):
                    agreement_count += 1

            if agreement_count >= len(member_ids):
                # Early agreement bonus
                return 1.0 - (i * 0.2)

        return 0.0

    def _calculate_risk_score(
        self, member_ids: list[str], simulation_state
    ) -> float:
        """Calculate risk reduction score."""
        if not simulation_state or not simulation_state.rounds:
            return 0.0

        risk_mentions = 0
        total_messages = 0

        for round_state in simulation_state.rounds:
            for msg in round_state.messages:
                if msg.agent_id in member_ids:
                    total_messages += 1
                    content_lower = msg.content.lower()
                    if any(word in content_lower for word in ["risk", "caution", "safe"]):
                        risk_mentions += 1

        return risk_mentions / total_messages if total_messages > 0 else 0.0

    def _calculate_coalition_score(
        self, member_ids: list[str], simulation_state
    ) -> float:
        """Calculate coalition strength score."""
        if not simulation_state or not simulation_state.agents:
            return 0.0

        # Check if team members have formed coalitions
        coalition_strength = 0.0

        for agent in simulation_state.agents:
            if agent.id in member_ids:
                # Count coalition members who are also team members
                team_coalition = [
                    m for m in agent.coalition_members if m in member_ids
                ]
                if team_coalition:
                    coalition_strength += len(team_coalition) / len(member_ids)

        return min(1.0, coalition_strength / len(member_ids)) if member_ids else 0.0

    def _calculate_engagement_score(
        self, member_ids: list[str], simulation_state
    ) -> float:
        """Calculate engagement score based on message activity."""
        if not simulation_state or not simulation_state.rounds:
            return 0.0

        total_messages = 0
        team_messages = 0

        for round_state in simulation_state.rounds:
            for msg in round_state.messages:
                total_messages += 1
                if msg.agent_id in member_ids:
                    team_messages += 1

        # Normalize by team size
        expected_share = len(member_ids) / len(simulation_state.agents) if simulation_state.agents else 0
        actual_share = team_messages / total_messages if total_messages > 0 else 0

        # Score based on proportional participation
        if expected_share > 0:
            ratio = actual_share / expected_share
            return min(1.0, ratio)

        return 0.0

    async def update_leaderboard(
        self,
        simulation_id: str,
        round_state,
        config: GamificationConfig | None = None,
    ) -> Leaderboard:
        """Update leaderboard after each round.

        Args:
            simulation_id: Simulation ID
            round_state: Current round state
            config: Optional gamification config

        Returns:
            Updated Leaderboard
        """
        # This is a simplified version - in practice, you'd retrieve
        # the full simulation state and compute fresh scores

        if not config or not config.enabled:
            return Leaderboard(
                simulation_id=simulation_id,
                round_number=round_state.round_number if round_state else 0,
                teams=[],
            )

        # Create minimal team scores based on round activity
        teams = []
        for team_config in config.teams:
            team_id = team_config.get("id", "")
            team_name = team_config.get("name", f"Team {team_id}")
            member_ids = team_config.get("member_ids", [])

            # Count messages from team members in this round
            message_count = sum(
                1 for msg in round_state.messages
                if msg.agent_id in member_ids
            ) if round_state else 0

            teams.append(
                TeamScore(
                    team_id=team_id,
                    team_name=team_name,
                    members=member_ids,
                    total_score=float(message_count * 10),
                    score_breakdown={
                        "round_activity": float(message_count * 10)
                    },
                    rank=0,
                )
            )

        # Sort and rank
        teams.sort(key=lambda x: x.total_score, reverse=True)
        for i, team in enumerate(teams):
            team.rank = i + 1

        return Leaderboard(
            simulation_id=simulation_id,
            round_number=round_state.round_number if round_state else 0,
            teams=teams,
        )
