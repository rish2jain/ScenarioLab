"""MCP (Model Context Protocol) server implementation for ScenarioLab."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.playbooks.manager import playbook_manager
from app.simulation.engine import SimulationEngine, simulation_engine
from app.simulation.models import (
    AgentConfig,
    EnvironmentType,
    SimulationConfig,
    SimulationStatus,
)

logger = logging.getLogger(__name__)


class MCPToolDefinition(BaseModel):
    """Definition of an MCP tool for discovery."""

    name: str
    description: str
    parameters: dict  # JSON Schema for parameters


class MCPToolResult(BaseModel):
    """Result of an MCP tool execution."""

    tool_name: str
    status: str  # "success", "error"
    result: dict | None = None
    error: str | None = None


class ScenarioLabMCPServer:
    """MCP server exposing ScenarioLab simulation tools."""

    def __init__(self, engine: SimulationEngine | None = None):
        self.simulation_engine = engine or simulation_engine
        self.tools = self._register_tools()
        self._simulation_tasks: dict[str, asyncio.Task] = {}

    def _on_simulation_task_done(self, task: asyncio.Task) -> None:
        """Log failures from asyncio.create_task(run_simulation); avoids lost exceptions."""
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            logger.debug("MCP background simulation task cancelled: %s", task.get_name())
            return
        if exc is not None:
            logger.error(
                "MCP background simulation task failed",
                exc_info=(type(exc), exc, exc.__traceback__),
            )

    def _on_simulation_task_done_for_id(self, simulation_id: str, task: asyncio.Task) -> None:
        """Done callback: log outcome and drop the task from the active map."""
        try:
            self._on_simulation_task_done(task)
        finally:
            self._simulation_tasks.pop(simulation_id, None)

    async def shutdown_background_simulation(self) -> None:
        """Cancel and await all spawned run_simulation tasks (e.g. process shutdown)."""
        tasks_snapshot = list(self._simulation_tasks.values())
        for t in tasks_snapshot:
            if not t.done():
                t.cancel()
        for t in tasks_snapshot:
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._simulation_tasks.clear()

    def _register_tools(self) -> dict[str, MCPToolDefinition]:
        """Register all MCP tools."""
        return {
            "scenariolab/simulate": MCPToolDefinition(
                name="scenariolab/simulate",
                description="Run a strategic simulation. Specify a playbook template and seed material to simulate boardroom dynamics, war games, negotiations, or integration planning.",
                parameters={
                    "type": "object",
                    "properties": {
                        "playbook": {
                            "type": "string",
                            "description": "Playbook ID (mna-culture-clash, regulatory-shock-test, competitive-response, boardroom-rehearsal)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Simulation name",
                        },
                        "seed_content": {
                            "type": "string",
                            "description": "Seed material content (text/markdown)",
                        },
                        "rounds": {
                            "type": "integer",
                            "description": "Number of simulation rounds",
                            "default": 10,
                        },
                        "environment": {
                            "type": "string",
                            "description": "Environment type (boardroom, war_room, negotiation, integration)",
                            "default": "boardroom",
                        },
                    },
                    "required": ["playbook", "name"],
                },
            ),
            "scenariolab/status": MCPToolDefinition(
                name="scenariolab/status",
                description="Check the status of a running or completed simulation.",
                parameters={
                    "type": "object",
                    "properties": {
                        "simulation_id": {
                            "type": "string",
                            "description": "Simulation ID",
                        },
                    },
                    "required": ["simulation_id"],
                },
            ),
            "scenariolab/results": MCPToolDefinition(
                name="scenariolab/results",
                description="Retrieve the results and report of a completed simulation.",
                parameters={
                    "type": "object",
                    "properties": {
                        "simulation_id": {
                            "type": "string",
                            "description": "Simulation ID",
                        },
                        "section": {
                            "type": "string",
                            "description": "Report section (executive_summary, risk_register, scenario_matrix, stakeholder_heatmap, full)",
                            "default": "full",
                        },
                    },
                    "required": ["simulation_id"],
                },
            ),
            "scenariolab/export": MCPToolDefinition(
                name="scenariolab/export",
                description="Export simulation results to a specific format.",
                parameters={
                    "type": "object",
                    "properties": {
                        "simulation_id": {
                            "type": "string",
                            "description": "Simulation ID",
                        },
                        "format": {
                            "type": "string",
                            "description": "Export format (json, markdown, pdf, miro)",
                            "default": "markdown",
                        },
                    },
                    "required": ["simulation_id"],
                },
            ),
            "scenariolab/playbooks/list": MCPToolDefinition(
                name="scenariolab/playbooks/list",
                description="List available consulting playbook templates for simulation.",
                parameters={"type": "object", "properties": {}},
            ),
            "scenariolab/graphiti/search": MCPToolDefinition(
                name="scenariolab/graphiti/search",
                description=(
                    "Search the Graphiti temporal knowledge graph for one simulation "
                    "(group_id = simulation_id). Requires GRAPHITI_ENABLED and OpenAI credentials."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "simulation_id": {
                            "type": "string",
                            "description": "Simulation UUID",
                        },
                        "query": {
                            "type": "string",
                            "description": "Natural language question",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max facts to return",
                            "default": 8,
                        },
                    },
                    "required": ["simulation_id", "query"],
                },
            ),
        }

    def get_tool_definitions(self) -> list[MCPToolDefinition]:
        """Return all tool definitions for MCP discovery."""
        return list(self.tools.values())

    async def execute_tool(self, tool_name: str, arguments: dict) -> MCPToolResult:
        """Execute an MCP tool by name with given arguments."""
        logger.info(f"Executing MCP tool: {tool_name}")

        if tool_name not in self.tools:
            return MCPToolResult(
                tool_name=tool_name,
                status="error",
                error=f"Unknown tool: {tool_name}",
            )

        try:
            if tool_name == "scenariolab/simulate":
                return await self._handle_simulate(arguments)
            elif tool_name == "scenariolab/status":
                return await self._handle_status(arguments)
            elif tool_name == "scenariolab/results":
                return await self._handle_results(arguments)
            elif tool_name == "scenariolab/export":
                return await self._handle_export(arguments)
            elif tool_name == "scenariolab/playbooks/list":
                return await self._handle_list_playbooks(arguments)
            elif tool_name == "scenariolab/graphiti/search":
                return await self._handle_graphiti_search(arguments)
            else:
                return MCPToolResult(
                    tool_name=tool_name,
                    status="error",
                    error=f"Tool handler not implemented: {tool_name}",
                )
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return MCPToolResult(
                tool_name=tool_name,
                status="error",
                error=str(e),
            )

    async def _handle_simulate(self, args: dict) -> MCPToolResult:
        """Handle scenariolab/simulate tool call."""
        playbook_id = args.get("playbook")
        name = args.get("name")
        seed_content = args.get("seed_content", "")
        rounds = args.get("rounds", 10)
        environment = args.get("environment", "boardroom")

        if not playbook_id or not name:
            return MCPToolResult(
                tool_name="scenariolab/simulate",
                status="error",
                error="Missing required parameters: playbook and name",
            )

        # Get playbook
        playbook = playbook_manager.get_playbook(playbook_id)
        if not playbook:
            available = playbook_manager.get_playbook_ids()
            return MCPToolResult(
                tool_name="scenariolab/simulate",
                status="error",
                error=f"Playbook not found: {playbook_id}. Available: {available}",
            )

        # Build agent configs from playbook roster
        agent_configs = []
        for entry in playbook.agent_roster:
            for i in range(entry.count):
                agent_name = entry.role
                if entry.count > 1:
                    agent_name = f"{entry.role} {i + 1}"

                agent_configs.append(
                    AgentConfig(
                        name=agent_name,
                        archetype_id=entry.archetype_id,
                        customization=entry.customization,
                    )
                )

        # Map environment string to EnvironmentType
        env_map = {
            "boardroom": EnvironmentType.BOARDROOM,
            "war_room": EnvironmentType.WAR_ROOM,
            "negotiation": EnvironmentType.NEGOTIATION,
            "integration": EnvironmentType.INTEGRATION,
        }
        env_type = env_map.get(environment.lower(), EnvironmentType.BOARDROOM)

        # Create simulation config
        config = SimulationConfig(
            name=name,
            description=f"MCP simulation using playbook: {playbook.name}",
            playbook_id=playbook_id,
            environment_type=env_type,
            agents=agent_configs,
            total_rounds=rounds,
            parameters={"seed_content": seed_content},
        )

        # Create simulation
        sim_state = await self.simulation_engine.create_simulation(config)

        # Start simulation in background (track each Task + log exceptions via done callback)
        sim_id = sim_state.config.id
        bg_task = asyncio.create_task(
            self.simulation_engine.run_simulation(sim_id),
            name=f"mcp-sim-{sim_id}",
        )
        self._simulation_tasks[sim_id] = bg_task
        bg_task.add_done_callback(lambda t, sid=sim_id: self._on_simulation_task_done_for_id(sid, t))

        return MCPToolResult(
            tool_name="scenariolab/simulate",
            status="success",
            result={
                "simulation_id": sim_id,
                "name": sim_state.config.name,
                "status": sim_state.status.value,
                "playbook": playbook_id,
                "rounds": rounds,
                "environment": environment,
                "agent_count": len(agent_configs),
                "message": "Simulation started. Use scenariolab/status to check progress.",
            },
        )

    async def _handle_status(self, args: dict) -> MCPToolResult:
        """Handle scenariolab/status tool call."""
        simulation_id = args.get("simulation_id")

        if not simulation_id:
            return MCPToolResult(
                tool_name="scenariolab/status",
                status="error",
                error="Missing required parameter: simulation_id",
            )

        sim_state = await self.simulation_engine.get_simulation(simulation_id)
        if not sim_state:
            return MCPToolResult(
                tool_name="scenariolab/status",
                status="error",
                error=f"Simulation not found: {simulation_id}",
            )

        # Calculate progress
        progress = 0
        if sim_state.config.total_rounds > 0:
            progress = min(
                100,
                int((sim_state.current_round / sim_state.config.total_rounds) * 100),
            )

        return MCPToolResult(
            tool_name="scenariolab/status",
            status="success",
            result={
                "simulation_id": simulation_id,
                "name": sim_state.config.name,
                "status": sim_state.status.value,
                "current_round": sim_state.current_round,
                "total_rounds": sim_state.config.total_rounds,
                "progress_percent": progress,
                "agent_count": len(sim_state.agents),
                "message_count": sum(len(r.messages) for r in sim_state.rounds),
                "created_at": sim_state.created_at,
                "updated_at": sim_state.updated_at,
            },
        )

    async def _handle_results(self, args: dict) -> MCPToolResult:
        """Handle scenariolab/results tool call."""
        simulation_id = args.get("simulation_id")
        section = args.get("section", "full")

        if not simulation_id:
            return MCPToolResult(
                tool_name="scenariolab/results",
                status="error",
                error="Missing required parameter: simulation_id",
            )

        sim_state = await self.simulation_engine.get_simulation(simulation_id)
        if not sim_state:
            return MCPToolResult(
                tool_name="scenariolab/results",
                status="error",
                error=f"Simulation not found: {simulation_id}",
            )

        if sim_state.status not in [SimulationStatus.COMPLETED, SimulationStatus.PAUSED]:
            return MCPToolResult(
                tool_name="scenariolab/results",
                status="error",
                error=f"Simulation not complete. Current status: {sim_state.status.value}",
            )

        # Build results based on section
        if section == "executive_summary":
            result = self._build_executive_summary(sim_state)
        elif section == "risk_register":
            result = self._build_risk_register(sim_state)
        elif section == "scenario_matrix":
            result = self._build_scenario_matrix(sim_state)
        elif section == "stakeholder_heatmap":
            result = self._build_stakeholder_heatmap(sim_state)
        else:  # full
            result = {
                "executive_summary": self._build_executive_summary(sim_state),
                "risk_register": self._build_risk_register(sim_state),
                "scenario_matrix": self._build_scenario_matrix(sim_state),
                "stakeholder_heatmap": self._build_stakeholder_heatmap(sim_state),
                "full_transcript": self._build_transcript(sim_state),
            }

        return MCPToolResult(
            tool_name="scenariolab/results",
            status="success",
            result=result,
        )

    async def _handle_export(self, args: dict) -> MCPToolResult:
        """Handle scenariolab/export tool call."""
        simulation_id = args.get("simulation_id")
        format_type = args.get("format", "markdown")

        if not simulation_id:
            return MCPToolResult(
                tool_name="scenariolab/export",
                status="error",
                error="Missing required parameter: simulation_id",
            )

        sim_state = await self.simulation_engine.get_simulation(simulation_id)
        if not sim_state:
            return MCPToolResult(
                tool_name="scenariolab/export",
                status="error",
                error=f"Simulation not found: {simulation_id}",
            )

        if format_type == "json":
            export_data = sim_state.model_dump()
        elif format_type == "markdown":
            export_data = self._export_to_markdown(sim_state)
        elif format_type == "pdf":
            # PDF export would require additional libraries
            export_data = {"error": "PDF export not implemented. Use markdown or json."}
        elif format_type == "miro":
            # Miro board export would require Miro API integration
            export_data = {"error": "Miro export not implemented. Use markdown or json."}
        else:
            return MCPToolResult(
                tool_name="scenariolab/export",
                status="error",
                error=f"Unsupported format: {format_type}",
            )

        return MCPToolResult(
            tool_name="scenariolab/export",
            status="success",
            result={
                "simulation_id": simulation_id,
                "format": format_type,
                "export_data": export_data,
                "filename": f"scenariolab_{simulation_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.{format_type}",
            },
        )

    async def _handle_list_playbooks(self, args: dict) -> MCPToolResult:
        """Handle scenariolab/playbooks/list tool call."""
        playbooks = playbook_manager.get_all_playbooks()

        return MCPToolResult(
            tool_name="scenariolab/playbooks/list",
            status="success",
            result={
                "count": len(playbooks),
                "playbooks": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "category": p.category,
                        "estimated_time_minutes": p.estimated_time_minutes,
                        "environment": p.environment,
                    }
                    for p in playbooks
                ],
            },
        )

    async def _handle_graphiti_search(self, args: dict) -> MCPToolResult:
        """Handle scenariolab/graphiti/search tool call."""
        from app.config import settings
        from app.graph.graphiti_service import get_graphiti, search_simulation_graph

        simulation_id = args.get("simulation_id")
        query = args.get("query")
        limit = int(args.get("limit", 8))

        if not simulation_id or not query:
            return MCPToolResult(
                tool_name="scenariolab/graphiti/search",
                status="error",
                error="Missing simulation_id or query",
            )

        if not settings.graphiti_enabled or get_graphiti() is None:
            return MCPToolResult(
                tool_name="scenariolab/graphiti/search",
                status="error",
                error="Graphiti is not enabled or failed to initialize",
            )

        facts = await search_simulation_graph(
            simulation_id,
            query,
            limit=max(1, min(limit, 25)),
        )
        return MCPToolResult(
            tool_name="scenariolab/graphiti/search",
            status="success",
            result={
                "simulation_id": simulation_id,
                "query": query,
                "facts": facts,
            },
        )

    def _build_executive_summary(self, sim_state: Any) -> dict:
        """Build executive summary from simulation state."""
        key_decisions = []
        for round_state in sim_state.rounds:
            for decision in round_state.decisions:
                if "evaluation" in decision:
                    key_decisions.append(decision["evaluation"])

        return {
            "simulation_name": sim_state.config.name,
            "playbook": sim_state.config.playbook_id,
            "total_rounds": sim_state.current_round,
            "total_messages": sum(len(r.messages) for r in sim_state.rounds),
            "agents": [a.name for a in sim_state.agents],
            "key_decisions": key_decisions[:5],  # Top 5 decisions
            "summary": sim_state.results_summary.get("summary", "Simulation completed successfully."),
        }

    def _build_risk_register(self, sim_state: Any) -> list[dict]:
        """Build risk register from simulation messages."""
        risks = []
        risk_keywords = ["risk", "threat", "concern", "issue", "problem", "challenge"]

        for round_state in sim_state.rounds:
            for msg in round_state.messages:
                content_lower = msg.content.lower()
                for keyword in risk_keywords:
                    if keyword in content_lower:
                        risks.append(
                            {
                                "round": round_state.round_number,
                                "identified_by": msg.agent_name,
                                "description": (msg.content[:200] + "..." if len(msg.content) > 200 else msg.content),
                                "category": "strategic",
                            }
                        )
                        break

        return risks[:20]  # Limit to top 20 risks

    def _build_scenario_matrix(self, sim_state: Any) -> dict:
        """Build scenario matrix from simulation state."""
        scenarios = []

        for round_state in sim_state.rounds:
            for decision in round_state.decisions:
                if "evaluation" in decision:
                    eval_data = decision["evaluation"]
                    scenarios.append(
                        {
                            "round": round_state.round_number,
                            "scenario": eval_data.get("scenario", "Unknown"),
                            "outcome": eval_data.get("outcome", "pending"),
                            "confidence": eval_data.get("confidence", "medium"),
                        }
                    )

        return {
            "scenarios": scenarios,
            "matrix_summary": f"{len(scenarios)} scenarios evaluated across {sim_state.current_round} rounds",
        }

    def _build_stakeholder_heatmap(self, sim_state: Any) -> dict:
        """Build stakeholder heatmap from simulation state."""
        agent_activity = {}

        for agent in sim_state.agents:
            agent_activity[agent.name] = {
                "archetype": agent.archetype_id,
                "messages": 0,
                "coalitions": agent.coalition_members,
                "final_stance": agent.current_stance,
            }

        for round_state in sim_state.rounds:
            for msg in round_state.messages:
                if msg.agent_name in agent_activity:
                    agent_activity[msg.agent_name]["messages"] += 1

        return {
            "stakeholders": agent_activity,
            "total_interactions": sum(a["messages"] for a in agent_activity.values()),
        }

    def _build_transcript(self, sim_state: Any) -> list[dict]:
        """Build full transcript from simulation state."""
        transcript = []

        for round_state in sim_state.rounds:
            for msg in round_state.messages:
                transcript.append(
                    {
                        "round": msg.round_number,
                        "phase": msg.phase,
                        "agent": msg.agent_name,
                        "role": msg.agent_role,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                    }
                )

        return transcript

    def _export_to_markdown(self, sim_state: Any) -> str:
        """Export simulation to markdown format."""
        lines = [
            f"# {sim_state.config.name}",
            "",
            f"**Playbook:** {sim_state.config.playbook_id}",
            f"**Environment:** {sim_state.config.environment_type.value}",
            f"**Rounds:** {sim_state.current_round}/{sim_state.config.total_rounds}",
            f"**Status:** {sim_state.status.value}",
            f"**Created:** {sim_state.created_at}",
            "",
            "## Agents",
            "",
        ]

        for agent in sim_state.agents:
            lines.append(f"- **{agent.name}** ({agent.archetype_id})")
            if agent.current_stance:
                lines.append(f"  - Final stance: {agent.current_stance}")
            lines.append("")

        lines.extend(
            [
                "## Simulation Transcript",
                "",
            ]
        )

        for round_state in sim_state.rounds:
            lines.append(f"### Round {round_state.round_number} - {round_state.phase}")
            lines.append("")

            for msg in round_state.messages:
                lines.append(f"**{msg.agent_name}** ({msg.agent_role})")
                lines.append(f"> {msg.content}")
                lines.append("")

            if round_state.decisions:
                lines.append("**Decisions:**")
                for decision in round_state.decisions:
                    lines.append(f"- {decision}")
                lines.append("")

        return "\n".join(lines)


# Global MCP server instance
mcp_server = ScenarioLabMCPServer()
