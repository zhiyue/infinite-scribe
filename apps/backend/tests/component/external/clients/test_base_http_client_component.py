"""Component tests for BaseHttpClient using pytest-httpx."""

import asyncio
import json
from unittest.mock import MagicMock

import httpx
import pytest
from src.external.clients.base_http import BaseHttpClient
from tenacity import RetryError


class TestBaseHttpClientComponent:
    """Component tests using pytest-httpx mock server."""

    @pytest.fixture
    def base_url(self):
        """Base URL for testing."""
        return "http://test-api.example.com"

    @pytest.fixture
    def client(self, base_url):
        """Create a BaseHttpClient with basic configuration."""
        return BaseHttpClient(
            base_url=base_url,
            timeout=5.0,
            enable_retry=False,
        )

    @pytest.fixture
    def client_with_retry(self, base_url):
        """Create a BaseHttpClient with retry enabled."""
        return BaseHttpClient(
            base_url=base_url,
            timeout=2.0,
            enable_retry=True,
            retry_attempts=3,
            retry_min_wait=0.01,  # Very fast retries for testing
            retry_max_wait=0.02,
        )

    @pytest.fixture
    def metrics_hook(self):
        """Create a mock metrics hook."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_successful_get_request(self, client, base_url, httpx_mock):
        """Test successful GET request with mock server."""
        # Mock successful response
        httpx_mock.add_response(
            url=f"{base_url}/api/users",
            json={"users": ["alice", "bob"]},
            status_code=200,
        )

        async with client.session():
            response = await client.get("/api/users")

            assert response.status_code == 200
            data = response.json()
            assert data == {"users": ["alice", "bob"]}

    @pytest.mark.asyncio
    async def test_successful_post_request(self, client, base_url, httpx_mock):
        """Test successful POST request with JSON data."""
        request_data = {"name": "charlie", "email": "charlie@example.com"}
        response_data = {"id": 123, "name": "charlie", "created": True}

        httpx_mock.add_response(
            url=f"{base_url}/api/users",
            json=response_data,
            status_code=201,
        )

        async with client.session():
            response = await client.post("/api/users", json_data=request_data)

            assert response.status_code == 201
            data = response.json()
            assert data == response_data

        # Verify the request was made with correct JSON data
        request = httpx_mock.get_request()
        assert json.loads(request.content) == request_data

    @pytest.mark.asyncio
    async def test_get_with_query_parameters(self, client, base_url, httpx_mock):
        """Test GET request with query parameters."""
        httpx_mock.add_response(
            url=f"{base_url}/api/search?q=python&limit=10",
            json={"results": ["result1", "result2"]},
            status_code=200,
        )

        async with client.session():
            response = await client.get("/api/search", params={"q": "python", "limit": 10})

            assert response.status_code == 200
            data = response.json()
            assert data == {"results": ["result1", "result2"]}

    @pytest.mark.asyncio
    async def test_custom_headers_sent(self, client, base_url, httpx_mock):
        """Test that custom headers are properly sent."""
        httpx_mock.add_response(
            url=f"{base_url}/api/echo",
            json={"success": True},
            status_code=200,
        )

        async with client.session():
            custom_headers = {"Authorization": "Bearer token123", "Custom-Header": "value456"}
            await client.get("/api/echo", headers=custom_headers)

        # Verify headers were sent correctly
        request = httpx_mock.get_request()
        assert request.headers["Authorization"] == "Bearer token123"
        assert request.headers["Custom-Header"] == "value456"
        # Should also include the correlation ID
        assert "X-Correlation-ID" in request.headers

    @pytest.mark.asyncio
    async def test_retry_mechanism_success_after_failure(self, client_with_retry, base_url, httpx_mock):
        """Test retry mechanism succeeds after initial failures."""
        # Add multiple responses - first two fail, third succeeds
        httpx_mock.add_response(url=f"{base_url}/api/unstable", status_code=500, json={"error": "Server error"})
        httpx_mock.add_response(url=f"{base_url}/api/unstable", status_code=500, json={"error": "Server error"})
        httpx_mock.add_response(url=f"{base_url}/api/unstable", status_code=200, json={"success": True})

        async with client_with_retry.session():
            response = await client_with_retry.get("/api/unstable")

            assert response.status_code == 200
            data = response.json()
            assert data == {"success": True}

        # Should have made 3 requests total
        requests = httpx_mock.get_requests()
        assert len(requests) == 3

    @pytest.mark.asyncio
    async def test_retry_with_rate_limiting(self, client_with_retry, base_url, httpx_mock):
        """Test retry mechanism with rate limiting (429)."""
        # First request hits rate limit, second succeeds
        httpx_mock.add_response(url=f"{base_url}/api/rate-limited", status_code=429, json={"error": "Rate limited"})
        httpx_mock.add_response(url=f"{base_url}/api/rate-limited", status_code=200, json={"processed": True})

        async with client_with_retry.session():
            response = await client_with_retry.post("/api/rate-limited", json_data={"action": "process"})

            assert response.status_code == 200
            data = response.json()
            assert data == {"processed": True}

        # Should have made 2 requests total
        requests = httpx_mock.get_requests()
        assert len(requests) == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted_failure(self, client_with_retry, base_url, httpx_mock):
        """Test retry mechanism fails after all attempts exhausted."""
        # Add exactly the number of retry attempts
        for _ in range(3):  # Exactly retry attempts
            httpx_mock.add_response(
                url=f"{base_url}/api/always-fails", status_code=503, json={"error": "Service unavailable"}
            )

        async with client_with_retry.session():
            with pytest.raises(RetryError):
                await client_with_retry.get("/api/always-fails")

        # Should have made exactly the retry attempts (3)
        requests = httpx_mock.get_requests()
        assert len(requests) == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_client_errors(self, client_with_retry, base_url, httpx_mock):
        """Test that client errors (4xx) are not retried."""
        # Only one 404 response - if retried, test would fail
        httpx_mock.add_response(url=f"{base_url}/api/not-found", status_code=404, json={"error": "Not found"})

        async with client_with_retry.session():
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await client_with_retry.get("/api/not-found")

            assert exc_info.value.response.status_code == 404

        # Should have made only 1 request (no retry)
        requests = httpx_mock.get_requests()
        assert len(requests) == 1

    @pytest.mark.asyncio
    async def test_health_check_success(self, client, base_url, httpx_mock):
        """Test successful health check."""
        httpx_mock.add_response(
            url=f"{base_url}/health",
            json={"status": "healthy"},
            status_code=200,
        )

        async with client.session():
            is_healthy = await client.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client, base_url, httpx_mock):
        """Test health check failure."""
        httpx_mock.add_response(
            url=f"{base_url}/health",
            json={"status": "unhealthy"},
            status_code=503,
        )

        async with client.session():
            is_healthy = await client.health_check()
            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_custom_endpoint(self, client, base_url, httpx_mock):
        """Test health check with custom endpoint."""
        httpx_mock.add_response(
            url=f"{base_url}/api/status",
            json={"ok": True},
            status_code=200,
        )

        async with client.session():
            is_healthy = await client.health_check("/api/status")
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_metrics_collection_success(self, base_url, metrics_hook, httpx_mock):
        """Test metrics collection on successful requests."""
        client = BaseHttpClient(base_url, metrics_hook=metrics_hook)

        httpx_mock.add_response(
            url=f"{base_url}/api/data",
            json={"data": "value"},
            status_code=200,
        )

        async with client.session():
            await client.get("/api/data")

        # Verify metrics were recorded
        metrics_hook.assert_called_once()
        args = metrics_hook.call_args[0]
        assert args[0] == "GET"  # method
        assert args[1] == "/api/data"  # endpoint
        assert args[2] == 200  # status_code
        assert isinstance(args[3], float)  # duration
        assert args[3] >= 0  # non-negative duration
        assert args[4] is None  # no error

    @pytest.mark.asyncio
    async def test_metrics_collection_failure(self, base_url, metrics_hook, httpx_mock):
        """Test metrics collection on failed requests."""
        client = BaseHttpClient(base_url, metrics_hook=metrics_hook)

        httpx_mock.add_response(
            url=f"{base_url}/api/fail",
            json={"error": "Internal error"},
            status_code=500,
        )

        async with client.session():
            with pytest.raises(httpx.HTTPStatusError):
                await client.post("/api/fail")

        # Verify metrics were recorded with error
        metrics_hook.assert_called_once()
        args = metrics_hook.call_args[0]
        assert args[0] == "POST"  # method
        assert args[1] == "/api/fail"  # endpoint
        assert args[2] == 500  # status_code
        assert isinstance(args[3], float)  # duration
        assert args[3] >= 0  # non-negative duration
        assert isinstance(args[4], httpx.HTTPStatusError)  # error object

    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self, client, base_url, httpx_mock):
        """Test that correlation IDs are properly propagated."""
        httpx_mock.add_response(
            url=f"{base_url}/api/trace",
            json={"received": "ok"},
            status_code=200,
        )
        # Add another response for the second request
        httpx_mock.add_response(
            url=f"{base_url}/api/trace",
            json={"received": "ok"},
            status_code=200,
        )

        async with client.session():
            # Test with custom correlation ID
            custom_id = "custom-trace-123"
            await client.get("/api/trace", correlation_id=custom_id)

            # Test with auto-generated correlation ID
            await client.get("/api/trace")

        requests = httpx_mock.get_requests()
        assert len(requests) == 2

        # Check first request has custom correlation ID
        assert requests[0].headers["X-Correlation-ID"] == custom_id

        # Check second request has auto-generated correlation ID
        auto_id = requests[1].headers["X-Correlation-ID"]
        assert auto_id is not None
        assert len(auto_id) == 8  # Auto-generated IDs are 8 chars

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client, base_url, httpx_mock):
        """Test handling multiple concurrent requests."""
        # Mock multiple endpoints
        for i in range(5):
            httpx_mock.add_response(
                url=f"{base_url}/api/item/{i}",
                json={"id": i, "name": f"item{i}"},
                status_code=200,
            )

        async with client.session():
            # Make concurrent requests
            tasks = [client.get(f"/api/item/{i}") for i in range(5)]
            responses = await asyncio.gather(*tasks)

            # Verify all requests succeeded
            assert len(responses) == 5
            for i, response in enumerate(responses):
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == i
                assert data["name"] == f"item{i}"

        # Verify all requests were made
        requests = httpx_mock.get_requests()
        assert len(requests) == 5

    @pytest.mark.asyncio
    async def test_request_body_serialization(self, client, base_url, httpx_mock):
        """Test different types of request body serialization."""
        # Mock JSON endpoint
        httpx_mock.add_response(
            url=f"{base_url}/api/json",
            json={"received": "json"},
            status_code=200,
        )

        # Mock form endpoint
        httpx_mock.add_response(
            url=f"{base_url}/api/form",
            json={"received": "form"},
            status_code=200,
        )

        async with client.session():
            # Test JSON request
            json_data = {"name": "test", "value": 123, "active": True}
            json_response = await client.post("/api/json", json_data=json_data)
            assert json_response.status_code == 200

            # Test form data request
            form_data = {"username": "testuser", "password": "secret"}
            form_response = await client.post("/api/form", data=form_data)
            assert form_response.status_code == 200

        requests = httpx_mock.get_requests()
        assert len(requests) == 2

        # Verify JSON request
        json_request = requests[0]
        assert json.loads(json_request.content) == json_data

        # Verify form request - content would be form-encoded
        form_request = requests[1]
        assert form_request.content is not None

    @pytest.mark.asyncio
    async def test_connection_error_simulation(self, client, base_url, httpx_mock):
        """Test connection error handling."""
        # pytest-httpx can simulate network errors
        httpx_mock.add_exception(
            url=f"{base_url}/api/unreachable",
            exception=httpx.ConnectError("Connection failed"),
        )

        async with client.session():
            with pytest.raises(httpx.ConnectError):
                await client.get("/api/unreachable")

    @pytest.mark.asyncio
    async def test_timeout_error_simulation(self, client, base_url, httpx_mock):
        """Test timeout error handling."""
        httpx_mock.add_exception(
            url=f"{base_url}/api/slow",
            exception=httpx.TimeoutException("Request timed out"),
        )

        async with client.session():
            with pytest.raises(httpx.TimeoutException):
                await client.get("/api/slow")
