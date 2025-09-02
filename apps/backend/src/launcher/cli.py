"""CLI entry point for the unified backend launcher"""

import argparse
import asyncio
import json
import sys
from collections.abc import Callable, Iterable
from typing import NoReturn

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
    up_parser.add_argument("--apply", action="store_true", help="Execute the plan (start services)")
    up_parser.add_argument("--json", action="store_true", help="Output structured JSON status")
    up_parser.add_argument(
        "--stay", action="store_true", help="Wait for shutdown signal after starting services (daemon mode)"
    )

    # down command
    down_parser = subparsers.add_parser("down", help="Stop services")
    down_parser.add_argument("--grace", type=int, default=10, help="Grace period in seconds for graceful shutdown")
    down_parser.add_argument("--apply", action="store_true", help="Execute the plan (stop services)")
    down_parser.add_argument("--json", action="store_true", help="Output structured JSON status")

    # status command
    status_parser = subparsers.add_parser("status", help="Check service status")
    status_parser.add_argument("--watch", action="store_true", help="Continuously watch status")

    # logs command
    logs_parser = subparsers.add_parser("logs", help="View service logs")
    logs_parser.add_argument("component", choices=["api", "agents", "all"], help="Component to view logs for")

    return parser


def _handle_daemon_mode(orchestrator, service_names: list[str]) -> None:
    """
    Handle daemon mode: wait for shutdown signal and gracefully stop services

    :param orchestrator: The orchestrator instance to use for shutdown
    :param service_names: List of service names to shutdown
    """
    import asyncio as _asyncio

    from .signal_utils import wait_for_shutdown_signal

    print("🔄 Stay mode enabled, waiting for shutdown signal (Ctrl+C)...")

    try:
        # Wait for shutdown signal
        _asyncio.run(wait_for_shutdown_signal())
        print("📡 Shutdown signal received, stopping services...")

        # Gracefully shutdown services
        _asyncio.run(orchestrator.orchestrate_shutdown(service_names))
        print("✅ Services stopped gracefully")

    except KeyboardInterrupt:
        print("📡 Interrupted by user, stopping services...")
        try:
            _asyncio.run(orchestrator.orchestrate_shutdown(service_names))
            print("✅ Services stopped gracefully")
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")
            raise
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")
        # Re-raise to ensure proper exit code
        raise


def _handle_daemon_mode_with_early_registration(
    orchestrator,
    service_names: list[str],
    shutdown_event: asyncio.Event | None,
    cleanup_fn: Callable[[], None] | None,
) -> None:
    """
    Handle daemon mode with pre-registered signal handlers

    :param orchestrator: The orchestrator instance to use for shutdown
    :param service_names: List of service names to shutdown
    :param shutdown_event: Pre-registered asyncio.Event that will be set on signal
    :param cleanup_fn: Pre-registered cleanup function (should not be None when this function is called)
    """
    import asyncio as _asyncio

    # Additional safety check - this function should only be called when registration succeeded
    if cleanup_fn is None:
        raise RuntimeError("_handle_daemon_mode_with_early_registration called with failed registration")

    if shutdown_event is None:
        raise RuntimeError("_handle_daemon_mode_with_early_registration called with invalid shutdown_event")

    print("🔄 Stay mode enabled (early registration), waiting for shutdown signal (Ctrl+C)...")

    try:
        # Wait for the pre-registered shutdown signal (guaranteed to be registered since cleanup_fn is not None)
        _asyncio.run(shutdown_event.wait())

        print("📡 Shutdown signal received, stopping services...")

        # Gracefully shutdown services
        _asyncio.run(orchestrator.orchestrate_shutdown(service_names))
        print("✅ Services stopped gracefully")

    except KeyboardInterrupt:
        print("📡 Interrupted by user, stopping services...")
        try:
            _asyncio.run(orchestrator.orchestrate_shutdown(service_names))
            print("✅ Services stopped gracefully")
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")
            raise
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")
        # Re-raise to ensure proper exit code
        raise
    finally:
        # Clean up signal handlers (cleanup_fn guaranteed to be not None)
        try:
            cleanup_fn()
        except Exception as e:
            print(f"⚠️  Warning: Failed to cleanup signal handlers: {e}")


