"""JSON exporter for simulation reports."""

import json
import logging

from app.reports.models import SimulationReport

logger = logging.getLogger(__name__)


async def export_to_json(report: SimulationReport) -> bytes:
    """Export report as structured JSON.

    Args:
        report: The simulation report to export

    Returns:
        JSON bytes
    """
    try:
        # Use Pydantic's model_dump for serialization
        data = report.model_dump()

        # Convert to JSON bytes
        json_str = json.dumps(data, indent=2, default=str)
        return json_str.encode("utf-8")

    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        raise
