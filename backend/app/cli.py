"""
MiroFish CLI - Strategic Simulation from the Command Line

Usage:
    mirofish-sim simulate --playbook <name> --seed <file> --output <format>
    mirofish-sim list-playbooks
    mirofish-sim status <simulation_id>
    mirofish-sim results <simulation_id> --output <format>
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from app.mcp.server import mcp_server


def print_progress(message: str):
    """Print progress message to stderr."""
    print(message, file=sys.stderr)


def print_result(data: Any, format_type: str = "json"):
    """Print result to stdout."""
    if format_type == "json":
        print(json.dumps(data, indent=2))
    elif format_type == "markdown":
        if isinstance(data, str):
            print(data)
        else:
            print(json.dumps(data, indent=2))
    else:
        print(data)


async def simulate_local(args: argparse.Namespace) -> int:
    """Run simulation in local mode."""
    print_progress(f"Starting simulation with playbook: {args.playbook}")

    # Read seed content if provided
    seed_content = ""
    if args.seed:
        seed_path = Path(args.seed)
        if not seed_path.exists():
            print_progress(f"Error: Seed file not found: {args.seed}")
            return 1
        seed_content = seed_path.read_text(encoding="utf-8")
        print_progress(f"Loaded seed material: {len(seed_content)} characters")

    # Execute simulate tool
    result = await mcp_server.execute_tool(
        "mirofish/simulate",
        {
            "playbook": args.playbook,
            "name": args.name or f"CLI Simulation {int(time.time())}",
            "seed_content": seed_content,
            "rounds": args.rounds,
            "environment": args.environment,
        },
    )

    if result.status == "error":
        print_progress(f"Error: {result.error}")
        return 1

    simulation_id = result.result["simulation_id"]
    print_progress(f"Simulation created: {simulation_id}")
    print_progress(f"Status: {result.result['status']}")

    # Poll for completion
    print_progress("Waiting for simulation to complete...")
    max_wait = 300  # 5 minutes max
    wait_time = 0

    while wait_time < max_wait:
        await asyncio.sleep(2)
        wait_time += 2

        status_result = await mcp_server.execute_tool(
            "mirofish/status",
            {"simulation_id": simulation_id},
        )

        if status_result.status == "error":
            print_progress(f"Error checking status: {status_result.error}")
            return 1

        status = status_result.result["status"]
        progress = status_result.result["progress_percent"]
        print_progress(f"Status: {status} ({progress}% complete)")

        if status in ("completed", "failed"):
            break

    if status != "completed":
        print_progress(f"Simulation did not complete. Final status: {status}")
        return 1

    print_progress("Simulation completed successfully!")

    # Get results
    results_result = await mcp_server.execute_tool(
        "mirofish/results",
        {"simulation_id": simulation_id, "section": "full"},
    )

    if results_result.status == "error":
        print_progress(f"Error getting results: {results_result.error}")
        return 1

    # Output results
    if args.output == "json":
        print_result(results_result.result, "json")
    elif args.output == "markdown":
        export_result = await mcp_server.execute_tool(
            "mirofish/export",
            {"simulation_id": simulation_id, "format": "markdown"},
        )
        if export_result.status == "success":
            print_result(export_result.result["export_data"], "markdown")
        else:
            print_result(results_result.result, "json")
    else:
        print_result(results_result.result, "json")

    return 0


async def simulate_remote(args: argparse.Namespace, api_url: str) -> int:
    """Run simulation in remote mode via API."""
    print_progress(f"Connecting to API: {api_url}")

    # Read seed content if provided
    seed_content = ""
    if args.seed:
        seed_path = Path(args.seed)
        if not seed_path.exists():
            print_progress(f"Error: Seed file not found: {args.seed}")
            return 1
        seed_content = seed_path.read_text(encoding="utf-8")

    async with httpx.AsyncClient() as client:
        # Execute simulate tool
        response = await client.post(
            f"{api_url}/api/mcp/execute",
            json={
                "tool_name": "mirofish/simulate",
                "arguments": {
                    "playbook": args.playbook,
                    "name": args.name or f"CLI Simulation {int(time.time())}",
                    "seed_content": seed_content,
                    "rounds": args.rounds,
                    "environment": args.environment,
                },
            },
        )

        if response.status_code != 200:
            print_progress(f"Error: {response.text}")
            return 1

        data = response.json()
        simulation_id = data["result"]["simulation_id"]
        print_progress(f"Simulation created: {simulation_id}")

        # Poll for completion
        print_progress("Waiting for simulation to complete...")
        max_wait = 300
        wait_time = 0

        while wait_time < max_wait:
            await asyncio.sleep(2)
            wait_time += 2

            status_response = await client.post(
                f"{api_url}/api/mcp/execute",
                json={
                    "tool_name": "mirofish/status",
                    "arguments": {"simulation_id": simulation_id},
                },
            )

            if status_response.status_code != 200:
                continue

            status_data = status_response.json()
            status = status_data["result"]["status"]
            progress = status_data["result"]["progress_percent"]
            print_progress(f"Status: {status} ({progress}% complete)")

            if status in ("completed", "failed"):
                break

        if status != "completed":
            print_progress(
                f"Simulation did not complete. Final status: {status}"
            )
            return 1

        # Get results
        results_response = await client.post(
            f"{api_url}/api/mcp/execute",
            json={
                "tool_name": "mirofish/results",
                "arguments": {
                    "simulation_id": simulation_id,
                    "section": "full",
                },
            },
        )

        if results_response.status_code != 200:
            print_progress(f"Error getting results: {results_response.text}")
            return 1

        results_data = results_response.json()

        # Output results
        if args.output == "json":
            print_result(results_data["result"], "json")
        elif args.output == "markdown":
            export_response = await client.post(
                f"{api_url}/api/mcp/execute",
                json={
                    "tool_name": "mirofish/export",
                    "arguments": {
                        "simulation_id": simulation_id,
                        "format": "markdown",
                    },
                },
            )
            if export_response.status_code == 200:
                export_data = export_response.json()
                print_result(export_data["result"]["export_data"], "markdown")
            else:
                print_result(results_data["result"], "json")
        else:
            print_result(results_data["result"], "json")

    return 0


async def list_playbooks_local(args: argparse.Namespace) -> int:
    """List playbooks in local mode."""
    result = await mcp_server.execute_tool("mirofish/playbooks/list", {})

    if result.status == "error":
        print_progress(f"Error: {result.error}")
        return 1

    print_result(result.result, "json")
    return 0


async def list_playbooks_remote(args: argparse.Namespace, api_url: str) -> int:
    """List playbooks in remote mode."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/api/mcp/execute",
            json={
                "tool_name": "mirofish/playbooks/list",
                "arguments": {},
            },
        )

        if response.status_code != 200:
            print_progress(f"Error: {response.text}")
            return 1

        data = response.json()
        print_result(data["result"], "json")
        return 0


