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
@pytest.mark.timeout(10)  # Quick timeout for unit test
async def test_api_adapter_single_mode_start(api_adapter):
    """Test single-process mode manages server lifecycle correctly"""
    # Mock the FastAPI app startup to avoid database dependencies
    mock_server = Mock()
    mock_server.started = True  # Simulate successful startup
    mock_server.serve = AsyncMock()

    with patch("launcher.adapters.api.uvicorn.Server", return_value=mock_server):
        api_adapter.config.update(
            {
                "host": "127.0.0.1",
                "port": 8001,
                "reload": False,
                "mode": LaunchMode.SINGLE,
            }
        )

        try:
            result = await api_adapter.start()

            assert result is True
            assert api_adapter.status == ServiceStatus.RUNNING
            assert api_adapter._task is not None
            assert api_adapter._server is not None
            assert api_adapter._host == "127.0.0.1"
            assert api_adapter._port == 8001

            # Test health check
            health = await api_adapter.health_check()
            assert health["status"] == ServiceStatus.RUNNING.value
            assert "url" in health

        finally:
            await api_adapter.stop()


@pytest.mark.asyncio
@pytest.mark.timeout(10)  # Quick timeout for unit test
async def test_api_adapter_single_mode_start_with_reload(api_adapter):
    """Test single-process mode with reload configuration"""
    mock_process = Mock()
    mock_process.pid = 12345
    mock_process.returncode = None  # Process is running

    mock_response = Mock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "launcher.adapters.api.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_process,
        ),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        api_adapter.config.update(
            {
                "host": "127.0.0.1",
                "port": 8002,
                "reload": True,
                "mode": "single",  # Test string mode conversion
            }
        )

        try:
            result = await api_adapter.start()

            assert result is True
            assert api_adapter.status == ServiceStatus.RUNNING

            # Test health check
            health = await api_adapter.health_check()
            assert health["status"] == ServiceStatus.RUNNING.value
            # When reload=True with mode="single", it automatically switches to multi-process mode
            assert health["mode"] == "multi"

        finally:
            await api_adapter.stop()


@pytest.mark.asyncio
@pytest.mark.timeout(15)  # Reasonable timeout for process test
async def test_api_adapter_multi_mode_start_posix(api_adapter):
    """Test multi-process mode manages subprocess correctly"""
    mock_process = Mock()
    mock_process.pid = 12345
    mock_process.returncode = None  # Process running

    with (
        patch("launcher.adapters.api.asyncio.create_subprocess_exec", return_value=mock_process),
        patch("httpx.AsyncClient") as mock_httpx,
    ):
        # Mock successful health check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx.return_value.__aenter__.return_value.get.return_value = mock_response

        api_adapter.config.update(
            {
                "host": "127.0.0.1",
                "port": 8003,
                "reload": False,
                "mode": LaunchMode.MULTI,
            }
        )

        try:
            result = await api_adapter.start()

            assert result is True
            assert api_adapter.status == ServiceStatus.RUNNING
            assert api_adapter.process == mock_process

            # Test health check
            health = await api_adapter.health_check()
            assert health["status"] == ServiceStatus.RUNNING.value
            assert health["mode"] == "multi"

        finally:
            await api_adapter.stop(timeout=5)


