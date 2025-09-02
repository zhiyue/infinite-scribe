"""Argument resolution utilities for CLI launcher"""

import json
import sys
from collections.abc import Iterable
from typing import NoReturn

from .types import ComponentType, LaunchMode


def resolve_mode(arg_mode: str | None, default_mode: LaunchMode) -> LaunchMode:
    """Resolve launch mode from arguments or defaults"""
    return LaunchMode(arg_mode) if arg_mode else default_mode


def resolve_components(arg_components: str | None, default_components: list[ComponentType]) -> list[ComponentType]:
    """Resolve components from arguments or defaults"""
    if arg_components is None:
        return default_components

    try:
        components_strs = parse_list_like(arg_components)
        return parse_components(components_strs)
    except ValueError as e:
        error_exit(f"Invalid --components: {e}")


def resolve_agents(arg_agents: str | None, default_agents: list[str] | None) -> list[str] | None:
    """Resolve agent names from arguments or defaults"""
    if arg_agents is None:
        return default_agents

    try:
        agent_names_list = parse_list_like(arg_agents)
        if not agent_names_list:
            return None  # Treat empty list as None (no agents)

        # Fast path: basic type validation only; skip pydantic for performance
        if not all(isinstance(x, str) and x for x in agent_names_list):
            raise ValueError("Agent names must be non-empty strings")
        return agent_names_list
    except ValueError as e:
        error_exit(f"Invalid --agents: {e}")


def parse_list_like(value: str) -> list[str]:
    """Parse a CLI list value which may be a JSON array or CSV string."""
    # Security: Limit input size to prevent DoS attacks
    max_input_size = 1024  # 1KB limit for CLI arguments
    max_list_items = 100   # Maximum number of items in list

    value = value.strip()

    # Validate input size
    if len(value) > max_input_size:
        raise ValueError(f"Input too large: {len(value)} bytes > {max_input_size} bytes limit")

    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON list: {e}") from e

        if not isinstance(parsed, list):
            raise ValueError("JSON value must be a list")

        # Validate list size
        if len(parsed) > max_list_items:
            raise ValueError(f"Too many items: {len(parsed)} > {max_list_items} limit")

        # Validate all items are strings
        if not all(isinstance(x, str) for x in parsed):
            raise ValueError("JSON list must contain only strings")

        # Validate individual string lengths
        for item in parsed:
            if len(item) > 256:  # Individual item size limit
                raise ValueError(f"Item too long: '{item[:50]}...' > 256 characters")

        return parsed

    # CSV fallback with validation
    items = [x.strip() for x in value.split(",") if x.strip()]

    # Validate CSV list size
    if len(items) > max_list_items:
        raise ValueError(f"Too many CSV items: {len(items)} > {max_list_items} limit")

    # Validate individual CSV item lengths
    for item in items:
        if len(item) > 256:
            raise ValueError(f"CSV item too long: '{item[:50]}...' > 256 characters")

    return items


def parse_components(items: Iterable[str]) -> list[ComponentType]:
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


def error_exit(message: str, exit_code: int = 2) -> NoReturn:
    """Print error message and exit with consistent formatting"""
    print(message, file=sys.stderr)
    sys.exit(exit_code)
