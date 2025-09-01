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
    parser = _create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Route to command handlers
    command_handlers = {
        "up": _handle_up_command,
        "down": _handle_down_command,
        "status": _handle_status_command,
        "logs": _handle_logs_command,
    }

    handler = command_handlers.get(args.command)
    if handler:
        handler(args)
    else:
        # Fallback for unexpected commands
        print(f"Command: {args.command}")


def _create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(prog="is-launcher", description="Unified Backend Launcher for InfiniteScribe")
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

    return parser


def _handle_up_command(args: argparse.Namespace) -> None:
    """Handle the 'up' command"""
    settings = Settings()
    base = settings.launcher

    # Resolve parameters with error handling
    mode = _resolve_mode(args.mode, base.default_mode)
    components = _resolve_components(args.components, base.components)
    agent_names = _resolve_agents(args.agents, base.agents.names)

    # Format and display the launch plan
    _print_launch_plan(mode, components, agent_names, base.api.reload)


def _handle_down_command(args: argparse.Namespace) -> None:
    """Handle the 'down' command"""
    print(f"Shutdown plan => grace={args.grace}s")


def _handle_status_command(args: argparse.Namespace) -> None:
    """Handle the 'status' command"""
    watch_mode = " (watch mode)" if args.watch else ""
    print(f"Status check{watch_mode}")


def _handle_logs_command(args: argparse.Namespace) -> None:
    """Handle the 'logs' command"""
    print(f"Viewing logs for component: {args.component}")


def _resolve_mode(arg_mode: str | None, default_mode: LaunchMode) -> LaunchMode:
    """Resolve launch mode from arguments or defaults"""
    return LaunchMode(arg_mode) if arg_mode else default_mode


def _resolve_components(arg_components: str | None, default_components: list[ComponentType]) -> list[ComponentType]:
    """Resolve components from arguments or defaults"""
    if arg_components is None:
        return default_components

    try:
        components_strs = _parse_list_like(arg_components)
        return _parse_components(components_strs)
    except ValueError as e:
        _error_exit(f"Invalid --components: {e}")


def _resolve_agents(arg_agents: str | None, default_agents: list[str] | None) -> list[str] | None:
    """Resolve agent names from arguments or defaults"""
    if arg_agents is None:
        return default_agents

    try:
        agent_names_list = _parse_list_like(arg_agents)
        if not agent_names_list:
            return None  # Treat empty list as None (no agents)

        # Validate using existing model
        return LauncherAgentsConfig(names=agent_names_list).names
    except (ValueError, ValidationError) as e:
        _error_exit(f"Invalid --agents: {e}")


def _print_launch_plan(
    mode: LaunchMode, components: list[ComponentType], agent_names: list[str] | None, reload: bool
) -> None:
    """Print the launch plan in a consistent format"""
    components_str = ",".join([c.value for c in components])
    agent_str = ",".join(agent_names) if agent_names else "<auto>"
    print(f"Launcher plan => mode={mode.value}, components=[{components_str}], agents={agent_str}, api.reload={reload}")


def _error_exit(message: str, exit_code: int = 2) -> None:
    """Print error message and exit with consistent formatting"""
    print(message, file=sys.stderr)
    sys.exit(exit_code)


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
    component_map = {
        ComponentType.API.value: ComponentType.API,
        ComponentType.AGENTS.value: ComponentType.AGENTS,
    }

    mapped: list[ComponentType] = []
    seen: set[ComponentType] = set()

    for raw in items:
        norm = raw.strip().lower()
        component = component_map.get(norm)
        if component is None:
            raise ValueError(f"Unknown component '{raw}' (allowed: {', '.join(component_map.keys())})")

        if component not in seen:
            mapped.append(component)
            seen.add(component)

    if not mapped:
        raise ValueError("Components list cannot be empty")
    return mapped


if __name__ == "__main__":
    main()
