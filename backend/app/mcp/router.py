"""FastAPI router for MCP endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.mcp.server import mcp_server

logger = logging.getLogger(__name__)


def _require_mcp_enabled():
    """Dependency that blocks MCP endpoints when the server is disabled."""
    if not settings.mcp_server_enabled:
        raise HTTPException(status_code=404, detail="MCP server is not enabled")


router = APIRouter(
    prefix="/api/mcp",
    tags=["mcp"],
    dependencies=[Depends(_require_mcp_enabled)],
)


class MCPToolExecuteRequest(BaseModel):
    """Request to execute an MCP tool."""

    tool_name: str
    arguments: dict = {}


class MCPStatusResponse(BaseModel):
    """MCP server status response."""

    enabled: bool
    version: str
    tools_available: int


@router.get("/tools")
async def list_tools() -> dict:
    """List available MCP tools (tool discovery)."""
    tools = mcp_server.get_tool_definitions()
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in tools
        ],
        "count": len(tools),
    }


@router.post("/execute")
async def execute_tool(request: MCPToolExecuteRequest) -> dict:
    """Execute an MCP tool."""
    try:
        result = await mcp_server.execute_tool(
            tool_name=request.tool_name,
            arguments=request.arguments,
        )

        if result.status == "error":
            raise HTTPException(
                status_code=400,
                detail={
                    "tool_name": result.tool_name,
                    "error": result.error,
                },
            )

        return {
            "tool_name": result.tool_name,
            "status": result.status,
            "result": result.result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing MCP tool {request.tool_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "tool_name": request.tool_name,
                "error": str(e),
            },
        )


@router.get("/status")
async def get_status() -> MCPStatusResponse:
    """Get MCP server status."""
    tools = mcp_server.get_tool_definitions()
    return MCPStatusResponse(
        enabled=settings.mcp_server_enabled,
        version="0.1.0",
        tools_available=len(tools),
    )
