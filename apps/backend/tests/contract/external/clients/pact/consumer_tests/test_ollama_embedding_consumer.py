"""Consumer contract tests for OllamaEmbeddingProvider using Pact.

These tests define the contract between our application (consumer) and the Ollama API (provider).
They verify that our client can handle the expected API responses and generate pact files
for contract verification.

Note: This uses the corrected Ollama API endpoints and response formats.
"""

import pytest
from pact import match
from src.external.clients.errors import ExternalServiceError

pytestmark = [
    pytest.mark.contract,
    pytest.mark.pact_pair(provider="ollama-api"),
    pytest.mark.asyncio,
]

number = match.like(0.0)  # 任意 JSON number（v3 匹配器，示例值 0.0）


async def test_health_check_contract(pact, external_client_builder):
    """Test health check contract - GET /api/tags."""

    (
        pact.upon_receiving("a request for available models")
        .given("Ollama service is available")
        .with_request("GET", "/api/tags")
        .will_respond_with(200)
        .with_header(
            "Content-Type",
            match.regex("application/json; charset=utf-8", regex=r"^application/json(;.*)?$"),
        )
        .with_body(
            {
                "models": match.each_like(
                    {
                        "name": match.like("dengcao/Qwen3-Embedding-0.6B:F16"),
                        "model": match.like("dengcao/Qwen3-Embedding-0.6B:F16"),
                        "size": match.like(1197629321),
                        "digest": match.like("68d659a5c2ee4cdcbde61f85d292de073c977cea735c32944304469803804b6f"),
                        "modified_at": match.regex(
                            "2025-06-24T22:15:03.9648298+08:00",
                            regex=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{7})?\+\d{2}:\d{2}$",
                        ),
                        "details": match.like(
                            {
                                "parent_model": match.like(""),
                                "format": match.like("gguf"),
                                "family": match.like("qwen3"),
                                "families": match.each_like(match.like("qwen3"), min=1),
                                "parameter_size": match.like("595.78M"),
                                "quantization_level": match.like("F16"),
                            }
                        ),
                    },
                    min=1,
                )
            }
        )
    )

    with pact.serve() as srv:
        client = external_client_builder(str(srv.url))
        async with client.session():
            result = await client.check_connection()
            assert result is True


async def test_single_input_embedding_contract(pact, external_client_builder):
    """Test single text embedding contract - POST /api/embed -> embeddings."""
    (
        pact.upon_receiving("a request for single text embedding")
        .given("Ollama embedding model is available")
        .with_request("POST", "/api/embed")
        .with_header(
            "Content-Type",
            match.regex("application/json; charset=utf-8", regex=r"^application/json(;.*)?$"),
            part="Request",
        )
        .with_body({"model": "dengcao/Qwen3-Embedding-0.6B:F16", "input": "Hello world"}, part="Request")
        .will_respond_with(200)
        .with_header(
            "Content-Type",
            match.regex("application/json; charset=utf-8", regex=r"^application/json(;.*)?$"),
        )
        .with_body(
            {
                "model": match.like("dengcao/Qwen3-Embedding-0.6B:F16"),
                "embeddings": match.each_like(match.each_like(number, min=1024), min=1),
                "total_duration": match.like(95717700),
                "load_duration": match.like(63740100),
                "prompt_eval_count": match.like(4),
            }
        )
    )
    with pact.serve() as srv:
        client = external_client_builder(str(srv.url))
        async with client.session():
            result = await client.get_embedding("Hello world")
            assert result


async def test_batch_input_embeddings_contract(pact, external_client_builder):
    """Test batch text embeddings contract using single batch request.

    The API supports multiple texts in a single request.
    """
    inputs = ["First text", "Second text"]
    embedding_matchers = [match.each_like(number, min=1024) for _ in inputs]
    (
        pact.upon_receiving("a request for batch text embeddings")
        .given("Ollama embedding model supports batch input")
        .with_request("POST", "/api/embed")
        .with_header(
            "Content-Type",
            match.regex("application/json; charset=utf-8", regex=r"^application/json(;.*)?$"),
            part="Request",
        )
        .with_body({"model": "dengcao/Qwen3-Embedding-0.6B:F16", "input": inputs}, part="Request")
        .will_respond_with(200)
        .with_header(
            "Content-Type",
            match.regex("application/json; charset=utf-8", regex=r"^application/json(;.*)?$"),
        )
        .with_body(
            {
                "model": match.like("dengcao/Qwen3-Embedding-0.6B:F16"),
                "embeddings": embedding_matchers,
                "total_duration": match.like(95717700),
                "load_duration": match.like(63740100),
                "prompt_eval_count": match.like(4),
            }
        )
    )
    with pact.serve() as srv:
        client = external_client_builder(str(srv.url))
        async with client.session():
            results = await client.get_embeddings_batch(inputs)
            assert len(results) == len(inputs)


async def test_embedding_model_not_found_contract(pact, external_client_builder):
    """Test error contract - model not found."""

    (
        pact.upon_receiving("a request for embedding with non-existent model")
        .given("Requested embedding model does not exist")
        .with_request("POST", "/api/embed")
        .with_header(
            "Content-Type",
            match.regex("application/json; charset=utf-8", regex=r"^application/json(;.*)?$"),
            part="Request",
        )
        .with_body({"model": "non-existent-model", "input": "Test text"}, part="Request")
        .will_respond_with(404)
        .with_header(
            "Content-Type",
            match.regex("application/json; charset=utf-8", regex=r"^application/json(;.*)?$"),
        )
        .with_body(
            {
                "error": match.regex(
                    'model "non-existent-model" not found, try pulling it first',
                    regex=r"model \"[^\"]+\" not found, try pulling it first",
                )
            }
        )
    )

    # 启动 mock server 并调用
    with pact.serve() as srv:
        client = external_client_builder(str(srv.url))
        async with client.session():
            client.model = "non-existent-model"
            with pytest.raises(ExternalServiceError):
                await client.get_embedding("Test text")
