"""Miro board exporter for simulation reports."""

import logging

import httpx
from pydantic import BaseModel

from app.reports.models import (
    ExecutiveSummary,
    KeyRecommendation,
    RiskRegister,
    ScenarioMatrix,
    SimulationReport,
    StakeholderHeatmap,
)

logger = logging.getLogger(__name__)

# Miro supported colors for sticky notes
MIRO_COLORS = [
    "gray",
    "light_yellow",
    "yellow",
    "orange",
    "light_green",
    "green",
    "dark_green",
    "cyan",
    "light_pink",
    "pink",
    "violet",
    "red",
    "light_blue",
    "blue",
    "dark_blue",
    "black",
]

# Color mapping for risk severity
RISK_SEVERITY_COLORS = {
    "critical": "red",
    "high": "orange",
    "medium": "yellow",
    "low": "green",
}

# Color mapping for stakeholder positions
STAKEHOLDER_POSITION_COLORS = {
    "strongly_support": "dark_green",
    "support": "green",
    "neutral": "yellow",
    "oppose": "orange",
    "strongly_oppose": "red",
}

# Color mapping for recommendation priority
PRIORITY_COLORS = {
    "high": "red",
    "medium": "orange",
    "low": "green",
}


class MiroBoardConfig(BaseModel):
    """Configuration for creating a Miro board."""

    board_name: str
    description: str = ""


class MiroFrame(BaseModel):
    """Configuration for a Miro frame."""

    title: str
    x: float
    y: float
    width: float = 800
    height: float = 600


class MiroExportResult(BaseModel):
    """Result of exporting a report to Miro."""

    board_id: str
    board_url: str
    frames_created: int
    cards_created: int
    sticky_notes_created: int
    connectors_created: int


