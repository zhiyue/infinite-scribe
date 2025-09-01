"""Unit tests for ApiAdapter"""

import asyncio
import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from launcher.adapters.api import ApiAdapter
from launcher.types import LaunchMode, ServiceStatus


@pytest.fixture
def api_adapter():
    """Create ApiAdapter for testing"""
    return ApiAdapter()


@pytest.fixture
def mock_uvicorn_server():
    """Create mock uvicorn server for testing"""
    server = Mock()
    server.serve = AsyncMock()
    return server


def test_api_adapter_initialization():
    """Test ApiAdapter initialization with defaults"""
    adapter = ApiAdapter()

    assert adapter.process is None
    assert adapter._task is None
    assert adapter.status == ServiceStatus.STOPPED
    assert adapter._host == "0.0.0.0"
    assert adapter._port == 8000


@pytest.mark.asyncio
async def test_api_adapter_single_mode_start(api_adapter, mock_uvicorn_server):
    """Test single-process mode startup"""
    with (
        patch("launcher.adapters.api.uvicorn.Server", return_value=mock_uvicorn_server),
        patch("launcher.adapters.api.asyncio.create_task") as mock_create_task,
    ):
        # Configure adapter via config and start
        api_adapter.config.update({"host": "127.0.0.1", "port": 8001, "reload": False, "mode": LaunchMode.SINGLE})
        result = await api_adapter.start()

        assert result is True
        assert api_adapter.status == ServiceStatus.RUNNING
        assert api_adapter._host == "127.0.0.1"
        assert api_adapter._port == 8001
        mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_api_adapter_single_mode_start_with_reload(api_adapter, mock_uvicorn_server):
    """Test single-process mode startup with reload enabled"""
    with (
        patch("launcher.adapters.api.uvicorn.Server", return_value=mock_uvicorn_server),
        patch("launcher.adapters.api.asyncio.create_task"),
    ):
        api_adapter.config.update({"host": "localhost", "port": 8000, "reload": True, "mode": "single"})
        result = await api_adapter.start()

        assert result is True
        assert api_adapter.status == ServiceStatus.RUNNING


