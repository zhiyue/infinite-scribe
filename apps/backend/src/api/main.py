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

    from src.common.services.neo4j_service import neo4j_service
    from src.common.services.postgres_service import postgres_service
    from src.common.services.redis_service import redis_service

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

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")

    yield

    # Shutdown
    try:
        logger.info("Shutting down services...")

        # Clean up SSE services if initialized
        from src.api.routes.v1.events import cleanup_sse_services

        await cleanup_sse_services()

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
if settings.environment == "development" or (hasattr(settings, 'launcher') and 
                                           hasattr(settings.launcher, 'admin_enabled') and 
                                           settings.launcher.admin_enabled):
    from src.api.routes.admin import launcher as launcher_admin
    app.include_router(launcher_admin.router)
