"""TOML 配置加载器，支持环境变量插值"""

import os
import re
import tomllib
from pathlib import Path
from typing import Any


def _interpolate_env_vars(value: Any) -> Any:
    """递归地在配置值中插值环境变量

    支持的语法：
    - ${VAR_NAME} - 使用环境变量，如果不存在则报错
    - ${VAR_NAME:-default_value} - 使用环境变量，如果不存在则使用默认值
    """
    if isinstance(value, str):
        # 匹配 ${VAR} 或 ${VAR:-default} 模式
        pattern = r"\$\{([^}]+)\}"

        def replace_var(match):
            var_expr = match.group(1)

            # 检查是否有默认值
            if ":-" in var_expr:
                var_name, default_value = var_expr.split(":-", 1)
                return os.environ.get(var_name.strip(), default_value)
            else:
                var_name = var_expr.strip()
                if var_name in os.environ:
                    return os.environ[var_name]
                else:
                    # 如果环境变量不存在且没有默认值，保持原样
                    return match.group(0)

        # 如果整个值是一个环境变量引用，可能需要类型转换
        if value.strip().startswith("${") and value.strip().endswith("}"):
            result = re.sub(pattern, replace_var, value)
            # 尝试转换为适当的类型
            if result.lower() in ("true", "false"):
                return result.lower() == "true"
            try:
                # 尝试转换为整数
                return int(result)
            except ValueError:
                try:
                    # 尝试转换为浮点数
                    return float(result)
                except ValueError:
                    # 保持字符串
                    return result
        else:
            # 部分替换，保持字符串类型
            return re.sub(pattern, replace_var, value)

    elif isinstance(value, dict):
        # 递归处理字典
        return {k: _interpolate_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        # 递归处理列表
        return [_interpolate_env_vars(item) for item in value]

    else:
        # 其他类型直接返回
        return value


def load_toml_config(config_path: str | Path) -> dict[str, Any]:
    """加载 TOML 配置文件并进行环境变量插值

    Args:
        config_path: TOML 配置文件路径

    Returns:
        插值后的配置字典
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    # 读取 TOML 文件
    with open(config_path, "rb") as f:
        config_data = tomllib.load(f)

    # 进行环境变量插值
    interpolated_config = _interpolate_env_vars(config_data)

    return interpolated_config


def flatten_config(config: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
    """将嵌套的配置字典扁平化

    例如：
    {'database': {'postgres_host': 'localhost'}}
    变为：
    {'database__postgres_host': 'localhost'}
    """
    items = []
    for k, v in config.items():
        new_key = f"{parent_key}__{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_config(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)
