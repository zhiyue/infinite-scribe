"""TOML configuration loader with environment variable interpolation"""

import os
import re
import tomllib
from pathlib import Path
from typing import Any

# Pre-compiled regex pattern for better performance
# Matches environment variable references in the form:
#   - ${VAR} (simple variable)
#   - ${VAR:-default} (variable with default value)
# Captures the contents inside the curly braces for further processing.
ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _convert_type(value: str) -> Any:
    """Convert string value to appropriate Python type"""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"

    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _replace_env_var(match: re.Match) -> str:
    """Replace environment variable reference with actual value"""
    var_expr = match.group(1)

    if ":-" in var_expr:
        var_name, default_value = var_expr.split(":-", 1)
        return os.environ.get(var_name.strip(), default_value)
    else:
        var_name = var_expr.strip()
        return os.environ.get(var_name, match.group(0))  # Return original if not found


def _interpolate_env_vars(value: Any) -> Any:
    """Recursively interpolate environment variables in configuration values

    Supports: ${VAR_NAME} and ${VAR_NAME:-default_value} syntax
    """
    if isinstance(value, str):
        result = ENV_VAR_PATTERN.sub(_replace_env_var, value)

        # Apply type conversion only if the entire string was a single env var
        if value.strip().startswith("${") and value.strip().endswith("}") and result != value:
            return _convert_type(result)
        return result

    elif isinstance(value, dict):
        return {k: _interpolate_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [_interpolate_env_vars(item) for item in value]

    return value


def load_toml_config(config_path: str | Path) -> dict[str, Any]:
    """Load TOML configuration file with environment variable interpolation

    Args:
        config_path: Path to TOML configuration file

    Returns:
        Configuration dictionary with interpolated values

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "rb") as f:
        config_data = tomllib.load(f)

    return _interpolate_env_vars(config_data)


def flatten_config(config: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
    """Flatten nested configuration dictionary

    Example: {'database': {'postgres_host': 'localhost'}} -> {'database__postgres_host': 'localhost'}
    """
    items: list[tuple[str, Any]] = []
    for k, v in config.items():
        new_key = f"{parent_key}__{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_config(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)
