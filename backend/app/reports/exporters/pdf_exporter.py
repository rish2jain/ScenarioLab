"""PDF exporter for simulation reports.

Note: Full PDF support requires libraries like WeasyPrint or ReportLab.
This implementation generates HTML that can be rendered to PDF.
"""

import logging
from datetime import datetime

from app.reports.models import SimulationReport

logger = logging.getLogger(__name__)


async def export_to_pdf(report: SimulationReport) -> bytes:
    """Export report to PDF.

    Currently returns HTML bytes that can be rendered to PDF using
    external tools like WeasyPrint, wkhtmltopdf, or browser print.

    Args:
        report: The simulation report to export

    Returns:
        HTML bytes that can be rendered to PDF
    """
    try:
        html = generate_report_html(report)
        return html.encode("utf-8")

    except Exception as e:
        logger.error(f"Error exporting to PDF: {e}")
        raise


def generate_report_html(report: SimulationReport) -> str:
    """Generate HTML representation of the report.

    Args:
        report: The simulation report

    Returns:
        HTML string
    """
    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, ' 'initial-scale=1.0">',
        f"    <title>Report: {report.simulation_name}</title>",
        "    <style>",
        "        body { font-family: Arial, sans-serif; line-height: 1.6; "
        "max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }",
        "        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; " "padding-bottom: 10px; }",
        "        h2 { color: #34495e; border-bottom: 2px solid #bdc3c7; " "padding-bottom: 5px; margin-top: 30px; }",
        "        h3 { color: #7f8c8d; }",
        "        table { border-collapse: collapse; width: 100%; " "margin: 20px 0; }",
        "        th, td { border: 1px solid #ddd; padding: 12px; " "text-align: left; }",
        "        th { background-color: #3498db; color: white; }",
        "        tr:nth-child(even) { background-color: #f2f2f2; }",
        "        .priority-high { color: #e74c3c; font-weight: bold; }",
        "        .priority-medium { color: #f39c12; font-weight: bold; }",
        "        .priority-low { color: #27ae60; font-weight: bold; }",
        "        .position-support { color: #27ae60; }",
        "        .position-oppose { color: #e74c3c; }",
        "        .position-neutral { color: #95a5a6; }",
        "        .info-box { background: #ecf0f1; padding: 15px; " "border-left: 4px solid #3498db; margin: 15px 0; }",
        "        .footer { margin-top: 40px; padding-top: 20px; "
        "border-top: 1px solid #bdc3c7; font-size: 0.9em; color: #7f8c8d; }",
        "    </style>",
        "</head>",
        "<body>",
    ]

    # Header
    html_parts.extend(
        [
            f"    <h1>{report.simulation_name}</h1>",
            '    <div class="info-box">',
            f"        <strong>Report ID:</strong> {report.id}<br>",
            f"        <strong>Simulation ID:</strong> {report.simulation_id}<br>",
            f"        <strong>Status:</strong> {report.status.upper()}<br>",
            f"        <strong>Generated:</strong> {report.created_at}",
            "    </div>",
        ]
    )

    # Executive Summary
    if report.executive_summary:
        summary = report.executive_summary.summary_text.replace(chr(10), "<br>")
        html_parts.extend(
            [
                "    <h2>Executive Summary</h2>",
                f"    <p>{summary}</p>",
            ]
        )

        if report.executive_summary.key_findings:
            html_parts.extend(
                [
                    "    <h3>Key Findings</h3>",
                    "    <ul>",
                ]
            )
            for finding in report.executive_summary.key_findings:
                html_parts.append(f"        <li>{finding}</li>")
            html_parts.append("    </ul>")

        if report.executive_summary.recommendations:
            html_parts.extend(
                [
                    "    <h3>Key Recommendations</h3>",
                    "    <table>",
                    "        <tr><th>Priority</th><th>Title</th>" "<th>Description</th></tr>",
                ]
            )
            for rec in report.executive_summary.recommendations:
                priority_class = f"priority-{rec.priority}"
                html_parts.append(
                    f"        <tr>"
                    f'<td class="{priority_class}">'
                    f"{rec.priority.upper()}</td>"
                    f"<td>{rec.title}</td>"
                    f"<td>{rec.description}<br>"
                    f"<em>Rationale: {rec.rationale}</em></td>"
                    f"</tr>"
                )
            html_parts.append("    </table>")

    # Risk Register
    if report.risk_register and report.risk_register.items:
        html_parts.extend(
            [
                "    <h2>Risk Register</h2>",
                f"    <p>Total Risks: {len(report.risk_register.items)}</p>",
                "    <table>",
                "        <tr>",
                "            <th>Risk ID</th>",
                "            <th>Description</th>",
                "            <th>Probability</th>",
                "            <th>Impact</th>",
                "            <th>Owner</th>",
                "        </tr>",
            ]
        )

        for risk in report.risk_register.items:
            impact_class = f"priority-{risk.impact}"
            html_parts.append(
                f"        <tr>"
                f"<td>{risk.risk_id}</td>"
                f"<td>{risk.description}</td>"
                f"<td>{risk.probability:.0%}</td>"
                f'<td class="{impact_class}">{risk.impact.upper()}</td>'
                f"<td>{risk.owner}</td>"
                f"</tr>"
            )

        html_parts.append("    </table>")

    # Scenario Matrix
    if report.scenario_matrix and report.scenario_matrix.scenarios:
        html_parts.extend(
            [
                "    <h2>Scenario Matrix</h2>",
                "    <table>",
                "        <tr><th>Scenario</th><th>Probability</th>" "<th>Key Drivers</th></tr>",
            ]
        )

        for scenario in report.scenario_matrix.scenarios:
            prob_min, prob_max = scenario.probability_range
            drivers = ", ".join(scenario.key_drivers[:3])
            html_parts.append(
                f"        <tr>"
                f"<td><strong>{scenario.scenario_name}</strong><br>"
                f"{scenario.description[:100]}...</td>"
                f"<td>{prob_min:.0%} - {prob_max:.0%}</td>"
                f"<td>{drivers}</td>"
                f"</tr>"
            )

        html_parts.append("    </table>")

    # Stakeholder Heatmap
    if report.stakeholder_heatmap and report.stakeholder_heatmap.stakeholders:
        html_parts.extend(
            [
                "    <h2>Stakeholder Heatmap</h2>",
                "    <table>",
                "        <tr>",
                "            <th>Stakeholder</th>",
                "            <th>Role</th>",
                "            <th>Position</th>",
                "            <th>Influence</th>",
                "            <th>Support</th>",
                "        </tr>",
            ]
        )

        for sh in report.stakeholder_heatmap.stakeholders:
            position_class = "position-neutral"
            if "support" in sh.position and "strongly" not in sh.position:
                position_class = "position-support"
            elif "oppose" in sh.position:
                position_class = "position-oppose"

            html_parts.append(
                f"        <tr>"
                f"<td>{sh.stakeholder}</td>"
                f"<td>{sh.role}</td>"
                f'<td class="{position_class}">'
                f"{sh.position.replace('_', ' ').title()}</td>"
                f"<td>{sh.influence:.0%}</td>"
                f"<td>{sh.support_level:+.0%}</td>"
                f"</tr>"
            )

        html_parts.append("    </table>")

    # Footer
    html_parts.extend(
        [
            '    <div class="footer">',
            f"        <p>Report generated by MiroFish on " f"{datetime.utcnow().isoformat()}</p>",
            "    </div>",
            "</body>",
            "</html>",
        ]
    )

    return "\n".join(html_parts)
