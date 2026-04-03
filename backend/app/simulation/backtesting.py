"""Backtesting Engine for simulation accuracy validation."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.llm.factory import get_llm_provider
from app.simulation.engine import SimulationEngine, simulation_engine
from app.simulation.models import (
    AgentConfig,
    EnvironmentType,
    SimulationConfig,
)

logger = logging.getLogger(__name__)


# Bundled test cases
BUNDLED_CASES = [
    {
        "case_id": "microsoft_activision_merger",
        "name": "Microsoft-Activision Merger",
        "description": "Microsoft's $68.7 billion acquisition of Activision Blizzard, facing regulatory scrutiny from FTC and CMA.",
        "tags": ["M&A", "Regulatory", "Tech", "Gaming"],
        "seed_material": """
Microsoft announced its intent to acquire Activision Blizzard for $68.7 billion in January 2022.
Key stakeholders:
- Microsoft: Seeking to expand gaming portfolio and metaverse presence
- Activision Blizzard: Facing workplace culture issues, seeking exit
- FTC: Concerned about competition in gaming market
- CMA (UK): Initially blocked, later approved with remedies
- Sony: Competitor concerned about Call of Duty exclusivity

Timeline context:
- Jan 2022: Deal announced
- Dec 2022: FTC files to block
- Apr 2023: CMA blocks deal
- May 2023: EU approves with remedies
- Jul 2023: US court rules in Microsoft's favor
- Oct 2023: Deal closes after CMA approval

Key issues: Cloud gaming competition, Call of Duty exclusivity, regulatory jurisdiction.
""",
        "actual_outcomes": {
            "stakeholder_stances": {
                "microsoft": "aggressively pursued deal, made concessions on licensing",
                "activision": "strongly supportive, needed deal for culture reset",
                "ftc": "opposed, filed lawsuit to block",
                "cma": "initially blocked, approved with behavioral remedies",
                "sony": "opposed, concerned about exclusivity",
                "eu": "approved with licensing remedies",
            },
            "timeline": {
                "announcement_to_close_months": 21,
                "regulatory_hurdles": 3,
                "key_milestones": [
                    "FTC lawsuit filed",
                    "CMA initial block",
                    "US court victory",
                    "CMA approval",
                ],
            },
            "outcome_direction": {
                "deal_completed": True,
                "with_concessions": True,
                "behavioral_remedies": True,
                "structural_remedies": False,
            },
        },
    },
    {
        "case_id": "svb_collapse",
        "name": "Silicon Valley Bank Collapse",
        "description": "The sudden collapse of SVB in March 2023, the second-largest bank failure in US history.",
        "tags": ["Financial Crisis", "Banking", "Tech", "Regulatory"],
        "seed_material": """
Silicon Valley Bank, a key lender to tech startups, collapsed in March 2023.
Key stakeholders:
- SVB Management: Attempted capital raise after bond portfolio losses revealed
- VCs: Many advised portfolio companies to withdraw funds
- Startups: Rushed to withdraw deposits, many uninsured
- FDIC: Took over bank, guaranteed all deposits
- Federal Reserve: Launched Bank Term Funding Program
- Other Regional Banks: Faced contagion fears

Timeline context:
- Mar 8, 2023: SVB announces $1.8B loss and capital raise
- Mar 9, 2023: VC panic, $42B withdrawal attempt
- Mar 10, 2023: FDIC takes over SVB
- Mar 12, 2023: Government guarantees all deposits
- Mar 12, 2023: Signature Bank also closed

Key issues: Interest rate risk, uninsured deposits, tech sector concentration, regulatory oversight.
""",
        "actual_outcomes": {
            "stakeholder_stances": {
                "svb_management": "attempted emergency capital raise, failed",
                "vcs": "sounded alarm, told companies to withdraw",
                "startups": "panic withdrawal, advocated for bailout",
                "fdic": "took control, guaranteed deposits",
                "federal_reserve": "created emergency lending facility",
                "other_banks": "faced contagion, some failed",
            },
            "timeline": {
                "crisis_start_to_failure_days": 2,
                "government_intervention_days": 2,
                "key_milestones": [
                    "Capital raise announced",
                    "Bank run triggered",
                    "FDIC takeover",
                    "Deposit guarantee",
                ],
            },
            "outcome_direction": {
                "bank_failed": True,
                "depositors_protected": True,
                "shareholders_wiped_out": True,
                "contagion_limited": True,
            },
        },
    },
    {
        "case_id": "eu_ai_act",
        "name": "EU AI Act Implementation",
        "description": "The European Union's comprehensive AI regulation, the world's first major AI law.",
        "tags": ["Regulatory", "Tech", "AI", "Policy"],
        "seed_material": """
