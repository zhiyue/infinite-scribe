"""
Test file for launcher module structure and skeleton files.
This follows TDD approach - tests are written before implementation.
"""

import subprocess
import sys
import tomllib
from pathlib import Path


class TestDirectoryStructure:
    """Test launcher directory structure"""

    def test_launcher_directory_exists(self):
        """Test that launcher main directory exists"""
        launcher_path = Path("src/launcher")
        assert launcher_path.exists(), f"Directory {launcher_path} does not exist"
        assert launcher_path.is_dir(), f"{launcher_path} is not a directory"

    def test_adapters_subdirectory_exists(self):
        """Test that adapters subdirectory exists"""
        adapters_path = Path("src/launcher/adapters")
        assert adapters_path.exists(), f"Directory {adapters_path} does not exist"
        assert adapters_path.is_dir(), f"{adapters_path} is not a directory"


class TestModuleFiles:
    """Test module file existence"""

    def test_core_module_files_exist(self):
        """Test all core module files are created"""
        launcher_path = Path("src/launcher")
        required_files = ["__init__.py", "cli.py", "orchestrator.py", "health.py", "types.py", "errors.py"]

        for file_name in required_files:
            file_path = launcher_path / file_name
            assert file_path.exists(), f"Missing file: {file_name}"
            assert file_path.is_file(), f"{file_name} is not a file"

    def test_adapter_files_exist(self):
        """Test adapter module files exist"""
        adapters_path = Path("src/launcher/adapters")
        required_files = ["__init__.py", "api.py", "agents.py"]

        for file_name in required_files:
            file_path = adapters_path / file_name
            assert file_path.exists(), f"Missing adapter file: {file_name}"
            assert file_path.is_file(), f"{file_name} is not a file"


class TestModuleImports:
    """Test module imports"""

    def test_cli_module_importable(self):
        """Test CLI module can be imported"""
        import src.launcher.cli

        assert hasattr(src.launcher.cli, "main"), "CLI module missing 'main' function"
        assert callable(src.launcher.cli.main), "'main' is not callable"

    def test_orchestrator_class_exists(self):
        """Test Orchestrator class is defined"""
        from src.launcher.orchestrator import Orchestrator

        assert isinstance(Orchestrator, type), "Orchestrator is not a class"
        # Check expected methods exist (they can be empty for now)
        assert hasattr(Orchestrator, "orchestrate_startup"), "Missing orchestrate_startup method"
        assert hasattr(Orchestrator, "orchestrate_shutdown"), "Missing orchestrate_shutdown method"

    def test_health_monitor_class_exists(self):
        """Test HealthMonitor class is defined"""
        from src.launcher.health import HealthMonitor

        assert isinstance(HealthMonitor, type), "HealthMonitor is not a class"
        assert hasattr(HealthMonitor, "check_health"), "Missing check_health method"

    def test_api_adapter_class_exists(self):
        """Test ApiAdapter class is defined"""
        from src.launcher.adapters.api import ApiAdapter

        assert isinstance(ApiAdapter, type), "ApiAdapter is not a class"
        assert hasattr(ApiAdapter, "start"), "Missing start method"
        assert hasattr(ApiAdapter, "stop"), "Missing stop method"
        assert hasattr(ApiAdapter, "status"), "Missing status method"

    def test_agents_adapter_class_exists(self):
        """Test AgentsAdapter class is defined"""
        from src.launcher.adapters.agents import AgentsAdapter

        assert isinstance(AgentsAdapter, type), "AgentsAdapter is not a class"
        assert hasattr(AgentsAdapter, "load"), "Missing load method"
        assert hasattr(AgentsAdapter, "start"), "Missing start method"
        assert hasattr(AgentsAdapter, "stop"), "Missing stop method"


class TestExceptionClasses:
    """Test exception class definitions"""

    def test_launcher_error_defined(self):
        """Test LauncherError base exception"""
        from src.launcher.errors import LauncherError

        assert issubclass(LauncherError, Exception), "LauncherError should inherit from Exception"

        # Test instantiation
        error = LauncherError("Test error")
        assert str(error) == "Test error"

    def test_derived_exceptions(self):
        """Test derived exception classes"""
        from src.launcher.errors import DependencyNotReadyError, LauncherError, ServiceStartupError

        assert issubclass(
            DependencyNotReadyError, LauncherError
        ), "DependencyNotReadyError should inherit from LauncherError"
        assert issubclass(ServiceStartupError, LauncherError), "ServiceStartupError should inherit from LauncherError"


class TestCLIEntryPoint:
    """Test CLI entry point registration"""

    def test_pyproject_entry_point_registered(self):
        """Test CLI entry point in pyproject.toml"""
        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)

        assert "project" in config, "Missing 'project' section in pyproject.toml"
        assert "scripts" in config["project"], "Missing 'scripts' section in project"
        assert "is-launcher" in config["project"]["scripts"], "Missing 'is-launcher' entry point"
        assert (
            config["project"]["scripts"]["is-launcher"] == "src.launcher.cli:main"
        ), "Incorrect entry point definition"

    def test_cli_help_command(self):
        """Test CLI help command executes"""
        result = subprocess.run([sys.executable, "-m", "src.launcher.cli", "--help"], capture_output=True, text=True)
        assert result.returncode == 0, f"CLI help command failed: {result.stderr}"
        # The help output should contain some expected text
        assert (
            "launcher" in result.stdout.lower() or "launcher" in result.stderr.lower()
        ), "Help output doesn't mention launcher"


class TestVersionInfo:
    """Test module version information"""

    def test_module_has_version(self):
        """Test launcher module has version info"""
        import src.launcher

        assert hasattr(src.launcher, "__version__"), "Module missing __version__ attribute"
        assert isinstance(src.launcher.__version__, str), "__version__ should be a string"
        assert len(src.launcher.__version__) > 0, "__version__ should not be empty"
        # Check version follows semantic versioning pattern
        import re

        pattern = r"^\d+\.\d+\.\d+.*$"
        assert re.match(
            pattern, src.launcher.__version__
        ), f"Version '{src.launcher.__version__}' doesn't follow semantic versioning"
