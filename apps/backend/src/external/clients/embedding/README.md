# Embedding Providers

This package provides a unified interface for different embedding service providers, following the adapter pattern from Clean/Hexagonal architecture. Enhanced with retry mechanisms, observability, batch performance optimization, and lazy initialization.

## Architecture

```
embedding/
├── base.py              # Abstract base class (EmbeddingProvider)
├── ollama.py           # Ollama provider implementation  
├── factory.py          # Factory for creating providers
├── example_openai.py   # Example implementation template
└── __init__.py         # Package exports with lazy loading
```

## Current Providers

- **Ollama** (`OllamaEmbeddingProvider`) - Local/self-hosted embedding models with retry & concurrency support

## Features

- 🔄 **Retry & Resilience** - Configurable tenacity-based retry with exponential backoff
- 📊 **Observability** - Request timing, status codes, correlation IDs, and metrics hooks  
- ⚡ **Batch Performance** - Bounded concurrency for high-throughput batch processing
- 🚀 **Lazy Initialization** - Avoid import-time side effects with lazy provider instantiation
- 🛡️ **Error Handling** - Structured exceptions with semantic preservation
- 🔌 **Clean Architecture** - Pluggable providers following hexagonal architecture

## Usage

### Basic Usage (Recommended)

```python
from src.external.clients.embedding import get_embedding_service

# Get the default configured provider with lazy initialization (recommended)
service = get_embedding_service()

# Single embedding
embedding = await service.get_embedding("Hello world")
print(f"Embedding: {embedding[:5]}...")  # First 5 dimensions

# Batch processing (sequential by default)
texts = ["Hello", "World", "Python"]
embeddings = await service.get_embeddings_batch(texts)
print(f"Generated {len(embeddings)} embeddings")
```

### High-Performance Batch Processing

```python
from src.external.clients.embedding import get_embedding_service

service = get_embedding_service()
texts = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]

# Sequential processing (default, most stable)
embeddings = await service.get_embeddings_batch(texts, concurrency=1)

# Bounded concurrent processing (higher throughput)
embeddings = await service.get_embeddings_batch(texts, concurrency=3)

# For large batches, adjust concurrency based on:
# - Provider rate limits (Ollama: 3-5 concurrent requests)
# - Network latency and bandwidth
# - Memory constraints
```

### Legacy Usage (Deprecated but Supported)

```python
# These still work but issue deprecation warnings
from src.external.clients import embedding_service, embedding_client

# Use new functions instead:
from src.external.clients.embedding import get_embedding_service, get_embedding_client
```

### Factory Pattern (Advanced)

```python
from src.external.clients.embedding import EmbeddingProviderFactory

# Create provider with custom configuration
provider = EmbeddingProviderFactory.create_provider(
    provider_type="ollama",
    base_url="http://localhost:11434",
    model="custom-embedding-model",
    timeout=45.0
)

# Use the provider
embedding = await provider.get_embedding("Hello world")
```

### Retry & Resilience Configuration

```python
from src.external.clients.embedding import OllamaEmbeddingProvider

# Provider with retry enabled for better resilience
provider = OllamaEmbeddingProvider(
    base_url="http://localhost:11434",
    model="your-model",
    timeout=30.0,
    # Retry configuration
    enable_retry=True,
    retry_attempts=3,
    retry_min_wait=1.0,
    retry_max_wait=10.0
)

# The provider will automatically retry on:
# - Network errors (connection issues, timeouts)
# - HTTP 5xx server errors
# - HTTP 429 rate limiting
# Uses exponential backoff with jitter
```

### Observability & Monitoring

```python
import logging
from src.external.clients.embedding import OllamaEmbeddingProvider

# Custom metrics hook for monitoring
def metrics_callback(method: str, endpoint: str, status_code: int, 
                    duration: float, error: Exception = None):
    if error:
        logging.error(f"{method} {endpoint} failed: {error} ({duration:.3f}s)")
    else:
        logging.info(f"{method} {endpoint}: {status_code} ({duration:.3f}s)")
    
    # Send to your monitoring system (Prometheus, etc.)
    # prometheus_client.counter.inc(...)
    # prometheus_client.histogram.observe(...)

# Provider with observability
provider = OllamaEmbeddingProvider(
    base_url="http://localhost:11434",
    model="your-model",
    metrics_hook=metrics_callback
)

# All requests will be logged with timing and correlation IDs
embedding = await provider.get_embedding("Hello world")
```

### Connection Management

```python
from src.external.clients.embedding import OllamaEmbeddingProvider

provider = OllamaEmbeddingProvider()

# Manual connection management
await provider.connect()
try:
    embedding = await provider.get_embedding("Hello world")
finally:
    await provider.disconnect()

# Or use context manager (if implemented)
async with provider.session():
    embedding = await provider.get_embedding("Hello world")
```

## Adding New Providers