@pytest.mark.asyncio
async def test_api_adapter_multi_mode_start_posix(api_adapter):
    """Test multi-process mode startup on POSIX systems"""
    mock_process = Mock()
    mock_process.pid = 12345
    mock_process.returncode = None

    with (
        patch("launcher.adapters.api.asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec,
        patch("launcher.adapters.process_utils.os.name", "posix"),
        patch("httpx.AsyncClient") as mock_httpx,
    ):
        # Mock successful health check response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx.return_value.__aenter__.return_value.get.return_value = mock_response
        api_adapter.config.update({"host": "0.0.0.0", "port": 8002, "reload": False, "mode": LaunchMode.MULTI})
        result = await api_adapter.start()

        assert result is True
        assert api_adapter.status == ServiceStatus.RUNNING
        assert api_adapter.process == mock_process

        # Verify subprocess arguments
        args, kwargs = mock_exec.call_args
        expected_args = ("-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8002")
        assert args[1:] == expected_args  # Skip python executable
        assert "preexec_fn" in kwargs


@pytest.mark.asyncio
async def test_api_adapter_multi_mode_start_windows(api_adapter):
    """Test multi-process mode startup on Windows"""
    mock_process = Mock()
    mock_process.pid = 12345
    mock_process.returncode = None

    with (
        patch("launcher.adapters.api.asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec,
        patch("launcher.adapters.process_utils.os.name", "nt"),
        patch("httpx.AsyncClient") as mock_httpx,
    ):
        # Mock successful health check response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx.return_value.__aenter__.return_value.get.return_value = mock_response
        api_adapter.config.update({"host": "127.0.0.1", "port": 8003, "reload": True, "mode": LaunchMode.MULTI})
        result = await api_adapter.start()

        assert result is True
        assert api_adapter.status == ServiceStatus.RUNNING

        # Verify subprocess arguments include reload
        args, kwargs = mock_exec.call_args
        assert "--reload" in args
        assert "creationflags" in kwargs
        assert kwargs["creationflags"] == 0x00000200


@pytest.mark.asyncio
async def test_api_adapter_start_invalid_mode(api_adapter):
    """Test startup with invalid mode"""
    api_adapter.config.update({"host": "localhost", "port": 8000, "reload": False, "mode": "invalid_mode"})
    with pytest.raises(ValueError, match="Unsupported launch mode"):
        await api_adapter.start()


@pytest.mark.asyncio
async def test_api_adapter_start_already_running(api_adapter):
    """Test starting adapter that's already running"""
    api_adapter.status = ServiceStatus.RUNNING

    result = await api_adapter.start()

    assert result is False


@pytest.mark.asyncio
async def test_api_adapter_start_exception(api_adapter):
    """Test startup failure handling"""
    with patch("launcher.adapters.api.uvicorn.Server", side_effect=Exception("Server error")):
        api_adapter.config.update({"host": "localhost", "port": 8000, "reload": False, "mode": LaunchMode.SINGLE})
        result = await api_adapter.start()

        assert result is False
        assert api_adapter.status == ServiceStatus.STOPPED


@pytest.mark.asyncio
async def test_api_adapter_stop_single_mode(api_adapter):
    """Test stopping single-process mode"""

    # Create a proper task mock using asyncio.Task
    async def dummy_task():
        pass

    mock_task = asyncio.create_task(dummy_task())
    # Cancel it immediately to test the cancellation path
    mock_task.cancel()

    api_adapter._task = mock_task
    api_adapter.status = ServiceStatus.RUNNING

    result = await api_adapter.stop(timeout=5)

    assert result is True
    assert api_adapter.status == ServiceStatus.STOPPED
    assert api_adapter._task is None


@pytest.mark.asyncio
async def test_api_adapter_stop_multi_mode_graceful(api_adapter):
    """Test graceful stop of multi-process mode"""
    mock_process = Mock()
    mock_process.returncode = None
    mock_process.pid = 12345
    mock_process.wait = AsyncMock()

    api_adapter.process = mock_process
    api_adapter.status = ServiceStatus.RUNNING

    with (
        patch("launcher.adapters.process_utils.os.name", "posix"),
        patch("launcher.adapters.process_utils.os.killpg") as mock_killpg,
        patch("launcher.adapters.process_utils.os.getpgid", return_value=12345) as mock_getpgid,
        patch("launcher.adapters.process_utils.asyncio.wait_for", return_value=None),
    ):
        result = await api_adapter.stop(timeout=10)

        assert result is True
        assert api_adapter.status == ServiceStatus.STOPPED
        assert api_adapter.process is None

        mock_getpgid.assert_called_with(12345)
        mock_killpg.assert_called_with(12345, signal.SIGTERM)


@pytest.mark.asyncio
async def test_api_adapter_stop_multi_mode_force_kill(api_adapter):
    """Test force kill after timeout in multi-process mode"""
    mock_process = Mock()
    mock_process.returncode = None
    mock_process.pid = 12345
    mock_process.wait = AsyncMock()

    api_adapter.process = mock_process
    api_adapter.status = ServiceStatus.RUNNING

    with (
        patch("launcher.adapters.process_utils.os.name", "posix"),
        patch("launcher.adapters.process_utils.os.killpg") as mock_killpg,
        patch("launcher.adapters.process_utils.os.getpgid", return_value=12345),
        patch("launcher.adapters.process_utils.asyncio.wait_for", side_effect=TimeoutError),
    ):
        result = await api_adapter.stop(timeout=2)

        assert result is True
        assert api_adapter.status == ServiceStatus.STOPPED

        # Should call SIGTERM first, then SIGKILL
        assert mock_killpg.call_count == 2
        mock_killpg.assert_any_call(12345, signal.SIGTERM)
        mock_killpg.assert_any_call(12345, signal.SIGKILL)


@pytest.mark.asyncio
async def test_api_adapter_stop_process_already_dead(api_adapter):
    """Test stopping when process is already dead"""
    mock_process = Mock()
    mock_process.returncode = 0  # Already terminated

    api_adapter.process = mock_process
    api_adapter.status = ServiceStatus.RUNNING

    result = await api_adapter.stop()

    assert result is True
    assert api_adapter.status == ServiceStatus.STOPPED
    assert api_adapter.process is None


@pytest.mark.asyncio
async def test_api_adapter_stop_not_running(api_adapter):
    """Test stopping when not running"""
    result = await api_adapter.stop()

    assert result is True


@pytest.mark.asyncio
async def test_api_adapter_stop_exception_handling(api_adapter):
    """Test stop with exception handling"""
    mock_task = Mock()
    mock_task.cancel = Mock(side_effect=Exception("Cancel error"))

    api_adapter._task = mock_task
    api_adapter.status = ServiceStatus.RUNNING

    result = await api_adapter.stop()

    # Should return True even with error (force cleanup)
    assert result is True
    assert api_adapter.status == ServiceStatus.STOPPED


def test_api_adapter_status(api_adapter):
    """Test status property via BaseAdapter"""
    assert api_adapter.status == ServiceStatus.STOPPED

    api_adapter.status = ServiceStatus.RUNNING
    assert api_adapter.status == ServiceStatus.RUNNING

    api_adapter.status = ServiceStatus.STARTING
    assert api_adapter.status == ServiceStatus.STARTING


def test_api_adapter_get_url(api_adapter):
    """Test get_url method"""
    assert api_adapter.get_url() == "http://0.0.0.0:8000"

    api_adapter._host = "127.0.0.1"
    api_adapter._port = 8080
    assert api_adapter.get_url() == "http://127.0.0.1:8080"


@pytest.mark.asyncio
async def test_api_adapter_windows_process_handling(api_adapter):
    """Test Windows-specific process handling"""
    mock_process = Mock()
    mock_process.returncode = None
    mock_process.pid = 12345
    mock_process.send_signal = Mock()
    mock_process.wait = AsyncMock()

    api_adapter.process = mock_process
    api_adapter.status = ServiceStatus.RUNNING

    with (
        patch("launcher.adapters.process_utils.os.name", "nt"),
        patch("launcher.adapters.process_utils.asyncio.wait_for", return_value=None),
        patch("launcher.adapters.process_utils.signal.CTRL_BREAK_EVENT", 7, create=True),
    ):
        result = await api_adapter.stop(timeout=5)

        assert result is True
        mock_process.send_signal.assert_called_with(7)  # CTRL_BREAK_EVENT value (patched)


@pytest.mark.asyncio
async def test_api_adapter_process_lookup_error_handling(api_adapter):
    """Test handling ProcessLookupError during stop"""
    mock_process = Mock()
    mock_process.returncode = None
    mock_process.pid = 12345

    api_adapter.process = mock_process
    api_adapter.status = ServiceStatus.RUNNING

    with (
        patch("launcher.adapters.process_utils.os.name", "posix"),
        patch("launcher.adapters.process_utils.os.killpg", side_effect=ProcessLookupError),
        patch("launcher.adapters.process_utils.os.getpgid", return_value=12345),
    ):
        result = await api_adapter.stop()

        # Should handle ProcessLookupError gracefully
        assert result is True
        assert api_adapter.status == ServiceStatus.STOPPED
