"""TOML 配置加载器的单元测试"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from src.core.toml_loader import _interpolate_env_vars, flatten_config, load_toml_config


class TestInterpolateEnvVars:
    """测试环境变量插值功能"""

    def test_simple_string_no_vars(self):
        """测试不包含变量的简单字符串"""
        assert _interpolate_env_vars("hello world") == "hello world"
        assert _interpolate_env_vars("123") == "123"

    def test_env_var_exists(self):
        """测试环境变量存在的情况"""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            assert _interpolate_env_vars("${TEST_VAR}") == "test_value"
            assert _interpolate_env_vars("prefix_${TEST_VAR}_suffix") == "prefix_test_value_suffix"

    def test_env_var_not_exists(self):
        """测试环境变量不存在的情况"""
        with patch.dict(os.environ, clear=True):
            # 不存在且无默认值，保持原样
            assert _interpolate_env_vars("${UNKNOWN_VAR}") == "${UNKNOWN_VAR}"

    def test_env_var_with_default(self):
        """测试带默认值的环境变量"""
        with patch.dict(os.environ, clear=True):
            # 变量不存在，使用默认值
            assert _interpolate_env_vars("${VAR:-default}") == "default"
            assert _interpolate_env_vars("${VAR:-}") == ""

        with patch.dict(os.environ, {"VAR": "actual"}):
            # 变量存在，使用实际值
            assert _interpolate_env_vars("${VAR:-default}") == "actual"

    def test_type_conversion(self):
        """测试类型自动转换"""
        # 布尔值
        assert _interpolate_env_vars("${VAR:-true}") is True
        assert _interpolate_env_vars("${VAR:-false}") is False
        assert _interpolate_env_vars("${VAR:-True}") is True
        assert _interpolate_env_vars("${VAR:-FALSE}") is False

        # 整数
        assert _interpolate_env_vars("${VAR:-123}") == 123
        assert _interpolate_env_vars("${VAR:-0}") == 0
        assert _interpolate_env_vars("${VAR:--456}") == -456

        # 浮点数
        assert _interpolate_env_vars("${VAR:-3.14}") == 3.14
        assert _interpolate_env_vars("${VAR:-0.0}") == 0.0
        assert _interpolate_env_vars("${VAR:--2.5}") == -2.5

        # 字符串（不能转换的值）
        assert _interpolate_env_vars("${VAR:-hello}") == "hello"
        assert _interpolate_env_vars("${VAR:-123abc}") == "123abc"

    def test_multiple_vars(self):
        """测试多个变量的插值"""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "8080"}):
            result = _interpolate_env_vars("http://${HOST}:${PORT}/api")
            assert result == "http://localhost:8080/api"

    def test_nested_dict(self):
        """测试嵌套字典的递归处理"""
        config = {
            "database": {
                "host": "${DB_HOST:-localhost}",
                "port": "${DB_PORT:-5432}",
                "credentials": {
                    "user": "${DB_USER:-admin}",
                    "pass": "${DB_PASS}"
                }
            }
        }

        with patch.dict(os.environ, {"DB_PASS": "secret"}):
            result = _interpolate_env_vars(config)
            assert result["database"]["host"] == "localhost"
            assert result["database"]["port"] == 5432
            assert result["database"]["credentials"]["user"] == "admin"
            assert result["database"]["credentials"]["pass"] == "secret"

    def test_list_interpolation(self):
        """测试列表中的插值"""
        config = ["${VAR1:-item1}", "${VAR2:-item2}", "static"]

        with patch.dict(os.environ, {"VAR1": "custom1"}):
            result = _interpolate_env_vars(config)
            assert result == ["custom1", "item2", "static"]

    def test_mixed_types(self):
        """测试混合类型的配置"""
        config = {
            "string": "${STR:-hello}",
            "number": 42,
            "bool": True,
            "list": ["${ITEM:-default}", 123],
            "nested": {
                "value": "${NESTED:-nested_default}"
            }
        }

        result = _interpolate_env_vars(config)
        assert result["string"] == "hello"
        assert result["number"] == 42
        assert result["bool"] is True
        assert result["list"] == ["default", 123]
        assert result["nested"]["value"] == "nested_default"

    def test_partial_substitution(self):
        """测试部分替换（字符串中包含变量）"""
        with patch.dict(os.environ, {"USER": "alice", "DOMAIN": "example.com"}):
            result = _interpolate_env_vars("${USER}@${DOMAIN}")
            assert result == "alice@example.com"

            # 部分替换不进行类型转换
            result = _interpolate_env_vars("port:${PORT:-8080}")
            assert result == "port:8080"  # 保持字符串类型


class TestFlattenConfig:
    """测试配置扁平化功能"""

    def test_simple_dict(self):
        """测试简单字典的扁平化"""
        config = {"key": "value", "number": 42}
        assert flatten_config(config) == {"key": "value", "number": 42}

    def test_nested_dict(self):
        """测试嵌套字典的扁平化"""
        config = {
            "database": {
                "host": "localhost",
                "port": 5432
            },
            "api": {
                "timeout": 30
            }
        }

        expected = {
            "database__host": "localhost",
            "database__port": 5432,
            "api__timeout": 30
        }
        assert flatten_config(config) == expected

    def test_deeply_nested(self):
        """测试深度嵌套的扁平化"""
        config = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }

        expected = {"level1__level2__level3__value": "deep"}
        assert flatten_config(config) == expected

    def test_mixed_values(self):
        """测试包含各种类型值的扁平化"""
        config = {
            "string": "text",
            "number": 123,
            "bool": True,
            "list": [1, 2, 3],
            "nested": {
                "key": "value"
            }
        }

        expected = {
            "string": "text",
            "number": 123,
            "bool": True,
            "list": [1, 2, 3],
            "nested__key": "value"
        }
        assert flatten_config(config) == expected

    def test_empty_dict(self):
        """测试空字典"""
        assert flatten_config({}) == {}
        assert flatten_config({"empty": {}}) == {}


class TestLoadTomlConfig:
    """测试 TOML 配置加载功能"""

    def test_load_simple_toml(self):
        """测试加载简单的 TOML 文件"""
        toml_content = """