### Step 1: Implement the Provider

Create a new file (e.g., `my_provider.py`) implementing `EmbeddingProvider`:

```python
from .base import EmbeddingProvider
from ..base_http import BaseHttpClient

class MyEmbeddingProvider(EmbeddingProvider, BaseHttpClient):
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        BaseHttpClient.__init__(self, **kwargs)
    
    @property
    def provider_name(self) -> str:
        return "my_provider"
    
    @property 
    def model_name(self) -> str:
        return self.model
        
    # Implement all abstract methods...
    async def get_embedding(self, text: str) -> List[float]:
        # Your implementation here
        pass
```

### Step 2: Register the Provider

```python
from .factory import EmbeddingProviderFactory
from .my_provider import MyEmbeddingProvider

EmbeddingProviderFactory.register_provider("my_provider", MyEmbeddingProvider)
```

### Step 3: Use the New Provider

```python
provider = EmbeddingProviderFactory.create_provider(
    provider_type="my_provider",
    api_key="your-api-key"
)
```

## Provider Interface

All providers must implement these methods:

### Required Methods

- `async def connect() -> None` - Establish connection
- `async def disconnect() -> None` - Close connection  
- `async def check_connection() -> bool` - Health check
- `async def get_embedding(text: str) -> List[float]` - Single embedding
- `async def get_embeddings_batch(texts: List[str]) -> List[List[float]]` - Batch embeddings

### Required Properties

- `provider_name: str` - Provider identifier
- `model_name: str` - Model being used

## Error Handling

The package provides structured error handling:

```python
from src.external.clients.errors import (
    ExternalServiceError,
    ServiceValidationError,
    ServiceResponseError,
    ServiceConnectionError,
)

try:
    embedding = await provider.get_embedding("")
except ServiceValidationError as e:
    print(f"Validation error: {e}")
except ServiceConnectionError as e:
    print(f"Connection error: {e}")  
except ExternalServiceError as e:
    print(f"General service error: {e}")
```

## Configuration

Providers are configured via `EmbeddingSettings` in `src/core/config.py`:

```python
# Embedding configuration in settings
class EmbeddingSettings(BaseModel):
    # Provider selection
    provider: str = "ollama"  # ollama, openai, anthropic
    
    # Ollama settings
    ollama_host: str = "192.168.1.191"
    ollama_port: int = 11434
    ollama_model: str = "your-embedding-model"
    
    # OpenAI settings (for future use)
    openai_api_key: str = ""
    openai_model: str = "text-embedding-ada-002"
    openai_base_url: str = "https://api.openai.com/v1"
    
    # Connection settings
    timeout: float = 30.0
    max_keepalive_connections: int = 5
    max_connections: int = 10

# Access via settings.embedding
from src.core.config import settings
provider_config = settings.embedding.provider_config
```

### Environment Variables

Configure via environment variables using double underscore notation:

```bash
# Provider selection
EMBEDDING__PROVIDER=ollama

# Ollama configuration  
EMBEDDING__OLLAMA_HOST=192.168.1.191
EMBEDDING__OLLAMA_PORT=11434
EMBEDDING__OLLAMA_MODEL=your-embedding-model

# Connection tuning
EMBEDDING__TIMEOUT=45.0
EMBEDDING__MAX_CONNECTIONS=20
```

## Backward Compatibility

The package maintains backward compatibility with deprecation warnings:

```python
# ✅ Recommended (new): Explicit lazy loading
from src.external.clients.embedding import get_embedding_service, get_embedding_client

service = get_embedding_service()  # No import-time side effects

# ⚠️ Deprecated (legacy): Direct property access  
from src.external.clients import embedding_service, embedding_client
# These still work but issue DeprecationWarning

# ✅ Legacy class name alias (still supported)
from src.external.clients.embedding import EmbeddingClient  # -> EmbeddingProvider
```

## Best Practices

### Performance Optimization

```python
# ✅ Use appropriate concurrency for your use case
embeddings = await service.get_embeddings_batch(texts, concurrency=3)

# ✅ Enable retry for production environments
provider = OllamaEmbeddingProvider(enable_retry=True, retry_attempts=3)

# ✅ Use lazy loading to avoid startup delays
service = get_embedding_service()  # Only creates provider when first used
```

### Error Handling

```python
from src.external.clients.errors import ServiceResponseError, ServiceValidationError

try:
    embeddings = await service.get_embeddings_batch(texts, concurrency=5)
except ServiceResponseError as e:
    # Handle API response format issues (specific semantic errors)
    logger.error(f"API response error: {e}")
    raise  # Preserve specific error semantics
except ServiceValidationError as e:
    # Handle input validation errors
    logger.error(f"Input validation failed: {e}")
    # Maybe retry with corrected input
except Exception as e:
    # Handle network/connection errors
    logger.error(f"Embedding service failed: {e}")
    # Implement fallback or circuit breaker
```

