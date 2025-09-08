"""API Gateway main entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import docs, health, v1
from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    import logging

    from src.db.graph import neo4j_service
    from src.db.redis import redis_service
    from src.db.sql import postgres_service

    logger = logging.getLogger(__name__)

    # Startup
    try:
        logger.info("Initializing database connections...")
        await postgres_service.connect()
        await neo4j_service.connect()
        await redis_service.connect()

        postgres_ok = await postgres_service.check_connection()
        neo4j_ok = await neo4j_service.check_connection()
        redis_ok = await redis_service.check_connection()

        if postgres_ok:
            logger.info("PostgreSQL connection established successfully")
        else:
            logger.error("Failed to establish PostgreSQL connection")

        if neo4j_ok:
            logger.info("Neo4j connection established successfully")
        else:
            logger.error("Failed to establish Neo4j connection")

        if redis_ok:
            logger.info("Redis connection established successfully")
        else:
            logger.error("Failed to establish Redis connection")

        # Initialize SSE provider (app-scoped)
        try:
            from src.services.sse.provider import SSEProvider

            logger.info("Initializing SSE provider...")
            app.state.sse_provider = SSEProvider(redis_service)
            # Eagerly initialize to catch errors early
            await app.state.sse_provider.get_redis_sse_service()
            await app.state.sse_provider.get_connection_manager()
            logger.info("SSE provider initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SSE provider: {e}")
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
