"""Unit tests for BaseHttpClient - Fixed Version."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.external.clients.base_http import BaseHttpClient
from tenacity import RetryError


class TestBaseHttpClient:
    """Test cases for BaseHttpClient."""

    @pytest.fixture
    def client(self):
        """Create a new BaseHttpClient instance for each test."""
        return BaseHttpClient(
            base_url="http://test.com",
            timeout=30.0,
            enable_retry=False,
            retry_attempts=3,
            retry_min_wait=1.0,
            retry_max_wait=10.0,
        )

    @pytest.fixture
    def client_with_retry(self):
        """Create a BaseHttpClient instance with retry enabled."""
        return BaseHttpClient(
            base_url="http://test.com",
            enable_retry=True,
            retry_attempts=3,
            retry_min_wait=0.1,  # Faster for tests
            retry_max_wait=1.0,
        )

    @pytest.fixture
    def mock_metrics_hook(self):
        """Create a mock metrics hook for testing."""
        return MagicMock()

    def test_init_defaults(self):
        """Test client initialization with default values."""
        client = BaseHttpClient("http://test.com")

        assert client.base_url == "http://test.com"
        assert client._client is None
        assert client._timeout == 30.0
        assert client._max_keepalive_connections == 5
        assert client._max_connections == 10
        assert client._enable_retry is False
        assert client._retry_attempts == 3
        assert client._retry_min_wait == 1.0
        assert client._retry_max_wait == 10.0
        assert client._metrics_hook is None

    def test_init_custom_parameters(self, mock_metrics_hook):
        """Test client initialization with custom parameters."""
        client = BaseHttpClient(
            base_url="http://custom.com/api/",
            timeout=60.0,
            max_keepalive_connections=10,
            max_connections=20,
            enable_retry=True,
            retry_attempts=5,
            retry_min_wait=2.0,
            retry_max_wait=20.0,
            metrics_hook=mock_metrics_hook,
        )

        assert client.base_url == "http://custom.com/api"  # Trailing slash removed
        assert client._timeout == 60.0
        assert client._max_keepalive_connections == 10
        assert client._max_connections == 20
        assert client._enable_retry is True
        assert client._retry_attempts == 5
        assert client._retry_min_wait == 2.0
        assert client._retry_max_wait == 20.0
        assert client._metrics_hook == mock_metrics_hook

    def test_should_retry_server_errors(self, client):
        """Test retry logic for server errors."""
        # 500 errors should be retried
        response_500 = MagicMock()
        response_500.status_code = 500
        http_error_500 = httpx.HTTPStatusError("Server error", request=MagicMock(), response=response_500)
        assert client._should_retry(http_error_500) is True

        # 502 errors should be retried
        response_502 = MagicMock()
        response_502.status_code = 502
        http_error_502 = httpx.HTTPStatusError("Bad gateway", request=MagicMock(), response=response_502)
        assert client._should_retry(http_error_502) is True

        # 503 errors should be retried
        response_503 = MagicMock()
        response_503.status_code = 503
        http_error_503 = httpx.HTTPStatusError("Service unavailable", request=MagicMock(), response=response_503)
        assert client._should_retry(http_error_503) is True

    def test_should_retry_rate_limiting(self, client):
        """Test retry logic for rate limiting."""
        response_429 = MagicMock()
        response_429.status_code = 429
        http_error_429 = httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=response_429)
        assert client._should_retry(http_error_429) is True

    def test_should_not_retry_client_errors(self, client):
        """Test retry logic for client errors."""
        # 400 errors should not be retried
        response_400 = MagicMock()
        response_400.status_code = 400
        http_error_400 = httpx.HTTPStatusError("Bad request", request=MagicMock(), response=response_400)
        assert client._should_retry(http_error_400) is False

        # 401 errors should not be retried
        response_401 = MagicMock()
        response_401.status_code = 401
        http_error_401 = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=response_401)
        assert client._should_retry(http_error_401) is False

        # 404 errors should not be retried
        response_404 = MagicMock()
        response_404.status_code = 404
        http_error_404 = httpx.HTTPStatusError("Not found", request=MagicMock(), response=response_404)
        assert client._should_retry(http_error_404) is False

    def test_should_retry_network_errors(self, client):
        """Test retry logic for network errors."""
        # Connection errors should be retried
        connect_error = httpx.ConnectError("Connection failed")
        assert client._should_retry(connect_error) is True

        # Timeout errors should be retried
        timeout_error = httpx.TimeoutException("Request timeout")
        assert client._should_retry(timeout_error) is True

        # Network errors should be retried
        network_error = httpx.NetworkError("Network error")
        assert client._should_retry(network_error) is True

        # General request errors should be retried
        request_error = httpx.RequestError("Request error")
        assert client._should_retry(request_error) is True

    def test_should_not_retry_other_errors(self, client):
        """Test retry logic for non-retryable errors."""
        # General exceptions should not be retried
        general_error = Exception("General error")
        assert client._should_retry(general_error) is False

        # ValueError should not be retried
        value_error = ValueError("Invalid value")
        assert client._should_retry(value_error) is False

    def test_record_metrics_with_hook(self, mock_metrics_hook):
        """Test metrics recording when hook is provided."""
        client = BaseHttpClient("http://test.com", metrics_hook=mock_metrics_hook)

        client._record_metrics("GET", "/test", 200, 1.5, provider="test", model="gpt-4")

        mock_metrics_hook.assert_called_once_with("GET", "/test", 200, 1.5, None, provider="test", model="gpt-4")

    def test_record_metrics_with_error(self, mock_metrics_hook):
        """Test metrics recording when error occurred."""
        client = BaseHttpClient("http://test.com", metrics_hook=mock_metrics_hook)
        error = Exception("Test error")

        client._record_metrics("POST", "/api", 500, 2.0, error, service="test")

        mock_metrics_hook.assert_called_once_with("POST", "/api", 500, 2.0, error, service="test")

    def test_record_metrics_without_hook(self, client):
        """Test metrics recording when no hook is provided."""
        # Should not raise any errors
        client._record_metrics("GET", "/test", 200, 1.0)

    def test_record_metrics_hook_failure(self, client, caplog):
        """Test metrics recording when hook itself fails."""
        failing_hook = MagicMock()
        failing_hook.side_effect = Exception("Hook failed")
        client._metrics_hook = failing_hook

        client._record_metrics("GET", "/test", 200, 1.0)

        # Should log warning but not raise
        assert "Metrics hook failed" in caplog.text

    def test_generate_correlation_id(self, client):
        """Test correlation ID generation."""
        correlation_id = client._generate_correlation_id()

        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 8

        # Should generate different IDs
        another_id = client._generate_correlation_id()
        assert correlation_id != another_id

    @pytest.mark.asyncio
    async def test_connect(self, client):
        """Test HTTP client connection."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            await client.connect()

            assert client._client == mock_client_instance
            mock_client_class.assert_called_once_with(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                ),
            )

    @pytest.mark.asyncio
    async def test_disconnect(self, client):
        """Test HTTP client disconnection."""
        mock_client = AsyncMock()
        client._client = mock_client

        await client.disconnect()

        mock_client.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_ensure_connected_success(self, client):
        """Test ensuring connection succeeds."""
        with patch.object(client, "connect") as mock_connect:
            mock_client = AsyncMock()
            client._client = mock_client

            result = await client.ensure_connected()

            assert result is True
            mock_connect.assert_not_called()  # Already connected

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        client._client = mock_client

        with patch.object(client, "ensure_connected", return_value=True):
            result = await client.health_check()

        assert result is True
        mock_client.get.assert_called_once_with("http://test.com/health")

    @pytest.mark.asyncio
    async def test_get_success(self, client):
        """Test successful GET request."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        client._client = mock_client

        with patch.object(client, "ensure_connected", return_value=True):
            result = await client.get("/test", params={"key": "value"}, headers={"Authorization": "Bearer token"})

        assert result == mock_response
        mock_client.get.assert_called_once()
        args, kwargs = mock_client.get.call_args

        assert args[0] == "http://test.com/test"
        assert kwargs["params"] == {"key": "value"}
        assert "Authorization" in kwargs["headers"]
        assert "X-Correlation-ID" in kwargs["headers"]

    @pytest.mark.asyncio
    async def test_post_success(self, client):
        """Test successful POST request."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_client.post.return_value = mock_response
        client._client = mock_client

        json_data = {"name": "test"}

        with patch.object(client, "ensure_connected", return_value=True):
            result = await client.post("/create", json_data=json_data, headers={"Content-Type": "application/json"})

        assert result == mock_response
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args

        assert args[0] == "http://test.com/create"
        assert kwargs["json"] == json_data
        assert kwargs["data"] is None
        assert "Content-Type" in kwargs["headers"]
        assert "X-Correlation-ID" in kwargs["headers"]

    @pytest.mark.asyncio
    async def test_get_with_retry_success_after_failure(self, client_with_retry):
        """Test GET request succeeds after retry."""
        mock_client = AsyncMock()

        # First call fails, second succeeds
        mock_response_error = MagicMock()
        mock_response_error.status_code = 500
        http_error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response_error)

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200

        mock_client.get.side_effect = [http_error, mock_response_success]
        client_with_retry._client = mock_client

        with patch.object(client_with_retry, "ensure_connected", return_value=True):
            result = await client_with_retry.get("/test")

        assert result == mock_response_success
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_post_with_retry_exhausted(self, client_with_retry):
        """Test POST request fails after retry exhausted."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response)
        mock_client.post.side_effect = http_error
        client_with_retry._client = mock_client

        with patch.object(client_with_retry, "ensure_connected", return_value=True), pytest.raises(RetryError):
            await client_with_retry.post("/test")

        # Should have tried the configured number of attempts
        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_session_context_manager(self, client):
        """Test session context manager."""
        with patch.object(client, "connect") as mock_connect:
            with patch.object(client, "disconnect") as mock_disconnect:
                async with client.session() as session:
                    assert session == client
                    mock_connect.assert_called_once()

                mock_disconnect.assert_called_once()

    def test_repr(self, client):
        """Test string representation of the client."""
        expected = "BaseHttpClient(base_url='http://test.com')"
        assert repr(client) == expected

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(self, mock_metrics_hook):
        """Test that metrics are recorded on successful requests."""
        client = BaseHttpClient("http://test.com", metrics_hook=mock_metrics_hook)
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        client._client = mock_client

        with patch.object(client, "ensure_connected", return_value=True):
            await client.get("/test")

        # Verify metrics hook was called with correct parameters
        mock_metrics_hook.assert_called_once()
        args = mock_metrics_hook.call_args[0]
        assert args[0] == "GET"  # method
        assert args[1] == "/test"  # endpoint
        assert args[2] == 200  # status_code
        assert isinstance(args[3], float)  # duration should be a float
        assert args[3] >= 0  # duration should be non-negative

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_error(self, mock_metrics_hook):
        """Test that metrics are recorded on failed requests."""
        client = BaseHttpClient("http://test.com", metrics_hook=mock_metrics_hook)
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response)
        mock_client.post.side_effect = http_error
        client._client = mock_client

        with patch.object(client, "ensure_connected", return_value=True), pytest.raises(httpx.HTTPStatusError):
            await client.post("/test")

        # Verify metrics hook was called with correct parameters
        mock_metrics_hook.assert_called_once()
        args = mock_metrics_hook.call_args[0]
        assert args[0] == "POST"  # method
        assert args[1] == "/test"  # endpoint
        assert args[2] == 500  # status_code
        assert isinstance(args[3], float)  # duration should be a float
        assert args[3] >= 0  # duration should be non-negative
        assert isinstance(args[4], httpx.HTTPStatusError)  # error