async def check_status_local(args: argparse.Namespace) -> int:
    """Check simulation status in local mode."""
    result = await mcp_server.execute_tool(
        "mirofish/status",
        {"simulation_id": args.simulation_id},
    )

    if result.status == "error":
        print_progress(f"Error: {result.error}")
        return 1

    print_result(result.result, "json")
    return 0


async def check_status_remote(args: argparse.Namespace, api_url: str) -> int:
    """Check simulation status in remote mode."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/api/mcp/execute",
            json={
                "tool_name": "mirofish/status",
                "arguments": {"simulation_id": args.simulation_id},
            },
        )

        if response.status_code != 200:
            print_progress(f"Error: {response.text}")
            return 1

        data = response.json()
        print_result(data["result"], "json")
        return 0


async def get_results_local(args: argparse.Namespace) -> int:
    """Get simulation results in local mode."""
    result = await mcp_server.execute_tool(
        "mirofish/results",
        {
            "simulation_id": args.simulation_id,
            "section": args.section,
        },
    )

    if result.status == "error":
        print_progress(f"Error: {result.error}")
        return 1

    if args.output == "json":
        print_result(result.result, "json")
    elif args.output == "markdown":
        export_result = await mcp_server.execute_tool(
            "mirofish/export",
            {"simulation_id": args.simulation_id, "format": "markdown"},
        )
        if export_result.status == "success":
            print_result(export_result.result["export_data"], "markdown")
        else:
            print_result(result.result, "json")
    else:
        print_result(result.result, "json")

    return 0


async def get_results_remote(args: argparse.Namespace, api_url: str) -> int:
    """Get simulation results in remote mode."""
    async with httpx.AsyncClient() as client:
        if args.output == "markdown":
            response = await client.post(
                f"{api_url}/api/mcp/execute",
                json={
                    "tool_name": "mirofish/export",
                    "arguments": {
                        "simulation_id": args.simulation_id,
                        "format": "markdown",
                    },
                },
            )
        else:
            response = await client.post(
                f"{api_url}/api/mcp/execute",
                json={
                    "tool_name": "mirofish/results",
                    "arguments": {
                        "simulation_id": args.simulation_id,
                        "section": args.section,
                    },
                },
            )

        if response.status_code != 200:
            print_progress(f"Error: {response.text}")
            return 1

        data = response.json()

        if args.output == "markdown":
            print_result(data["result"]["export_data"], "markdown")
        else:
            print_result(data["result"], "json")

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MiroFish - AI-Powered War Gaming and Scenario Simulation",
        prog="mirofish-sim",
    )

    parser.add_argument(
        "--api-url",
        help="API URL for remote mode (default: local mode)",
        default=None,
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    # simulate command
    sim_parser = subparsers.add_parser("simulate", help="Run a simulation")
    sim_parser.add_argument(
        "--playbook",
        required=True,
        help="Playbook template ID (e.g., mna-culture-clash)",
    )
    sim_parser.add_argument(
        "--seed",
        help="Path to seed material file",
    )
    sim_parser.add_argument(
        "--name",
        help="Simulation name",
    )
    sim_parser.add_argument(
        "--rounds",
        type=int,
        default=10,
        help="Number of rounds (default: 10)",
    )
    sim_parser.add_argument(
        "--environment",
        default="boardroom",
        choices=["boardroom", "war_room", "negotiation", "integration"],
        help="Environment type (default: boardroom)",
    )
    sim_parser.add_argument(
        "--output",
        default="json",
        choices=["json", "markdown"],
        help="Output format (default: json)",
    )

    # list-playbooks command
    subparsers.add_parser(
        "list-playbooks",
        help="List available playbook templates",
    )

    # status command
    status_parser = subparsers.add_parser(
        "status",
        help="Check simulation status",
    )
    status_parser.add_argument(
        "simulation_id",
        help="Simulation ID",
    )

    # results command
    results_parser = subparsers.add_parser(
        "results",
        help="Get simulation results",
    )
    results_parser.add_argument(
        "simulation_id",
        help="Simulation ID",
    )
    results_parser.add_argument(
        "--output",
        default="json",
        choices=["json", "markdown"],
        help="Output format (default: json)",
    )
    results_parser.add_argument(
        "--section",
        default="full",
        choices=[
            "full",
            "executive_summary",
            "risk_register",
            "scenario_matrix",
            "stakeholder_heatmap",
        ],
        help="Report section (default: full)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Determine mode (local or remote)
    api_url = args.api_url

    # Run appropriate command
    async def run_command():
        if args.command == "simulate":
            if api_url:
                return await simulate_remote(args, api_url)
            return await simulate_local(args)
        elif args.command == "list-playbooks":
            if api_url:
                return await list_playbooks_remote(args, api_url)
            return await list_playbooks_local(args)
        elif args.command == "status":
            if api_url:
                return await check_status_remote(args, api_url)
            return await check_status_local(args)
        elif args.command == "results":
            if api_url:
                return await get_results_remote(args, api_url)
            return await get_results_local(args)
        else:
            parser.print_help()
            return 1

    try:
        exit_code = asyncio.run(run_command())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_progress("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_progress(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
