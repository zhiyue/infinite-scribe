"""CLI entry point for the unified backend launcher"""

import argparse
import os
import sys
import time

from src.core.logging import bind_service_context, configure_logging, get_logger

from .commands import handle_down_command, handle_logs_command, handle_status_command, handle_up_command


def main() -> None:
    """Main entry point for is-launcher command"""
    # Configure full backend logging (at the very beginning)
    environment = os.getenv("INFINITE_SCRIBE_ENV", "development")
    configure_logging(
        environment=environment,
        level="INFO",
        output_format="auto",  # development uses console, production uses json
        enable_stdlib_bridge=True,
        enable_file_logging=True,  # Enable file logging for shared logs
        file_log_format="structured",  # Use structured format for better readability
    )

    # Bind service context for CLI component
    bind_service_context(service="launcher", component="cli")
    logger = get_logger(__name__)

    start_time = time.time()

    parser = _create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    logger.info("CLI initialized", command=args.command, elapsed_ms=int((time.time() - start_time) * 1000))

    # Route to command handlers
    command_handlers = {
        "up": handle_up_command,
        "down": handle_down_command,
        "status": handle_status_command,
        "logs": handle_logs_command,
    }

    handler = command_handlers.get(args.command)
    if handler:
        try:
            handler(args)
            logger.info("Command completed successfully", command=args.command)
        except Exception as e:
            logger.error("Command failed", command=args.command, error_type=type(e).__name__, error_message=str(e))
            raise
    else:
        # Fallback for unexpected commands
        logger.warning("Unknown command", command=args.command)
        print(f"Command: {args.command}")


def _create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(prog="is-launcher", description="Unified Backend Launcher for InfiniteScribe")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    _add_up_command_parser(subparsers)
    _add_down_command_parser(subparsers)
    _add_status_command_parser(subparsers)
    _add_logs_command_parser(subparsers)

    return parser


def _add_up_command_parser(subparsers) -> None:
    """Add 'up' command parser"""
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
    up_parser.add_argument(
        "--agents-ready-timeout",
        dest="agents_ready_timeout",
        type=float,
        default=None,
        help=(
            "Agents readiness wait in seconds (optional). "
            "Waits for Kafka consumer/producer initialization per loaded agent. "
            "0 or unset disables waiting."
        ),
    )
    up_parser.add_argument("--reload", action="store_true", help="Enable hot-reload for development")
    up_parser.add_argument("--apply", action="store_true", help="Execute the plan (start services)")
    up_parser.add_argument("--json", action="store_true", help="Output structured JSON status")
    up_parser.add_argument(
        "--stay", action="store_true", help="Wait for shutdown signal after starting services (daemon mode)"
    )


def _add_down_command_parser(subparsers) -> None:
    """Add 'down' command parser"""
    down_parser = subparsers.add_parser("down", help="Stop services")
    down_parser.add_argument("--grace", type=int, default=10, help="Grace period in seconds for graceful shutdown")
    down_parser.add_argument("--apply", action="store_true", help="Execute the plan (stop services)")
    down_parser.add_argument("--json", action="store_true", help="Output structured JSON status")


def _add_status_command_parser(subparsers) -> None:
    """Add 'status' command parser"""
    status_parser = subparsers.add_parser("status", help="Check service status")
    status_parser.add_argument("--watch", action="store_true", help="Continuously watch status")


def _add_logs_command_parser(subparsers) -> None:
    """Add 'logs' command parser"""
    logs_parser = subparsers.add_parser("logs", help="View service logs")
    logs_parser.add_argument("component", choices=["api", "agents", "all"], help="Component to view logs for")


if __name__ == "__main__":
    main()
