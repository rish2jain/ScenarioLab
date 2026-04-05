"""Markdown exporter for simulation reports."""

import logging
from datetime import datetime

from app.reports.models import SimulationReport

logger = logging.getLogger(__name__)


async def export_to_markdown(report: SimulationReport) -> bytes:
    """Export report to well-formatted Markdown.

    Args:
        report: The simulation report to export

    Returns:
        Markdown bytes
    """
    try:
        lines = []

        # Header
        lines.extend(
            [
                f"# Simulation Report: {report.simulation_name}",
                "",
                f"**Report ID:** {report.id}",
                f"**Simulation ID:** {report.simulation_id}",
                f"**Status:** {report.status}",
                f"**Generated:** {report.created_at}",
                "",
                "---",
                "",
            ]
        )

        # Executive Summary
        if report.executive_summary:
            lines.extend(
                [
                    "## Executive Summary",
                    "",
                    report.executive_summary.summary_text,
                    "",
                ]
            )

            if report.executive_summary.key_findings:
                lines.extend(
                    [
                        "### Key Findings",
                        "",
                    ]
                )
                for finding in report.executive_summary.key_findings:
                    lines.append(f"- {finding}")
                lines.append("")

            if report.executive_summary.recommendations:
                lines.extend(
                    [
                        "### Key Recommendations",
                        "",
                    ]
                )
                for rec in report.executive_summary.recommendations:
                    priority_emoji = {
                        "high": "🔴",
                        "medium": "🟡",
                        "low": "🟢",
                    }.get(rec.priority, "⚪")
                    lines.extend(
                        [
                            f"{priority_emoji} **{rec.title}** " f"({rec.priority.upper()})",
                            "",
                            f"{rec.description}",
                            "",
                            f"*Rationale: {rec.rationale}*",
                            "",
                        ]
                    )

            lines.append("---\n")

        # Risk Register
        if report.risk_register and report.risk_register.items:
            lines.extend(
                [
                    "## Risk Register",
                    "",
                    f"**Total Risks:** {len(report.risk_register.items)}",
                    "",
                    "| Risk ID | Description | Probability | Impact | Owner |",
                    "|---------|-------------|-------------|--------|-------|",
                ]
            )

            for risk in report.risk_register.items:
                # Truncate description for table
                desc = risk.description[:50] + "..." if len(risk.description) > 50 else risk.description
                lines.append(
                    f"| {risk.risk_id} | {desc} | "
                    f"{risk.probability:.0%} | {risk.impact.upper()} | "
                    f"{risk.owner} |"
                )

            lines.extend(
                [
                    "",
                    "### Detailed Risk Descriptions",
                    "",
                ]
            )

            for risk in report.risk_register.items:
                lines.extend(
                    [
                        f"#### {risk.risk_id}: {risk.description[:60]}",
                        "",
                        f"- **Probability:** {risk.probability:.0%}",
                        f"- **Impact:** {risk.impact.upper()}",
                        f"- **Owner:** {risk.owner}",
                        f"- **Trigger:** {risk.trigger}",
                        "",
                        f"**Mitigation:** {risk.mitigation}",
                        "",
                    ]
                )

            lines.append("---\n")

        # Scenario Matrix
        if report.scenario_matrix and report.scenario_matrix.scenarios:
            dims = ", ".join(report.scenario_matrix.outcome_dimensions)
            lines.extend(
                [
                    "## Scenario Matrix",
                    "",
                    f"**Outcome Dimensions:** {dims}",
                    "",
                ]
            )

            for scenario in report.scenario_matrix.scenarios:
                prob_min, prob_max = scenario.probability_range
                lines.extend(
                    [
                        f"### {scenario.scenario_name}",
                        "",
                        f"**Probability Range:** {prob_min:.0%} - {prob_max:.0%}",
                        f"**Confidence:** {scenario.confidence_interval:.0%}",
                        "",
                        f"**Description:** {scenario.description}",
                        "",
                    ]
                )

                if scenario.key_drivers:
                    lines.extend(
                        [
                            "**Key Drivers:**",
                            "",
                        ]
                    )
                    for driver in scenario.key_drivers:
                        lines.append(f"- {driver}")
                    lines.append("")

                if scenario.outcomes:
                    lines.extend(
                        [
                            "**Outcomes by Dimension:**",
                            "",
                            "| Dimension | Outcome |",
                            "|-----------|---------|",
                        ]
                    )
                    for dim, outcome in scenario.outcomes.items():
                        lines.append(f"| {dim} | {outcome} |")
                    lines.append("")

            lines.append("---\n")

        # Stakeholder Heatmap
        if report.stakeholder_heatmap and report.stakeholder_heatmap.stakeholders:
            lines.extend(
                [
                    "## Stakeholder Heatmap",
                    "",
                    "| Stakeholder | Role | Position | Influence | Support |",
                    "|-------------|------|----------|-----------|---------|",
                ]
            )

            for sh in report.stakeholder_heatmap.stakeholders:
                # Position emoji
                pos_emoji = {
                    "strongly_support": "✅✅",
                    "support": "✅",
                    "neutral": "➖",
                    "oppose": "❌",
                    "strongly_oppose": "❌❌",
                }.get(sh.position, "➖")

                lines.append(
                    f"| {sh.stakeholder} | {sh.role} | "
                    f"{pos_emoji} {sh.position.replace('_', ' ').title()} | "
                    f"{sh.influence:.0%} | {sh.support_level:+.0%} |"
                )

            lines.extend(
                [
                    "",
                    "### Stakeholder Details",
                    "",
                ]
            )

            for sh in report.stakeholder_heatmap.stakeholders:
                lines.extend(
                    [
                        f"#### {sh.stakeholder} ({sh.role})",
                        "",
                        f"- **Position:** {sh.position.replace('_', ' ').title()}",
                        f"- **Influence Score:** {sh.influence:.0%}",
                        f"- **Support Level:** {sh.support_level:+.0%}",
                        "",
                    ]
                )

                if sh.key_concerns:
                    lines.append("**Key Concerns:**")
                    for concern in sh.key_concerns:
                        lines.append(f"- {concern}")
                    lines.append("")

            lines.append("---\n")

        # Review Checkpoints
        if report.checkpoints:
            lines.extend(
                [
                    "## Review Checkpoints",
                    "",
                    "| Checkpoint | Stage | Status | Notes |",
                    "|------------|-------|--------|-------|",
                ]
            )

            for cp in report.checkpoints:
                status_emoji = {
                    "approved": "✅",
                    "pending": "⏳",
                    "revision_requested": "🔄",
                }.get(cp.status, "❓")
                notes = cp.reviewer_notes[:30]
                lines.append(f"| {cp.checkpoint_id} | {cp.stage} | " f"{status_emoji} {cp.status} | {notes}... |")

            lines.append("")

        # Footer
        lines.extend(
            [
                "---",
                "",
                f"*Generated by MiroFish on {datetime.utcnow().isoformat()}*",
                "",
            ]
        )

        markdown = "\n".join(lines)
        return markdown.encode("utf-8")

    except Exception as e:
        logger.error(f"Error exporting to Markdown: {e}")
        raise