def _handle_up_command(args: argparse.Namespace) -> None:
    """Handle the 'up' command"""
    # Lightweight defaults to avoid importing Settings/Pydantic on perf-sensitive code paths
    base_default_mode = LaunchMode.SINGLE
    base_components = [ComponentType.API, ComponentType.AGENTS]
    base_agents_names: list[str] | None = None
    base_api_reload = False

    # Resolve parameters with error handling
    mode = _resolve_mode(args.mode, base_default_mode)
    components = _resolve_components(args.components, base_components)
    agent_names = _resolve_agents(args.agents, base_agents_names)

    # Format and display the launch plan
    _print_launch_plan(mode, components, agent_names, args.reload or base_api_reload)

    if args.apply:
        # Import heavy modules only when executing
        import asyncio as _asyncio

        from .config import LauncherAgentsConfig, LauncherApiConfig, LauncherConfigModel
        from .orchestrator import Orchestrator

        # When --stay mode is enabled, CLI takes unified signal handling ownership
        # so agent signal handlers should be disabled to prevent conflicts
        disable_agent_signals = getattr(args, "stay", False)

        # Early signal registration for --stay mode (before service startup)
        shutdown_event = None
        signal_cleanup = None
        if disable_agent_signals:
            from .signal_utils import create_shutdown_signal_handler

            shutdown_event, signal_cleanup = create_shutdown_signal_handler()

        config = LauncherConfigModel(
            default_mode=mode,
            components=components,
            api=LauncherApiConfig(reload=bool(args.reload)),
            agents=LauncherAgentsConfig(names=agent_names, disable_signal_handlers=disable_agent_signals),
        )
        orch = Orchestrator(config)
        service_names = [c.value for c in components]
        ok = _asyncio.run(orch.orchestrate_startup(service_names))

        status = {name: orch.get_service_state(name).value for name in service_names}
        result = {"ok": ok, "services": status}
        if args.json:
            import json as _json

            print(_json.dumps(result, ensure_ascii=False))
        else:
            print(f"Result => ok={ok}, services={status}")

        # Handle daemon mode if requested
        if getattr(args, "stay", False):
            # Critical: Check if early signal registration succeeded (signal_cleanup is not None)
            # This determines whether SIGTERM can be handled via early registration or needs fallback
            if signal_cleanup is not None:
                print("✅ Using early signal registration for daemon mode")
                # Early registration successful, use pre-registered handlers
                _handle_daemon_mode_with_early_registration(orch, service_names, shutdown_event, signal_cleanup)
            else:
                print("⚠️  Early signal registration failed (no event loop), using proven fallback method")
                print("   → SIGTERM handling guaranteed via fallback path")
                # Early registration failed - use original method which registers signals within event loop context
                # This path ensures both SIGINT and SIGTERM are properly handled
                _handle_daemon_mode(orch, service_names)
        else:
            # Default behavior: exit immediately after startup
            print("💡 Use --stay to wait for shutdown signal.")


def _handle_down_command(args: argparse.Namespace) -> None:
    """Handle the 'down' command"""
    if args.grace < 0:
        _error_exit(f"Invalid --grace value: {args.grace}. Grace period must be >= 0 seconds")

    print(f"Shutdown plan => grace={args.grace}s")
    if args.apply:
        import asyncio as _asyncio

        from .config import LauncherConfigModel
        from .orchestrator import Orchestrator

        # Use defaults; stopping is idempotent
        config = LauncherConfigModel()
        orch = Orchestrator(config)
        # Attempt to stop known components
        service_names = [c.value for c in config.components]
        ok = _asyncio.run(orch.orchestrate_shutdown(service_names))
        status = {name: orch.get_service_state(name).value for name in service_names}
        result = {"ok": ok, "services": status}
        if args.json:
            import json as _json

            print(_json.dumps(result, ensure_ascii=False))
        else:
            print(f"Result => ok={ok}, services={status}")


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

        # Fast path: basic type validation only; skip pydantic for performance
        if not all(isinstance(x, str) and x for x in agent_names_list):
            raise ValueError("Agent names must be non-empty strings")
        return agent_names_list
    except ValueError as e:
        _error_exit(f"Invalid --agents: {e}")


def _print_launch_plan(
    mode: LaunchMode, components: list[ComponentType], agent_names: list[str] | None, reload: bool
) -> None:
    """Print the launch plan in a consistent format"""
    components_str = ",".join([c.value for c in components])
    agent_str = ",".join(agent_names) if agent_names else "<auto>"
    print(f"Launcher plan => mode={mode.value}, components=[{components_str}], agents={agent_str}, api.reload={reload}")


def _error_exit(message: str, exit_code: int = 2) -> NoReturn:
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
            raise ValueError(f"Invalid JSON list: {e}") from e
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