[server]
host = "localhost"
port = 8080

[database]
url = "postgresql://localhost/db"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()

            try:
                config = load_toml_config(f.name)
                assert config["server"]["host"] == "localhost"
                assert config["server"]["port"] == 8080
                assert config["database"]["url"] == "postgresql://localhost/db"
            finally:
                os.unlink(f.name)

    def test_load_toml_with_env_vars(self):
        """测试加载包含环境变量的 TOML 文件"""
        toml_content = """
[app]
name = "myapp"
debug = "${DEBUG:-false}"

[database]
host = "${DB_HOST:-localhost}"
port = "${DB_PORT:-5432}"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()

            try:
                with patch.dict(os.environ, {"DEBUG": "true", "DB_HOST": "prod.db.com"}):
                    config = load_toml_config(f.name)
                    assert config["app"]["name"] == "myapp"
                    assert config["app"]["debug"] is True
                    assert config["database"]["host"] == "prod.db.com"
                    assert config["database"]["port"] == 5432
            finally:
                os.unlink(f.name)

    def test_file_not_found(self):
        """测试文件不存在的情况"""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_toml_config("non_existent.toml")
        assert "配置文件不存在" in str(exc_info.value)

    def test_load_complex_toml(self):
        """测试加载复杂的 TOML 文件"""
        toml_content = """
title = "TOML Example"

[owner]
name = "${OWNER_NAME:-John Doe}"
dob = 1979-05-27T07:32:00-08:00

[database]
server = "${DB_SERVER}"
ports = [ 8001, 8001, 8002 ]
connection_max = 5000
enabled = "${DB_ENABLED:-true}"

[servers]

  [servers.alpha]
  ip = "10.0.0.1"
  dc = "eqdc10"

  [servers.beta]
  ip = "10.0.0.2"
  dc = "eqdc10"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()

            try:
                with patch.dict(os.environ, {"DB_SERVER": "192.168.1.1", "DB_ENABLED": "false"}):
                    config = load_toml_config(f.name)
                    assert config["title"] == "TOML Example"
                    assert config["owner"]["name"] == "John Doe"
                    assert config["database"]["server"] == "192.168.1.1"
                    assert config["database"]["enabled"] is False
                    assert config["servers"]["alpha"]["ip"] == "10.0.0.1"
            finally:
                os.unlink(f.name)

    def test_path_types(self):
        """测试不同类型的路径参数"""
        toml_content = '[test]\nkey = "value"'

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()

            try:
                # 字符串路径
                config1 = load_toml_config(f.name)
                assert config1["test"]["key"] == "value"

                # Path 对象
                config2 = load_toml_config(Path(f.name))
                assert config2["test"]["key"] == "value"
            finally:
                os.unlink(f.name)