The EU AI Act, passed in 2024, establishes comprehensive rules for AI systems.
Key stakeholders:
- EU Parliament: Pushed for stricter rules, transparency requirements
- EU Commission: Proposed original framework, balanced interests
- Tech Companies (Google, Microsoft, OpenAI): Sought flexible rules, warned about innovation impact
- Civil Society: Advocated for strong protections against AI harms
- Member States: France sought lighter touch for national champions

Timeline context:
- Apr 2021: Commission proposes AI Act
- Dec 2022: Council adopts position
- Jun 2023: Parliament adopts position
- Dec 2023: Political agreement reached
- Mar 2024: Parliament passes final text
- Aug 2024: Entry into force

Key issues: Risk classification, foundation models, biometric surveillance, transparency requirements, enforcement.
""",
        "actual_outcomes": {
            "stakeholder_stances": {
                "eu_parliament": "strong pro-regulation, pushed for strict rules",
                "eu_commission": "moderate, balanced innovation and protection",
                "tech_companies": "concerned but accepting, sought clarity",
                "civil_society": "satisfied with protections",
                "member_states": "mixed, some wanted lighter rules",
            },
            "timeline": {
                "proposal_to_passage_months": 35,
                "negotiation_phases": 3,
                "key_milestones": [
                    "Commission proposal",
                    "Parliament amendments",
                    "Trilogue negotiations",
                    "Final passage",
                ],
            },
            "outcome_direction": {
                "comprehensive_regulation": True,
                "risk_based_approach": True,
                "foundation_model_rules": True,
                "innovation_concerns_addressed": "partially",
            },
        },
    },
    {
        "case_id": "boeing_737_max",
        "name": "Boeing 737 MAX Crisis",
        "description": "Two fatal crashes and the subsequent grounding and safety crisis for Boeing's 737 MAX aircraft.",
        "tags": ["Crisis Management", "Aviation", "Safety", "Corporate"],
        "seed_material": """
Boeing 737 MAX was grounded worldwide after two fatal crashes (Lion Air 2018, Ethiopian 2019).
Key stakeholders:
- Boeing: Minimized issues, pushed for return to service
- FAA: Initially deferred to Boeing, later criticized
- Airlines: Lost revenue, sought compensation
- Victims' Families: Demanded accountability and justice
- Congress: Investigated, criticized FAA delegation
- Pilots' Unions: Raised safety concerns

Timeline context:
- Oct 2018: Lion Air crash (189 deaths)
- Mar 2019: Ethiopian crash (157 deaths)
- Mar 2019: Worldwide grounding
- Dec 2020: Return to service (US)
- Jan 2021: Criminal settlement ($2.5B)

Key issues: MCAS system, pilot training, regulatory capture, corporate culture, safety vs profit.
""",
        "actual_outcomes": {
            "stakeholder_stances": {
                "boeing": "initially defensive, later apologetic, restructured",
                "faa": "defensive, later reformed certification process",
                "airlines": "frustrated, demanded compensation",
                "victims_families": "demanded accountability, achieved settlement",
                "congress": "critical, mandated reforms",
                "pilots": "raised early warnings, vindicated",
            },
            "timeline": {
                "first_crash_to_grounding_months": 5,
                "grounding_duration_months": 20,
                "key_milestones": [
                    "Lion Air crash",
                    "Ethiopian crash",
                    "Worldwide grounding",
                    "Software fix approved",
                    "Return to service",
                ],
            },
            "outcome_direction": {
                "aircraft_recertified": True,
                "management_changed": True,
                "criminal_charges": True,
                "compensation_paid": True,
                "regulatory_reform": True,
            },
        },
    },
    {
        "case_id": "twitter_x_acquisition",
        "name": "Twitter/X Acquisition",
        "description": "Elon Musk's $44 billion acquisition of Twitter, transforming it into X.",
        "tags": ["M&A", "Tech", "Social Media", "Hostile Takeover"],
        "seed_material": """
