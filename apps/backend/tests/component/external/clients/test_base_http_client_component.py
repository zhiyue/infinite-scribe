"""Component tests for BaseHttpClient using mock HTTP servers."""

import asyncio
import json
from unittest.mock import MagicMock

import httpx
import pytest
from aioresponses import aioresponses
from src.external.clients.base_http import BaseHttpClient


class TestBaseHttpClientComponent:
    """Component tests using mock HTTP servers."""

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
            retry_min_wait=0.1,  # Fast retries for testing
            retry_max_wait=0.2,
        )

    @pytest.fixture
    def metrics_hook(self):
        """Create a mock metrics hook."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_successful_get_request(self, client, base_url):
        """Test successful GET request with mock server."""
        with aioresponses() as m:
            # Mock successful response
            m.get(f"{base_url}/api/users", status=200, payload={"users": ["alice", "bob"]})

            async with client.session():
                response = await client.get("/api/users")

                assert response.status_code == 200
                data = response.json()
                assert data == {"users": ["alice", "bob"]}

    @pytest.mark.asyncio
    async def test_successful_post_request(self, client, base_url):
        """Test successful POST request with JSON data."""
        with aioresponses() as m:
            request_data = {"name": "charlie", "email": "charlie@example.com"}
            response_data = {"id": 123, "name": "charlie", "created": True}

            m.post(f"{base_url}/api/users", status=201, payload=response_data)

            async with client.session():
                response = await client.post("/api/users", json_data=request_data)

                assert response.status_code == 201
                data = response.json()
                assert data == response_data

    @pytest.mark.asyncio
    async def test_get_with_query_parameters(self, client, base_url):
        """Test GET request with query parameters."""
        with aioresponses() as m:
            m.get(
                f"{base_url}/api/search?q=python&limit=10",
                status=200,
                payload={"results": ["result1", "result2"]},
            )

            async with client.session():
                response = await client.get("/api/search", params={"q": "python", "limit": 10})

                assert response.status_code == 200
                data = response.json()
                assert data == {"results": ["result1", "result2"]}

    @pytest.mark.asyncio
    async def test_custom_headers_sent(self, client, base_url):
        """Test that custom headers are properly sent."""
        with aioresponses() as m:
            # Mock server that echoes headers back
            def callback(url, **kwargs):
                headers = kwargs.get("headers", {})
                return aioresponses.CallbackResult(
                    status=200, payload={"received_headers": dict(headers)}
                )

            m.get(f"{base_url}/api/echo", callback=callback)

            async with client.session():
                custom_headers = {"Authorization": "Bearer token123", "Custom-Header": "value456"}
                response = await client.get("/api/echo", headers=custom_headers)

                assert response.status_code == 200
                data = response.json()
                received_headers = data["received_headers"]

                # Check that our custom headers were sent
                assert received_headers["Authorization"] == "Bearer token123"
                assert received_headers["Custom-Header"] == "value456"
                # Should also include the correlation ID
                assert "X-Correlation-ID" in received_headers

    @pytest.mark.asyncio
    async def test_retry_mechanism_success_after_failure(self, client_with_retry, base_url):
        """Test retry mechanism succeeds after initial failures."""
        with aioresponses() as m:
            # First two requests fail with 500, third succeeds
            m.get(f"{base_url}/api/unstable", status=500, payload={"error": "Server error"})
            m.get(f"{base_url}/api/unstable", status=500, payload={"error": "Server error"})
            m.get(f"{base_url}/api/unstable", status=200, payload={"success": True})

            async with client_with_retry.session():
                response = await client_with_retry.get("/api/unstable")

                assert response.status_code == 200
                data = response.json()
                assert data == {"success": True}

    @pytest.mark.asyncio
    async def test_retry_with_rate_limiting(self, client_with_retry, base_url):
        """Test retry mechanism with rate limiting (429)."""
        with aioresponses() as m:
            # First request hits rate limit, second succeeds
            m.post(f"{base_url}/api/rate-limited", status=429, payload={"error": "Rate limited"})
            m.post(f"{base_url}/api/rate-limited", status=200, payload={"processed": True})

            async with client_with_retry.session():
                response = await client_with_retry.post(
                    "/api/rate-limited", json_data={"action": "process"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data == {"processed": True}

    @pytest.mark.asyncio
    async def test_retry_exhausted_failure(self, client_with_retry, base_url):
        """Test retry mechanism fails after all attempts exhausted."""
        with aioresponses() as m:
            # All requests fail with 503
            for _ in range(5):  # More than retry attempts
                m.get(f"{base_url}/api/always-fails", status=503, payload={"error": "Service unavailable"})

            async with client_with_retry.session():
                with pytest.raises(Exception):  # Should raise tenacity.RetryError
                    await client_with_retry.get("/api/always-fails")

    @pytest.mark.asyncio
    async def test_no_retry_on_client_errors(self, client_with_retry, base_url):
        """Test that client errors (4xx) are not retried."""
        with aioresponses() as m:
            # Only register one 404 response - if retried, this would fail
            m.get(f"{base_url}/api/not-found", status=404, payload={"error": "Not found"})

            async with client_with_retry.session():
                with pytest.raises(httpx.HTTPStatusError) as exc_info:
                    await client_with_retry.get("/api/not-found")

                assert exc_info.value.response.status_code == 404

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, client):
        """Test handling of connection errors."""
        # Don't use aioresponses - this will cause a connection error
        async with client.session():
            with pytest.raises(httpx.RequestError):
                await client.get("/api/unreachable")

    @pytest.mark.asyncio
    async def test_timeout_handling(self, base_url):
        """Test timeout handling with slow responses."""
        client = BaseHttpClient(base_url, timeout=0.1)  # Very short timeout

        with aioresponses() as m:
            # Simulate slow response
            def slow_callback(url, **kwargs):
                asyncio.sleep(0.2)  # Longer than timeout
                return aioresponses.CallbackResult(status=200, payload={"data": "slow"})

            m.get(f"{base_url}/api/slow", callback=slow_callback)

            async with client.session():
                with pytest.raises(httpx.TimeoutException):
                    await client.get("/api/slow")

    @pytest.mark.asyncio
    async def test_health_check_success(self, client, base_url):
        """Test successful health check."""
        with aioresponses() as m:
            m.get(f"{base_url}/health", status=200, payload={"status": "healthy"})

            async with client.session():
                is_healthy = await client.health_check()
                assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client, base_url):
        """Test health check failure."""
        with aioresponses() as m:
            m.get(f"{base_url}/health", status=503, payload={"status": "unhealthy"})

            async with client.session():
                is_healthy = await client.health_check()
                assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_custom_endpoint(self, client, base_url):
        """Test health check with custom endpoint."""
        with aioresponses() as m:
            m.get(f"{base_url}/api/status", status=200, payload={"ok": True})

            async with client.session():
                is_healthy = await client.health_check("/api/status")
                assert is_healthy is True

    @pytest.mark.asyncio
    async def test_metrics_collection_success(self, base_url, metrics_hook):
        """Test metrics collection on successful requests."""
        client = BaseHttpClient(base_url, metrics_hook=metrics_hook)

        with aioresponses() as m:
            m.get(f"{base_url}/api/data", status=200, payload={"data": "value"})

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
    async def test_metrics_collection_failure(self, base_url, metrics_hook):
        """Test metrics collection on failed requests."""
        client = BaseHttpClient(base_url, metrics_hook=metrics_hook)

        with aioresponses() as m:
            m.post(f"{base_url}/api/fail", status=500, payload={"error": "Internal error"})

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
    async def test_correlation_id_propagation(self, client, base_url):
        """Test that correlation IDs are properly propagated."""
        with aioresponses() as m:
            correlation_ids = []

            def callback(url, **kwargs):
                headers = kwargs.get("headers", {})
                correlation_id = headers.get("X-Correlation-ID")
                correlation_ids.append(correlation_id)
                return aioresponses.CallbackResult(status=200, payload={"received": correlation_id})

            m.get(f"{base_url}/api/trace", callback=callback)

            async with client.session():
                # Test with custom correlation ID
                custom_id = "custom-trace-123"
                response1 = await client.get("/api/trace", correlation_id=custom_id)

                # Test with auto-generated correlation ID
                response2 = await client.get("/api/trace")

        assert len(correlation_ids) == 2
        assert correlation_ids[0] == custom_id
        assert correlation_ids[1] is not None
        assert len(correlation_ids[1]) == 8  # Auto-generated IDs are 8 chars

        # Verify responses contain the correlation IDs
        data1 = response1.json()
        data2 = response2.json()
        assert data1["received"] == custom_id
        assert data2["received"] == correlation_ids[1]

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client, base_url):
        """Test handling multiple concurrent requests."""
        with aioresponses() as m:
            # Mock multiple endpoints
            for i in range(5):
                m.get(f"{base_url}/api/item/{i}", status=200, payload={"id": i, "name": f"item{i}"})

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

    @pytest.mark.asyncio
    async def test_request_body_serialization(self, client, base_url):
        """Test different types of request body serialization."""
        with aioresponses() as m:
            # Test JSON serialization
            def json_callback(url, **kwargs):
                # Verify the request body was properly serialized
                body = kwargs.get("json")
                return aioresponses.CallbackResult(status=200, payload={"received": body})

            m.post(f"{base_url}/api/json", callback=json_callback)

            # Test form data
            def form_callback(url, **kwargs):
                data = kwargs.get("data")
                return aioresponses.CallbackResult(status=200, payload={"form_data": data})

            m.post(f"{base_url}/api/form", callback=form_callback)

            async with client.session():
                # Test JSON request
                json_data = {"name": "test", "value": 123, "active": True}
                json_response = await client.post("/api/json", json_data=json_data)
                json_result = json_response.json()
                assert json_result["received"] == json_data

                # Test form data request
                form_data = {"username": "testuser", "password": "secret"}
                form_response = await client.post("/api/form", data=form_data)
                form_result = form_response.json()
                assert form_result["form_data"] == form_data