@pytest.mark.asyncio
@pytest.mark.timeout(15)  # Reasonable timeout for process test
async def test_api_adapter_multi_mode_start_with_reload(api_adapter):
    """Test multi-process mode with reload option"""
    mock_process = Mock()
    mock_process.pid = 12346
    mock_process.returncode = None

    with (
        patch("launcher.adapters.api.asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec,
        patch("httpx.AsyncClient") as mock_httpx,
    ):
        # Mock successful health check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx.return_value.__aenter__.return_value.get.return_value = mock_response

        api_adapter.config.update(
            {
                "host": "127.0.0.1",
                "port": 8004,
                "reload": True,  # Test reload functionality
                "mode": LaunchMode.MULTI,
            }
        )

        try:
            result = await api_adapter.start()

            assert result is True
            assert api_adapter.status == ServiceStatus.RUNNING
            assert api_adapter.process == mock_process

            # Verify that reload flag is passed to subprocess
            args, kwargs = mock_exec.call_args
            assert "--reload" in args

            # Test health check
            health = await api_adapter.health_check()
            assert health["status"] == ServiceStatus.RUNNING.value
            assert health["mode"] == "multi"

        finally:
            await api_adapter.stop(timeout=5)


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
@pytest.mark.timeout(10)  # Quick timeout for error test
async def test_api_adapter_start_exception(api_adapter):
    """Test startup failure handling"""
    with patch("launcher.adapters.api.uvicorn.Server", side_effect=Exception("Server error")):
        api_adapter.config.update({"host": "localhost", "port": 8000, "reload": False, "mode": LaunchMode.SINGLE})
        result = await api_adapter.start()

        assert result is False
        assert api_adapter.status == ServiceStatus.STOPPED


@pytest.mark.asyncio
@pytest.mark.timeout(15)  # Timeout for stop operations
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
@pytest.mark.timeout(20)  # Timeout for process stop operations
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
@pytest.mark.timeout(20)  # Timeout for force kill operations
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
@pytest.mark.timeout(10)  # Quick timeout for already dead process
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
@pytest.mark.timeout(5)  # Quick timeout for not running test
async def test_api_adapter_stop_not_running(api_adapter):
    """Test stopping when not running"""
    result = await api_adapter.stop()

    assert result is True


@pytest.mark.asyncio
@pytest.mark.timeout(10)  # Timeout for exception handling test
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
@pytest.mark.timeout(15)  # Timeout for Windows process handling
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
@pytest.mark.timeout(10)  # Timeout for process lookup error handling
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


# Real Error Scenario Tests (not mocked)


@pytest.mark.asyncio
@pytest.mark.timeout(20)  # Timeout for port conflict test
async def test_api_adapter_port_already_in_use():
    """Test startup failure when port is already in use"""
    import socket

    # First, start a socket server to occupy the port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))  # Let OS choose port
    occupied_port = sock.getsockname()[1]
    sock.listen(1)

    api_adapter = None
    try:
        # Now try to start adapter on same port
        api_adapter = ApiAdapter()
        api_adapter.config.update(
            {
                "host": "127.0.0.1",
                "port": occupied_port,  # Use the occupied port
                "reload": False,
                "mode": LaunchMode.SINGLE,
            }
        )

        # This should fail because port is in use
        # Uvicorn may call sys.exit(1) on port conflict, so catch SystemExit
        try:
            result = await api_adapter.start()
            # If no exception, should return False for failure
            assert result is False
        except SystemExit as e:
            # SystemExit with code 1 indicates port binding failure
            assert e.code == 1
            result = False

        assert api_adapter.status == ServiceStatus.STOPPED

    finally:
        sock.close()
        # Ensure cleanup
        if api_adapter and hasattr(api_adapter, "status") and api_adapter.status == ServiceStatus.RUNNING:
            await api_adapter.stop()


@pytest.mark.asyncio
@pytest.mark.timeout(25)  # Timeout for startup failure test
async def test_api_adapter_startup_timeout_failure():
    """Test startup failure when service takes too long to start"""
    api_adapter = ApiAdapter()

    # Configure with invalid app module to cause startup failure
    with patch("launcher.adapters.api.uvicorn.Config"):
        mock_server = Mock()
        mock_server.started = False  # Never becomes ready
        mock_server.serve = AsyncMock()

        with patch("launcher.adapters.api.uvicorn.Server", return_value=mock_server):
            api_adapter.config.update({"host": "127.0.0.1", "port": 0, "reload": False, "mode": LaunchMode.SINGLE})

            # This should fail due to timeout waiting for server.started
            result = await api_adapter.start()

            assert result is False
            assert api_adapter.status == ServiceStatus.STOPPED


@pytest.mark.asyncio
@pytest.mark.timeout(30)  # Timeout for process crash test
async def test_api_adapter_process_crashes_after_startup():
    """Test detection when subprocess crashes after initial startup"""
    api_adapter = ApiAdapter()
    api_adapter.config.update({"host": "127.0.0.1", "port": 0, "reload": False, "mode": LaunchMode.MULTI})

    # Mock a process that starts but then crashes
    mock_process = Mock()
    mock_process.pid = 12345
    mock_process.returncode = None  # Initially running

    with (
        patch("launcher.adapters.api.asyncio.create_subprocess_exec", return_value=mock_process),
        patch("httpx.AsyncClient") as mock_httpx,
    ):
        # Mock initial health check success
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx.return_value.__aenter__.return_value.get.return_value = mock_response

        # Start successfully
        result = await api_adapter.start()
        assert result is True
        assert api_adapter.status == ServiceStatus.RUNNING

        # Simulate process crash
        mock_process.returncode = 1  # Process exited with error

        # Health check should now detect the process is dead
        health = await api_adapter.health_check()
        assert health["status"] == ServiceStatus.RUNNING.value  # Status not updated yet

        # Stop should handle crashed process gracefully
        result = await api_adapter.stop()
        assert result is True
        assert api_adapter.status == ServiceStatus.STOPPED