Elon Musk acquired Twitter for $44 billion in October 2022 after a turbulent process.
Key stakeholders:
- Elon Musk: Made offer, tried to back out, forced to close
- Twitter Board: Initially resisted, then accepted with poison pill
- Twitter Employees: Faced mass layoffs, culture upheaval
- Advertisers: Concerned about content moderation changes
- Users/Creators: Mixed reactions, some left, some stayed
- Banks/Investors: Provided financing, faced losses

Timeline context:
- Apr 2022: Musk reveals stake, offers to buy
- Apr 2022: Board accepts offer with poison pill removed
- May 2022: Deal put on hold (bot accounts)
- Jul 2022: Musk tries to terminate
- Oct 2022: Court forces deal, Musk closes
- Late 2022: Mass layoffs, product changes

Key issues: Deal certainty, financing, employee treatment, content moderation, advertiser relations.
""",
        "actual_outcomes": {
            "stakeholder_stances": {
                "elon_musk": "reluctant buyer at end, proceeded with vision",
                "twitter_board": "forced deal through legal means",
                "employees": "mass exodus, layoffs, culture change",
                "advertisers": "many left, concerned about brand safety",
                "users": "polarized, some migrated to alternatives",
                "investors": "took losses as value declined",
            },
            "timeline": {
                "offer_to_close_months": 6,
                "legal_battles": 2,
                "key_milestones": [
                    "Initial offer",
                    "Board acceptance",
                    "Musk attempts to terminate",
                    "Court ruling",
                    "Deal close",
                ],
            },
            "outcome_direction": {
                "deal_completed": True,
                "original_leadership_retained": False,
                "mass_layoffs": True,
                "platform_transformed": True,
                "value_preserved": False,
            },
        },
    },
]


class BacktestingEngine:
    """Engine for backtesting simulations against historical outcomes."""

    def __init__(self):
        self.engine = simulation_engine

    async def run_backtest(
        self,
        case_id: str | None = None,
        seed_material: str | None = None,
        actual_outcomes: dict | None = None,
    ) -> dict[str, Any]:
        """Run a backtest comparing simulated vs actual outcomes.

        Args:
            case_id: ID of a bundled case to use.
            seed_material: Custom seed material (if not using bundled case).
            actual_outcomes: Custom actual outcomes (if not using bundled case).

        Returns:
            Backtest results with accuracy scores.
        """
        # Get case data
        if case_id:
            case = self.get_bundled_case(case_id)
            if not case:
                return {"error": f"Case not found: {case_id}"}
            seed_material = case["seed_material"]
            actual_outcomes = case["actual_outcomes"]
        elif not seed_material or not actual_outcomes:
            return {"error": "Either case_id or both seed_material and actual_outcomes required"}

        # Create simulation config from seed material
        config = self._create_simulation_config(seed_material)

        try:
            # Run simulation
            sim_state = await self.engine.create_simulation(config)
            await self.engine.run_simulation(sim_state.config.id)

            # Get final state
            final_state = await self.engine.get_simulation(sim_state.config.id)
            if not final_state:
                return {"error": "Simulation failed to complete"}

            # Compare results
            comparison = self.compare_results(
                self._extract_simulated_outcomes(final_state),
                actual_outcomes,
            )

            return {
                "case_id": case_id,
                "simulation_id": final_state.config.id,
                "status": final_state.status.value,
                "comparison": comparison,
                "seed_material": seed_material,
                "simulated_outcomes": self._extract_simulated_outcomes(final_state),
                "actual_outcomes": actual_outcomes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return {"error": str(e)}

    def _create_simulation_config(self, seed_material: str) -> SimulationConfig:
        """Create simulation config from seed material."""
        # Create default agents based on typical stakeholders
        agents = [
            AgentConfig(name="Executive", archetype_id="aggressor"),
            AgentConfig(name="Analyst", archetype_id="analyst"),
            AgentConfig(name="Skeptic", archetype_id="skeptic"),
            AgentConfig(name="Mediator", archetype_id="mediator"),
        ]

        return SimulationConfig(
            name="Backtest Simulation",
            description=f"Backtest run at {datetime.now(timezone.utc).isoformat()}",
            environment_type=EnvironmentType.BOARDROOM,
            agents=agents,
            total_rounds=5,
            parameters={"seed_material": seed_material},
        )

    def _extract_simulated_outcomes(self, sim_state: Any) -> dict:
        """Extract outcomes from simulation state."""
        stakeholder_stances = {}
        for agent in sim_state.agents:
            stakeholder_stances[agent.name.lower()] = agent.current_stance

        return {
            "stakeholder_stances": stakeholder_stances,
            "timeline": {
                "rounds_completed": sim_state.current_round,
                "total_messages": sum(len(r.messages) for r in sim_state.rounds),
            },
            "outcome_direction": {
                "consensus_reached": "consensus" in str(sim_state.results_summary).lower(),
                "final_status": sim_state.status.value,
            },
        }

    def compare_results(
        self, simulated: dict, actual: dict
    ) -> dict[str, Any]:
        """Compare simulated results against actual outcomes.

        Args:
            simulated: Simulated outcomes.
            actual: Actual outcomes.

        Returns:
            Detailed comparison with rubric scores.
        """
        comparison = {
            "rubric_scores": {},
            "detailed_analysis": {},
            "overall_accuracy": 0.0,
        }

        # 1. Stakeholder Stance Accuracy
        stance_score = self._score_stance_accuracy(
            simulated.get("stakeholder_stances", {}),
            actual.get("stakeholder_stances", {}),
        )
        comparison["rubric_scores"]["stakeholder_stance_accuracy"] = stance_score
        comparison["detailed_analysis"]["stance_comparison"] = self._detail_stance_comparison(
            simulated.get("stakeholder_stances", {}),
            actual.get("stakeholder_stances", {}),
        )

        # 2. Timeline Accuracy
        timeline_score = self._score_timeline_accuracy(
            simulated.get("timeline", {}),
            actual.get("timeline", {}),
        )
        comparison["rubric_scores"]["timeline_accuracy"] = timeline_score
        comparison["detailed_analysis"]["timeline_comparison"] = self._detail_timeline_comparison(
            simulated.get("timeline", {}),
            actual.get("timeline", {}),
        )

        # 3. Outcome Direction Accuracy
        outcome_score = self._score_outcome_accuracy(
            simulated.get("outcome_direction", {}),
            actual.get("outcome_direction", {}),
        )
        comparison["rubric_scores"]["outcome_direction_accuracy"] = outcome_score
        comparison["detailed_analysis"]["outcome_comparison"] = self._detail_outcome_comparison(
            simulated.get("outcome_direction", {}),
            actual.get("outcome_direction", {}),
        )

        # Calculate weighted overall accuracy
        weights = {
            "stakeholder_stance_accuracy": 0.35,
            "timeline_accuracy": 0.25,
            "outcome_direction_accuracy": 0.40,
        }
        overall = sum(
            comparison["rubric_scores"].get(k, 0) * v
            for k, v in weights.items()
        )
        comparison["overall_accuracy"] = round(overall, 3)

        return comparison

    def _score_stance_accuracy(
        self, simulated: dict, actual: dict
    ) -> float:
        """Score how well simulated stances match actual stances."""
        if not simulated or not actual:
            return 0.5

        scores = []
        for stakeholder, actual_stance in actual.items():
            if stakeholder in simulated:
                sim_stance = simulated[stakeholder].lower()
                act_stance = actual_stance.lower()

                # Check for keyword overlap
                positive_words = {"support", "agree", "favor", "approve", "accept"}
                negative_words = {"oppose", "disagree", "against", "reject", "block"}

                sim_positive = any(w in sim_stance for w in positive_words)
                sim_negative = any(w in sim_stance for w in negative_words)
                act_positive = any(w in act_stance for w in positive_words)
                act_negative = any(w in act_stance for w in negative_words)

                if (sim_positive and act_positive) or (sim_negative and act_negative):
                    scores.append(1.0)
                elif (sim_positive and act_negative) or (sim_negative and act_positive):
                    scores.append(0.0)
                else:
                    scores.append(0.5)
            else:
                scores.append(0.5)

        return round(sum(scores) / len(scores), 3) if scores else 0.5

    def _detail_stance_comparison(
        self, simulated: dict, actual: dict
    ) -> list[dict]:
        """Create detailed stance comparison."""
        comparison = []
        for stakeholder, actual_stance in actual.items():
            sim_stance = simulated.get(stakeholder, "Not simulated")
            comparison.append({
                "stakeholder": stakeholder,
                "simulated": sim_stance,
                "actual": actual_stance,
                "match": self._stance_matches(sim_stance, actual_stance),
            })
        return comparison

    def _stance_matches(self, simulated: str, actual: str) -> str:
        """Determine if stances match."""
        sim_lower = simulated.lower()
        act_lower = actual.lower()

        positive = {"support", "agree", "favor", "approve", "accept"}
        negative = {"oppose", "disagree", "against", "reject", "block"}

        sim_pos = any(w in sim_lower for w in positive)
        sim_neg = any(w in sim_lower for w in negative)
        act_pos = any(w in act_lower for w in positive)
        act_neg = any(w in act_lower for w in negative)

        if (sim_pos and act_pos) or (sim_neg and act_neg):
            return "match"
        elif (sim_pos and act_neg) or (sim_neg and act_pos):
            return "mismatch"
        return "unclear"

    def _score_timeline_accuracy(
        self, simulated: dict, actual: dict
    ) -> float:
        """Score timeline prediction accuracy."""
        if not simulated or not actual:
            return 0.5

        score = 0.5

        # Compare completion metrics
        sim_rounds = simulated.get("rounds_completed", 0)
        actual_duration = actual.get("announcement_to_close_months") or actual.get("crisis_start_to_failure_days")

        if actual_duration:
            # Normalize comparison
            if sim_rounds > 0:
                # Heuristic: more rounds = longer process
                if actual_duration > 20 and sim_rounds > 5:
                    score = 0.8
                elif actual_duration < 5 and sim_rounds <= 5:
                    score = 0.8
                else:
                    score = 0.5

        return score

    def _detail_timeline_comparison(
        self, simulated: dict, actual: dict
    ) -> dict:
        """Create detailed timeline comparison."""
        return {
            "simulated_rounds": simulated.get("rounds_completed", "N/A"),
            "actual_duration_months": actual.get("announcement_to_close_months", "N/A"),
            "actual_key_milestones": actual.get("key_milestones", []),
        }

    def _score_outcome_accuracy(
        self, simulated: dict, actual: dict
    ) -> float:
        """Score outcome direction prediction accuracy."""
        if not simulated or not actual:
            return 0.5

        scores = []
        bool_fields = [
            "deal_completed", "bank_failed", "consensus_reached",
            "aircraft_recertified", "comprehensive_regulation",
        ]

        for field in bool_fields:
            if field in actual:
                sim_val = simulated.get(field, None)
                act_val = actual[field]

                if sim_val is None:
                    scores.append(0.5)
                elif sim_val == act_val:
                    scores.append(1.0)
                else:
                    scores.append(0.0)

        return round(sum(scores) / len(scores), 3) if scores else 0.5

    def _detail_outcome_comparison(
        self, simulated: dict, actual: dict
    ) -> dict:
        """Create detailed outcome comparison."""
        comparison = {}
        for key, actual_val in actual.items():
            sim_val = simulated.get(key, "Not simulated")
            comparison[key] = {
                "simulated": sim_val,
                "actual": actual_val,
                "match": sim_val == actual_val if isinstance(actual_val, bool) else "N/A",
            }
        return comparison

    def get_bundled_cases(self) -> list[dict]:
        """Get list of bundled test cases.

        Returns:
            List of case summaries.
        """
        return [
            {
                "case_id": case["case_id"],
                "name": case["name"],
                "description": case["description"],
                "tags": case["tags"],
            }
            for case in BUNDLED_CASES
        ]

    def get_bundled_case(self, case_id: str) -> dict | None:
        """Get a specific bundled case by ID.

        Args:
            case_id: ID of the case to retrieve.

        Returns:
            Case data or None if not found.
        """
        for case in BUNDLED_CASES:
            if case["case_id"] == case_id:
                return case
        return None


# Global instance
backtesting_engine = BacktestingEngine()
