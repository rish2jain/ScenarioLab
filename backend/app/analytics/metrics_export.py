"""Export simulation metrics to various formats."""

import csv
import io
import json
import logging

from app.analytics.analytics_agent import SimulationMetrics

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Export simulation metrics to various formats."""

    @staticmethod
    async def to_json(metrics: SimulationMetrics) -> str:
        """Export as formatted JSON."""
        try:
            data = metrics.model_dump()
            return json.dumps(data, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to export metrics to JSON: {e}")
            return json.dumps({"error": str(e)})

    @staticmethod
    async def to_csv(metrics: SimulationMetrics) -> str:
        """Export as CSV format."""
        try:
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(["Metric", "Value"])

            # Write basic metrics
            writer.writerow(["simulation_id", metrics.simulation_id])
            writer.writerow(["compliance_violation_rate", f"{metrics.compliance_violation_rate}%"])
            ttc = metrics.time_to_consensus
            writer.writerow(["time_to_consensus", str(ttc) if ttc else "N/A"])
            writer.writerow(["policy_adoption_rate", f"{metrics.policy_adoption_rate}%"])

            # Write sentiment trajectory
            writer.writerow([])
            writer.writerow(["Sentiment Trajectory"])
            writer.writerow(["Round", "Positive", "Negative", "Neutral"])
            for item in metrics.sentiment_trajectory:
                writer.writerow(
                    [
                        item.get("round", ""),
                        item.get("positive", ""),
                        item.get("negative", ""),
                        item.get("neutral", ""),
                    ]
                )

            # Write role polarization
            writer.writerow([])
            writer.writerow(["Role Polarization Index"])
            writer.writerow(["Role", "Divergence Score"])
            for role, score in metrics.role_polarization_index.items():
                writer.writerow([role, score])

            # Write coalition events
            writer.writerow([])
            writer.writerow(["Coalition Formation Events"])
            writer.writerow(["Round", "Members", "Topic"])
            for event in metrics.coalition_formation_events:
                writer.writerow(
                    [
                        event.get("round", ""),
                        ", ".join(event.get("members", [])),
                        event.get("topic", ""),
                    ]
                )

            # Write turning points
            writer.writerow([])
            writer.writerow(["Key Turning Points"])
            writer.writerow(["Round", "Description", "Impact"])
            for tp in metrics.key_turning_points:
                writer.writerow(
                    [
                        tp.get("round", ""),
                        tp.get("description", ""),
                        tp.get("impact", ""),
                    ]
                )

            # Write agent activity scores
            writer.writerow([])
            writer.writerow(["Agent Activity Scores"])
            writer.writerow(["Agent ID", "Activity Level"])
            for agent_id, score in metrics.agent_activity_scores.items():
                writer.writerow([agent_id, score])

            # Write decision outcomes
            writer.writerow([])
            writer.writerow(["Decision Outcomes"])
            writer.writerow(["Round", "Decision", "Result"])
            for outcome in metrics.decision_outcomes:
                writer.writerow(
                    [
                        outcome.get("round", ""),
                        outcome.get("decision", ""),
                        outcome.get("result", ""),
                    ]
                )

            return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to export metrics to CSV: {e}")
            return f"error,{str(e)}"

    @staticmethod
    async def to_dashboard_data(metrics: SimulationMetrics) -> dict:
        """Format for frontend dashboard consumption."""
        try:
            data = {
                "summary": {
                    "simulation_id": metrics.simulation_id,
                    "compliance_violation_rate": (metrics.compliance_violation_rate),
                    "time_to_consensus": metrics.time_to_consensus,
                    "policy_adoption_rate": metrics.policy_adoption_rate,
                },
                "charts": {
                    "sentiment_over_time": {
                        "type": "line",
                        "title": "Sentiment Trajectory",
                        "data": {
                            "labels": [f"Round {s['round']}" for s in metrics.sentiment_trajectory],
                            "datasets": [
                                {
                                    "label": "Positive",
                                    "data": [s["positive"] for s in metrics.sentiment_trajectory],
                                    "color": "#10b981",
                                },
                                {
                                    "label": "Negative",
                                    "data": [s["negative"] for s in metrics.sentiment_trajectory],
                                    "color": "#ef4444",
                                },
                                {
                                    "label": "Neutral",
                                    "data": [s["neutral"] for s in metrics.sentiment_trajectory],
                                    "color": "#6b7280",
                                },
                            ],
                        },
                    },
                    "polarization_by_role": {
                        "type": "bar",
                        "title": "Role Polarization Index",
                        "data": {
                            "labels": list(metrics.role_polarization_index.keys()),
                            "datasets": [
                                {
                                    "label": "Divergence Score",
                                    "data": list(metrics.role_polarization_index.values()),
                                    "color": "#3b82f6",
                                }
                            ],
                        },
                    },
                    "agent_activity": {
                        "type": "bar",
                        "title": "Agent Activity Scores",
                        "data": {
                            "labels": list(metrics.agent_activity_scores.keys()),
                            "datasets": [
                                {
                                    "label": "Activity Level",
                                    "data": list(metrics.agent_activity_scores.values()),
                                    "color": "#8b5cf6",
                                }
                            ],
                        },
                    },
                    "decision_outcomes": {
                        "type": "pie",
                        "title": "Decision Outcomes",
                        "data": {
                            "labels": ["Approved", "Rejected", "Pending"],
                            "datasets": [
                                {
                                    "data": [
                                        sum(1 for d in metrics.decision_outcomes if d["result"] == "approved"),
                                        sum(1 for d in metrics.decision_outcomes if d["result"] == "rejected"),
                                        sum(1 for d in metrics.decision_outcomes if d["result"] == "pending"),
                                    ],
                                    "colors": ["#10b981", "#ef4444", "#f59e0b"],
                                }
                            ],
                        },
                    },
                },
                "tables": {
                    "coalition_events": metrics.coalition_formation_events,
                    "turning_points": metrics.key_turning_points,
                    "decisions": metrics.decision_outcomes,
                },
                "metrics": {
                    "sentiment_trajectory": metrics.sentiment_trajectory,
                    "role_polarization_index": (metrics.role_polarization_index),
                    "agent_activity_scores": metrics.agent_activity_scores,
                    "coalition_formation_events": (metrics.coalition_formation_events),
                    "key_turning_points": metrics.key_turning_points,
                    "decision_outcomes": metrics.decision_outcomes,
                },
            }

            return data

        except Exception as e:
            logger.error(f"Failed to format dashboard data: {e}")
            return {"error": str(e)}
