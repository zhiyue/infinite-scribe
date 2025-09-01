"""CLI entry point for the unified backend launcher"""

import argparse
import sys


def main() -> None:
    """Main entry point for is-launcher command"""
    parser = argparse.ArgumentParser(prog="is-launcher", description="Unified Backend Launcher for InfiniteScribe")

    # Create subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # up command
    up_parser = subparsers.add_parser("up", help="Start services")
    up_parser.add_argument(
        "--mode", choices=["single", "multi"], default="single", help="Startup mode (single-process or multi-process)"
    )
    up_parser.add_argument("--components", default="api,agents", help="Comma-separated list of components to start")
    up_parser.add_argument("--agents", help="Comma-separated list of specific agents to start")
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

    # TODO: Implement command handlers
    print(f"Command: {args.command}")

    # For now, just return to make tests pass
    return


if __name__ == "__main__":
    main()
