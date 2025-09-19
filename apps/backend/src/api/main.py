"""API Gateway main entry point."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.cancelled_error import CancelledErrorMiddleware
from src.api.routes import docs, health, v1
from src.core.config import settings
from src.core.logging import get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    from src.core.logging.config import configure_logging
    from src.core.logging.context import bind_service_context
    from src.db.graph import neo4j_service
    from src.db.redis import redis_service
    from src.db.sql import postgres_service

    logger = get_logger(__name__)

    # Startup
    try:
        # Ensure structured logging is configured (use console in development)
        try:
            configure_logging(
                environment=getattr(settings, "environment", "development"),
                level="INFO",
                enable_file_logging=True,  # Enable file logging for API subprocess
                file_log_format="structured",  # Use structured format for better readability
            )
            bind_service_context(service="api-gateway", component="lifespan")
        except Exception as e:
            # Fall back silently; uvicorn default logging will still work
            logger.debug(f"Logging configuration skipped: {e}")
        logger.info("Initializing database connections...")

        # PostgreSQL
        t0 = time.perf_counter()
        logger.info(
            "Connecting to PostgreSQL...",
            extra={
                "host": settings.database.postgres_host,
                "port": settings.database.postgres_port,
                "db": settings.database.postgres_db,
            },
        )
        await postgres_service.connect()
        postgres_ok = await postgres_service.check_connection()
        logger.info(
            "PostgreSQL connection check finished",
            extra={
                "ok": postgres_ok,
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            },
        )
        if not postgres_ok:
            logger.error("Failed to establish PostgreSQL connection")

        # Neo4j
        t1 = time.perf_counter()
        logger.info(
            "Connecting to Neo4j...",
            extra={
                "host": settings.database.neo4j_host,
                "port": settings.database.neo4j_port,
            },
        )
        await neo4j_service.connect()
        neo4j_ok = await neo4j_service.check_connection()
        logger.info(
            "Neo4j connection check finished",
            extra={
                "ok": neo4j_ok,
                "elapsed_ms": int((time.perf_counter() - t1) * 1000),
            },
        )
        if not neo4j_ok:
            logger.error("Failed to establish Neo4j connection")

        # Redis (cache)
        t2 = time.perf_counter()
        logger.info(
            "Connecting to Redis...",
            extra={
                "host": settings.database.redis_host,
                "port": settings.database.redis_port,
            },
        )
        await redis_service.connect()
        redis_ok = await redis_service.check_connection()
        logger.info(
            "Redis connection check finished",
            extra={
                "ok": redis_ok,
                "elapsed_ms": int((time.perf_counter() - t2) * 1000),
            },
        )
        if not redis_ok:
            logger.error("Failed to establish Redis connection")

        # Initialize shutdown event for graceful SSE connection handling
        import asyncio

        app.state.shutdown_event = asyncio.Event()

        # Initialize SSE provider (app-scoped) - lazy, singleflight ready
        try:
            from src.services.sse.provider import SSEProvider

            app.state.sse_provider = SSEProvider(redis_service)
            logger.info("SSE provider registered (lazy init, singleflight-coordinated)")
        except Exception as e:
            logger.error(f"Failed to register SSE provider: {e}")
            app.state.sse_provider = None

        # Initialize launcher components
        logger.info("Initializing launcher components...")
        try:
            from src.launcher.config import LauncherConfigModel
            from src.launcher.health import HealthMonitor
            from src.launcher.orchestrator import Orchestrator

            # Create launcher components (in production, these would be shared with the launcher process)
            launcher_config = LauncherConfigModel()
            app.state.orchestrator = Orchestrator(launcher_config)
            app.state.health_monitor = HealthMonitor(check_interval=launcher_config.health_interval)

            logger.info("Launcher components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize launcher components: {e}")
            # Set None to indicate unavailable (graceful degradation)
            app.state.orchestrator = None
            app.state.health_monitor = None

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")

    yield

    # Shutdown
    try:
        logger.info("Shutting down services...")

        # Set shutdown flag for SSE connections
        import asyncio

        if not hasattr(app.state, "shutdown_event"):
            app.state.shutdown_event = asyncio.Event()
        app.state.shutdown_event.set()

        # Give SSE connections a moment to detect shutdown
        await asyncio.sleep(0.5)

        # Clean up SSE provider if initialized
        try:
            sse_provider = getattr(app.state, "sse_provider", None)
            if sse_provider is not None:
                await sse_provider.close()
                app.state.sse_provider = None
        except Exception as e:
            logger.error(f"Unexpected error during SSE provider cleanup: {e}")

        # Cleanup launcher components
        if hasattr(app.state, "orchestrator") and app.state.orchestrator:
            try:
                # In production, this would coordinate with launcher shutdown
                logger.info("Shutting down launcher components...")
                app.state.orchestrator = None
                app.state.health_monitor = None
                logger.info("Launcher components shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down launcher components: {e}")

        # Disconnect database services
        await postgres_service.disconnect()
        await neo4j_service.disconnect()
        await redis_service.disconnect()
        logger.info("All services shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="Infinite Scribe API Gateway",
    description="API Gateway for the Infinite Scribe platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
# Place CancelledError middleware outermost to swallow shutdown cancellations early
app.add_middleware(CancelledErrorMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(docs.router, tags=["documentation"])
app.include_router(health.router, tags=["health"])
app.include_router(v1.router, prefix="/api/v1")

# Include admin routes (conditionally based on environment)
if settings.environment == "development" or settings.launcher.admin_enabled:
    from src.api.routes.admin import launcher as launcher_admin

    app.include_router(launcher_admin.router, tags=["admin"])