class MiroBoardExporter:
    """Export simulation reports to Miro boards."""

    BASE_URL = "https://api.miro.com/v2"

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    async def export_report(self, report: SimulationReport) -> MiroExportResult:
        """Export a full report to a Miro board.

        Args:
            report: The simulation report to export

        Returns:
            MiroExportResult with board details and stats
        """
        stats = {
            "frames_created": 0,
            "cards_created": 0,
            "sticky_notes_created": 0,
            "connectors_created": 0,
        }

        # 1. Create a new board
        board_name = f"MiroFish Report: {report.simulation_name}"
        board_id = await self._create_board(
            name=board_name,
            description=f"Simulation report for {report.simulation_name}",
        )

        # 2. Create frame hierarchy
        # Layout: Summary at top, then 3 frames below in a row
        # Frame positions:
        #   [Executive Summary]
        #   [Risk Register] [Scenario Matrix] [Stakeholder Heatmap]
        #   [Recommendations]

        # Executive Summary Frame (top)
        summary_frame = MiroFrame(
            title="Executive Summary",
            x=0,
            y=-700,
            width=2400,
            height=600,
        )
        summary_frame_id = await self._create_frame(board_id, summary_frame)
        stats["frames_created"] += 1

        if report.executive_summary:
            await self._export_executive_summary(board_id, report.executive_summary, summary_frame_id)

        # Risk Register Frame (middle left)
        risk_frame = MiroFrame(
            title="Risk Register",
            x=-800,
            y=0,
            width=750,
            height=600,
        )
        risk_frame_id = await self._create_frame(board_id, risk_frame)
        stats["frames_created"] += 1

        if report.risk_register:
            risk_stats = await self._export_risk_register(board_id, report.risk_register, risk_frame_id)
            stats["cards_created"] += risk_stats.get("cards", 0)
            stats["sticky_notes_created"] += risk_stats.get("sticky_notes", 0)
            stats["connectors_created"] += risk_stats.get("connectors", 0)

        # Scenario Matrix Frame (middle center)
        scenario_frame = MiroFrame(
            title="Scenario Matrix",
            x=0,
            y=0,
            width=750,
            height=600,
        )
        scenario_frame_id = await self._create_frame(board_id, scenario_frame)
        stats["frames_created"] += 1

        if report.scenario_matrix:
            scenario_stats = await self._export_scenario_matrix(board_id, report.scenario_matrix, scenario_frame_id)
            stats["sticky_notes_created"] += scenario_stats.get("sticky_notes", 0)

        # Stakeholder Heatmap Frame (middle right)
        stakeholder_frame = MiroFrame(
            title="Stakeholder Heatmap",
            x=800,
            y=0,
            width=750,
            height=600,
        )
        stakeholder_frame_id = await self._create_frame(board_id, stakeholder_frame)
        stats["frames_created"] += 1

        if report.stakeholder_heatmap:
            stakeholder_stats = await self._export_stakeholder_heatmap(
                board_id, report.stakeholder_heatmap, stakeholder_frame_id
            )
            stats["sticky_notes_created"] += stakeholder_stats.get("sticky_notes", 0)

        # Recommendations Frame (bottom)
        rec_frame = MiroFrame(
            title="Key Recommendations",
            x=0,
            y=700,
            width=2400,
            height=500,
        )
        rec_frame_id = await self._create_frame(board_id, rec_frame)
        stats["frames_created"] += 1

        if report.executive_summary and report.executive_summary.recommendations:
            rec_stats = await self._export_recommendations(
                board_id,
                report.executive_summary.recommendations,
                rec_frame_id,
            )
            stats["cards_created"] += rec_stats.get("cards", 0)

        # Build board URL
        board_url = f"https://miro.com/app/board/{board_id}/"

        return MiroExportResult(
            board_id=board_id,
            board_url=board_url,
            frames_created=stats["frames_created"],
            cards_created=stats["cards_created"],
            sticky_notes_created=stats["sticky_notes_created"],
            connectors_created=stats["connectors_created"],
        )

    async def _create_board(self, name: str, description: str = "") -> str:
        """Create a new Miro board.

        Args:
            name: The name of the board
            description: Optional description

        Returns:
            The board ID
        """
        url = f"{self.BASE_URL}/boards"
        payload = {
            "name": name,
            "description": description,
            "policy": {"permissionsPolicy": {"collaborationToolsStartAccess": "all_editors"}},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def _create_frame(
        self,
        board_id: str,
        frame: MiroFrame,
    ) -> str:
        """Create a frame on the board.

        Args:
            board_id: The board ID
            frame: Frame configuration

        Returns:
            The frame item ID
        """
        url = f"{self.BASE_URL}/boards/{board_id}/frames"
        payload = {
            "data": {
                "title": frame.title,
            },
            "style": {},
            "geometry": {
                "x": frame.x,
                "y": frame.y,
                "width": frame.width,
                "height": frame.height,
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def _create_sticky_note(
        self,
        board_id: str,
        content: str,
        x: float,
        y: float,
        color: str = "yellow",
        parent_id: str | None = None,
    ) -> str:
        """Create a sticky note.

        Args:
            board_id: The board ID
            content: The text content
            x: X position
            y: Y position
            color: Sticky note color (must be in MIRO_COLORS)
            parent_id: Optional parent frame ID

        Returns:
            The sticky note item ID
        """
        url = f"{self.BASE_URL}/boards/{board_id}/sticky_notes"
        payload = {
            "data": {
                "content": content,
            },
            "style": {
                "fillColor": color if color in MIRO_COLORS else "yellow",
            },
            "geometry": {
                "x": x,
                "y": y,
            },
        }

        if parent_id:
            payload["parent"] = {"id": parent_id}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def _create_app_card(
        self,
        board_id: str,
        title: str,
        description: str,
        x: float,
        y: float,
        parent_id: str | None = None,
    ) -> str:
        """Create an app card.

        Args:
            board_id: The board ID
            title: Card title
            description: Card description
            x: X position
            y: Y position
            parent_id: Optional parent frame ID

        Returns:
            The app card item ID
        """
        url = f"{self.BASE_URL}/boards/{board_id}/app_cards"
        payload = {
            "data": {
                "title": title,
                "description": description,
            },
            "geometry": {
                "x": x,
                "y": y,
                "width": 320,
                "height": 200,
                "rotation": 0,
            },
        }

        if parent_id:
            payload["parent"] = {"id": parent_id}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def _create_connector(
        self,
        board_id: str,
        start_item_id: str,
        end_item_id: str,
        caption: str = "",
    ) -> str:
        """Create a connector between items.

        Args:
            board_id: The board ID
            start_item_id: ID of the start item
            end_item_id: ID of the end item
            caption: Optional caption for the connector

        Returns:
            The connector item ID
        """
        url = f"{self.BASE_URL}/boards/{board_id}/connectors"
        payload = {
            "startItem": {"id": start_item_id},
            "endItem": {"id": end_item_id},
        }

        if caption:
            payload["caption"] = caption

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["id"]

    async def _export_executive_summary(
        self,
        board_id: str,
        summary: ExecutiveSummary,
        parent_frame_id: str,
    ) -> dict:
        """Export executive summary as sticky notes within a frame.

        Args:
            board_id: The board ID
            summary: The executive summary
            parent_frame_id: The parent frame ID

        Returns:
            Dict with stats
        """
        stats = {"sticky_notes": 0}

        # Main summary text (large sticky)
        await self._create_sticky_note(
            board_id,
            f"Summary:\n{summary.summary_text[:500]}",
            x=-1000,
            y=-200,
            color="light_yellow",
            parent_id=parent_frame_id,
        )
        stats["sticky_notes"] += 1

        # Key findings as separate stickies
        y_offset = -200
        for i, finding in enumerate(summary.key_findings[:6]):  # Limit to 6
            await self._create_sticky_note(
                board_id,
                f"Finding {i + 1}:\n{finding[:200]}",
                x=-400 + (i % 3) * 350,
                y=y_offset + (i // 3) * 250,
                color="light_green",
                parent_id=parent_frame_id,
            )
            stats["sticky_notes"] += 1

        return stats

    async def _export_risk_register(
        self,
        board_id: str,
        register: RiskRegister,
        parent_frame_id: str,
    ) -> dict:
        """Export risk register as app cards with connectors.

        Args:
            board_id: The board ID
            register: The risk register
            parent_frame_id: The parent frame ID

        Returns:
            Dict with stats
        """
        stats = {"cards": 0, "sticky_notes": 0, "connectors": 0}

        if not register.items:
            return stats

        # Create app cards for each risk
        card_ids = []
        cols = 2
        for i, risk in enumerate(register.items[:8]):  # Limit to 8 risks
            col = i % cols
            row = i // cols

            card_id = await self._create_app_card(
                board_id,
                title=f"Risk: {risk.risk_id}",
                description=(
                    f"{risk.description[:100]}...\n\n"
                    f"Probability: {risk.probability:.0%}\n"
                    f"Impact: {risk.impact.upper()}\n"
                    f"Owner: {risk.owner}\n\n"
                    f"Mitigation: {risk.mitigation[:100]}..."
                ),
                x=-300 + col * 350,
                y=-200 + row * 280,
                parent_id=parent_frame_id,
            )
            card_ids.append(card_id)
            stats["cards"] += 1

            # Add a sticky note with trigger info
            await self._create_sticky_note(
                board_id,
                f"Trigger: {risk.trigger}",
                x=-300 + col * 350,
                y=-200 + row * 280 + 120,
                color=RISK_SEVERITY_COLORS.get(risk.impact, "yellow"),
                parent_id=parent_frame_id,
            )
            stats["sticky_notes"] += 1

        # Create connectors between related risks
        for i in range(len(card_ids) - 1):
            if i % 2 == 0 and i + 1 < len(card_ids):
                await self._create_connector(
                    board_id,
                    card_ids[i],
                    card_ids[i + 1],
                    caption="related",
                )
                stats["connectors"] += 1

        return stats

    async def _export_scenario_matrix(
        self,
        board_id: str,
        matrix: ScenarioMatrix,
        parent_frame_id: str,
    ) -> dict:
        """Export scenario matrix as a visual grid.

        Args:
            board_id: The board ID
            matrix: The scenario matrix
            parent_frame_id: The parent frame ID

        Returns:
            Dict with stats
        """
        stats = {"sticky_notes": 0}

        if not matrix.scenarios:
            return stats

        # Header row with scenario names
        x_start = -300
        y_start = -200

        for col, scenario in enumerate(matrix.scenarios[:4]):
            # Scenario header
            prob_min, prob_max = scenario.probability_range
            await self._create_sticky_note(
                board_id,
                f"{scenario.scenario_name}\n({prob_min:.0%}-{prob_max:.0%})",
                x=x_start + col * 200,
                y=y_start,
                color="blue",
                parent_id=parent_frame_id,
            )
            stats["sticky_notes"] += 1

            # Key outcomes for this scenario
            if scenario.outcomes:
                outcome_text = "\n".join(f"{k}: {v[:50]}..." for k, v in list(scenario.outcomes.items())[:3])
                await self._create_sticky_note(
                    board_id,
                    outcome_text,
                    x=x_start + col * 200,
                    y=y_start + 150,
                    color="light_blue",
                    parent_id=parent_frame_id,
                )
                stats["sticky_notes"] += 1

            # Key drivers
            if scenario.key_drivers:
                drivers_text = "Drivers:\n" + "\n".join(f"• {d[:40]}" for d in scenario.key_drivers[:3])
                await self._create_sticky_note(
                    board_id,
                    drivers_text,
                    x=x_start + col * 200,
                    y=y_start + 300,
                    color="cyan",
                    parent_id=parent_frame_id,
                )
                stats["sticky_notes"] += 1

        return stats

    async def _export_stakeholder_heatmap(
        self,
        board_id: str,
        heatmap: StakeholderHeatmap,
        parent_frame_id: str,
    ) -> dict:
        """Export stakeholder heatmap as colored sticky notes.

        Args:
            board_id: The board ID
            heatmap: The stakeholder heatmap
            parent_frame_id: The parent frame ID

        Returns:
            Dict with stats
        """
        stats = {"sticky_notes": 0}

        if not heatmap.stakeholders:
            return stats

        # Sort by influence (highest first)
        sorted_stakeholders = sorted(
            heatmap.stakeholders,
            key=lambda s: s.influence,
            reverse=True,
        )[
            :12
        ]  # Limit to 12

        # Create sticky notes in a grid
        # Position based on support level (x-axis) and influence (y-axis)
        for stakeholder in sorted_stakeholders:
            # Map position to color
            color = STAKEHOLDER_POSITION_COLORS.get(stakeholder.position, "yellow")

            # Calculate position based on support and influence
            support_x = stakeholder.support_level * 300  # -300 to 300
            influence_y = -stakeholder.influence * 200  # 0 to -200

            # Add some randomness to avoid overlap
            content = (
                f"{stakeholder.stakeholder}\n"
                f"({stakeholder.role})\n\n"
                f"Influence: {stakeholder.influence:.0%}\n"
                f"Support: {stakeholder.support_level:+.0%}"
            )

            await self._create_sticky_note(
                board_id,
                content,
                x=support_x,
                y=influence_y,
                color=color,
                parent_id=parent_frame_id,
            )
            stats["sticky_notes"] += 1

        return stats

    async def _export_recommendations(
        self,
        board_id: str,
        recommendations: list[KeyRecommendation],
        parent_frame_id: str,
    ) -> dict:
        """Export recommendations as app cards.

        Args:
            board_id: The board ID
            recommendations: List of recommendations
            parent_frame_id: The parent frame ID

        Returns:
            Dict with stats
        """
        stats = {"cards": 0}

        if not recommendations:
            return stats

        # Create app cards for each recommendation
        x_start = -1000
        y_start = -100
        spacing = 400

        for i, rec in enumerate(recommendations[:6]):
            await self._create_app_card(
                board_id,
                title=f"{rec.priority.upper()}: {rec.title}",
                description=(f"{rec.description}\n\n" f"Rationale: {rec.rationale[:150]}..."),
                x=x_start + i * spacing,
                y=y_start,
                parent_id=parent_frame_id,
            )
            stats["cards"] += 1

            # Add priority indicator sticky
            priority_color = PRIORITY_COLORS.get(rec.priority, "yellow")
            await self._create_sticky_note(
                board_id,
                f"Priority: {rec.priority.upper()}",
                x=x_start + i * spacing,
                y=y_start - 150,
                color=priority_color,
                parent_id=parent_frame_id,
            )

        return stats

    async def export_report_mock(
        self,
        report: SimulationReport,
    ) -> dict:
        """Generate mock Miro board structure for testing without API token.

        Args:
            report: The simulation report to export

        Returns:
            Dict representing the board structure that would be created
        """
        mock_board = {
            "mock_mode": True,
            "note": ("Miro API token not configured. " "This is a mock representation."),
            "board_name": f"MiroFish Report: {report.simulation_name}",
            "board_url": None,
            "frames": [],
            "stats": {
                "frames_created": 0,
                "cards_created": 0,
                "sticky_notes_created": 0,
                "connectors_created": 0,
            },
        }

        # Executive Summary Frame
        summary_frame = {
            "title": "Executive Summary",
            "x": 0,
            "y": -700,
            "items": [],
        }

        if report.executive_summary:
            summary_frame["items"].append(
                {
                    "type": "sticky_note",
                    "content": ("Summary: " f"{report.executive_summary.summary_text[:300]}..."),
                    "color": "light_yellow",
                }
            )

            findings = report.executive_summary.key_findings[:6]
            for i, finding in enumerate(findings):
                summary_frame["items"].append(
                    {
                        "type": "sticky_note",
                        "content": f"Finding {i + 1}: {finding[:150]}...",
                        "color": "light_green",
                    }
                )

        mock_board["frames"].append(summary_frame)
        mock_board["stats"]["frames_created"] += 1
        notes_count = len(summary_frame["items"])
        mock_board["stats"]["sticky_notes_created"] += notes_count

        # Risk Register Frame
        risk_frame = {
            "title": "Risk Register",
            "x": -800,
            "y": 0,
            "items": [],
        }

        if report.risk_register:
            for risk in report.risk_register.items[:8]:
                risk_frame["items"].append(
                    {
                        "type": "app_card",
                        "title": f"Risk: {risk.risk_id}",
                        "description": (f"{risk.description[:100]}... " f"(Impact: {risk.impact})"),
                    }
                )
                risk_frame["items"].append(
                    {
                        "type": "sticky_note",
                        "content": f"Trigger: {risk.trigger}",
                        "color": RISK_SEVERITY_COLORS.get(risk.impact, "yellow"),
                    }
                )

        mock_board["frames"].append(risk_frame)
        mock_board["stats"]["frames_created"] += 1
        mock_board["stats"]["cards_created"] += sum(1 for item in risk_frame["items"] if item["type"] == "app_card")
        mock_board["stats"]["sticky_notes_created"] += sum(
            1 for item in risk_frame["items"] if item["type"] == "sticky_note"
        )

        # Scenario Matrix Frame
        scenario_frame = {
            "title": "Scenario Matrix",
            "x": 0,
            "y": 0,
            "items": [],
        }

        if report.scenario_matrix:
            for scenario in report.scenario_matrix.scenarios[:4]:
                prob_min, prob_max = scenario.probability_range
                scenario_frame["items"].append(
                    {
                        "type": "sticky_note",
                        "content": (f"{scenario.scenario_name}\n" f"Probability: {prob_min:.0%}-{prob_max:.0%}"),
                        "color": "blue",
                    }
                )

        mock_board["frames"].append(scenario_frame)
        mock_board["stats"]["frames_created"] += 1
        scenario_notes = len(scenario_frame["items"])
        mock_board["stats"]["sticky_notes_created"] += scenario_notes

        # Stakeholder Heatmap Frame
        stakeholder_frame = {
            "title": "Stakeholder Heatmap",
            "x": 800,
            "y": 0,
            "items": [],
        }

        if report.stakeholder_heatmap:
            for sh in report.stakeholder_heatmap.stakeholders[:12]:
                stakeholder_frame["items"].append(
                    {
                        "type": "sticky_note",
                        "content": (
                            f"{sh.stakeholder} ({sh.role})\n"
                            f"Influence: {sh.influence:.0%}, "
                            f"Support: {sh.support_level:+.0%}"
                        ),
                        "color": STAKEHOLDER_POSITION_COLORS.get(sh.position, "yellow"),
                    }
                )

        mock_board["frames"].append(stakeholder_frame)
        mock_board["stats"]["frames_created"] += 1
        sh_notes = len(stakeholder_frame["items"])
        mock_board["stats"]["sticky_notes_created"] += sh_notes

        # Recommendations Frame
        rec_frame = {
            "title": "Key Recommendations",
            "x": 0,
            "y": 700,
            "items": [],
        }

        has_recs = report.executive_summary and report.executive_summary.recommendations
        if has_recs:
            for rec in report.executive_summary.recommendations[:6]:
                rec_frame["items"].append(
                    {
                        "type": "app_card",
                        "title": f"{rec.priority.upper()}: {rec.title}",
                        "description": f"{rec.description[:150]}...",
                    }
                )
                rec_frame["items"].append(
                    {
                        "type": "sticky_note",
                        "content": f"Priority: {rec.priority.upper()}",
                        "color": PRIORITY_COLORS.get(rec.priority, "yellow"),
                    }
                )

        mock_board["frames"].append(rec_frame)
        mock_board["stats"]["frames_created"] += 1
        mock_board["stats"]["cards_created"] += sum(1 for item in rec_frame["items"] if item["type"] == "app_card")
        mock_board["stats"]["sticky_notes_created"] += sum(
            1 for item in rec_frame["items"] if item["type"] == "sticky_note"
        )

        return mock_board


async def export_to_miro(
    report: SimulationReport,
    api_token: str | None = None,
) -> dict:
    """Export a report to Miro.

    Args:
        report: The simulation report to export
        api_token: Optional Miro API token.
            If not provided, returns mock export.

    Returns:
        Dict with export result or mock structure
    """
    if not api_token:
        logger.warning("No Miro API token provided, returning mock export")
        exporter = MiroBoardExporter("")
        return await exporter.export_report_mock(report)

    try:
        exporter = MiroBoardExporter(api_token)
        result = await exporter.export_report(report)
        return {
            "mock_mode": False,
            "board_id": result.board_id,
            "board_url": result.board_url,
            "frames_created": result.frames_created,
            "cards_created": result.cards_created,
            "sticky_notes_created": result.sticky_notes_created,
            "connectors_created": result.connectors_created,
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"Miro API error: {e}")
        # Fall back to mock mode on auth failure
        if e.response.status_code in (401, 403):
            logger.warning("Miro API authentication failed, returning mock export")
            exporter = MiroBoardExporter("")
            mock_result = await exporter.export_report_mock(report)
            mock_result["auth_failed"] = True
            return mock_result
        raise
    except Exception as e:
        logger.error(f"Error exporting to Miro: {e}")
        raise
