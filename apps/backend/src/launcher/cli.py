"""CLI entry point for the unified backend launcher"""

import argparse
import json
import sys
from collections.abc import Iterable

from pydantic import ValidationError

from src.core.config import Settings

from .config import LauncherAgentsConfig
from .types import ComponentType, LaunchMode


def main() -> None:
    """Main entry point for is-launcher command"""
    parser = argparse.ArgumentParser(prog="is-launcher", description="Unified Backend Launcher for InfiniteScribe")

    # Create subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # up command
    up_parser = subparsers.add_parser("up", help="Start services")
    up_parser.add_argument(
        "--mode",
        choices=["single", "multi", "auto"],
        default=None,
        help="Startup mode (default from settings.launcher.default_mode)",
    )
    up_parser.add_argument(
        "--components",
        default=None,
        help="Components to start (CSV or JSON list). Defaults to settings.launcher.components",
    )
    up_parser.add_argument(
        "--agents",
        default=None,
        help="Agent names (CSV or JSON list). Defaults to settings.launcher.agents.names",
    )
    up_parser.add_argument("--reload", action="store_true", help="Enable hot-reload for development")

    # down command
    down_parser = subparsers.add_parser("down", help="Stop services")
    down_parser.add_argument("--grace", type=int, default=10, help="Grace period in seconds for graceful shutdown")

    # status command
    status_parser = subparsers.add_parser("status", help="Check service status")
    status_parser.add_argument("--watch", action="store_true", help="Continuously watch status")

    # logs command
    logs_parser = subparsers.add_parser("logs", help="View service logs")
    logs_parser.add_argument("component", choices=["api", "agents", "all"], help="Component to view logs for")

    # Parse arguments
    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Command handlers (partial integration)
    if args.command == "up":
        settings = Settings()

        # Base values from settings.launcher
        base = settings.launcher

        # Resolve mode
        mode = LaunchMode(args.mode) if args.mode else base.default_mode

        # Resolve components
        if args.components is None:
            components = base.components
        else:
            try:
                components_strs = _parse_list_like(args.components)
                components = _parse_components(components_strs)
            except ValueError as e:
                print(f"Invalid --components: {e}", file=sys.stderr)
                sys.exit(2)

        # Resolve agents
        if args.agents is None:
            agent_names = base.agents.names
        else:
            try:
                agent_names_list = _parse_list_like(args.agents)
                # Validate using existing model (enforces non-empty list and name pattern/length)
                agent_names = LauncherAgentsConfig(names=agent_names_list).names
            except (ValueError, ValidationError) as e:
                print(f"Invalid --agents: {e}", file=sys.stderr)
                sys.exit(2)

        # Print resolved plan (placeholder for orchestrator integration)
        components_str = ",".join([c.value for c in components])
        agent_str = ",".join(agent_names) if agent_names else "<auto>"
        print(
            f"Launcher plan => mode={mode.value}, components=[{components_str}], agents={agent_str}, api.reload={base.api.reload}"
        )
        return

    # Fallback
    print(f"Command: {args.command}")
    return


def _parse_list_like(value: str) -> list[str]:
    """Parse a CLI list value which may be a JSON array or CSV string."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON list: {e}")
        if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
            raise ValueError("JSON value must be a list of strings")
        return parsed

    # CSV fallback
    items = [x.strip() for x in value.split(",") if x.strip()]
    return items


def _parse_components(items: Iterable[str]) -> list[ComponentType]:
    """Map strings to ComponentType with validation and de-duplication."""
    mapped: list[ComponentType] = []
    seen: set[ComponentType] = set()
    for raw in items:
        norm = raw.strip().lower()
        if norm == ComponentType.API.value:
            c = ComponentType.API
        elif norm == ComponentType.AGENTS.value:
            c = ComponentType.AGENTS
        else:
            raise ValueError(f"Unknown component '{raw}' (allowed: api, agents)")
        if c not in seen:
            mapped.append(c)
            seen.add(c)

    # Reuse pydantic validator logic implicitly: ensure non-empty and no duplicates
    if not mapped:
        raise ValueError("Components list cannot be empty")
    return mapped


if __name__ == "__main__":
    main()