### Monitoring & Observability

```python
# ✅ Implement metrics collection for production
def prometheus_metrics_hook(method, endpoint, status_code, duration, error):
    request_duration_histogram.labels(method=method, endpoint=endpoint).observe(duration)
    request_counter.labels(method=method, status=status_code).inc()
    if error:
        error_counter.labels(method=method, error_type=type(error).__name__).inc()

provider = OllamaEmbeddingProvider(
    enable_retry=True,
    metrics_hook=prometheus_metrics_hook
)
```

### Concurrency Guidelines

- **Sequential (concurrency=1)**: Most stable, use for small batches or rate-limited APIs
- **Low concurrency (2-3)**: Good balance for Ollama and most local services  
- **Medium concurrency (5-10)**: For high-performance APIs with good rate limits
- **High concurrency (10+)**: Only for APIs designed for high throughput

Monitor response times and error rates to find optimal concurrency levels.

## Testing

Tests are located in `tests/unit/external/clients/test_ollama_embedding.py`.

### Testing New Features

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.external.clients.embedding import get_embedding_service, OllamaEmbeddingProvider

# Test lazy initialization
def test_lazy_initialization():
    """Test that get_embedding_service() provides lazy loading."""
    with patch('src.external.clients.embedding.factory.EmbeddingProviderFactory.get_default_provider') as mock_factory:
        mock_factory.return_value = AsyncMock()
        
        # First call should create provider
        service1 = get_embedding_service()
        assert mock_factory.call_count == 1
        
        # Second call should return cached provider
        service2 = get_embedding_service()
        assert mock_factory.call_count == 1
        assert service1 is service2

# Test concurrent batch processing
@pytest.mark.asyncio
async def test_concurrent_batch_processing():
    """Test that concurrency parameter works correctly."""
    provider = OllamaEmbeddingProvider()
    texts = ["text1", "text2", "text3", "text4"]
    
    with patch.object(provider, 'get_embedding') as mock_get:
        mock_get.return_value = [0.1, 0.2, 0.3]
        
        # Test sequential processing
        await provider.get_embeddings_batch(texts, concurrency=1)
        assert mock_get.call_count == len(texts)
        
        mock_get.reset_mock()
        
        # Test concurrent processing  
        await provider.get_embeddings_batch(texts, concurrency=2)
        assert mock_get.call_count == len(texts)

# Test retry mechanism
@pytest.mark.asyncio
async def test_retry_mechanism():
    """Test that retry mechanism works for transient errors."""
    provider = OllamaEmbeddingProvider(enable_retry=True, retry_attempts=3)
    
    with patch.object(provider, '_client') as mock_client:
        # Simulate transient error followed by success
        mock_client.post.side_effect = [
            httpx.HTTPStatusError("Server Error", request=None, response=Mock(status_code=500)),
            httpx.HTTPStatusError("Server Error", request=None, response=Mock(status_code=500)), 
            Mock(json=lambda: {"embedding": [0.1, 0.2, 0.3]}, status_code=200)
        ]
        
        result = await provider.get_embedding("test text")
        assert result == [0.1, 0.2, 0.3]
        assert mock_client.post.call_count == 3

# Test metrics hook
@pytest.mark.asyncio  
async def test_metrics_hook():
    """Test that metrics hook is called correctly."""
    metrics_calls = []
    
    def metrics_callback(method, endpoint, status_code, duration, error):
        metrics_calls.append((method, endpoint, status_code, error))
    
    provider = OllamaEmbeddingProvider(metrics_hook=metrics_callback)
    
    with patch.object(provider, '_client') as mock_client:
        mock_client.post.return_value = Mock(
            json=lambda: {"embedding": [0.1, 0.2, 0.3]}, 
            status_code=200
        )
        
        await provider.get_embedding("test")
        
        assert len(metrics_calls) == 1
        method, endpoint, status_code, error = metrics_calls[0]
        assert method == "POST"
        assert endpoint == "/api/embed"
        assert status_code == 200
        assert error is None
```

### Testing Guidelines for New Providers

1. **Unit Tests**: Mock HTTP responses for different scenarios
2. **Error Handling**: Test all error types (validation, response, connection)  
3. **Retry Logic**: Test retry behavior with transient errors
4. **Concurrency**: Test batch processing with different concurrency levels
5. **Observability**: Verify metrics hook integration
6. **Factory Integration**: Test provider creation and configuration
7. **Lazy Loading**: Test that providers aren't created at import time

### Integration Tests

Use testcontainers for integration tests when testing against real services:

```python
@pytest.mark.integration
async def test_ollama_integration():
    """Integration test with real Ollama service."""
    # Use testcontainer or real service endpoint
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="test-model",
        enable_retry=True
    )
    
    embedding = await provider.get_embedding("integration test")
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)
```