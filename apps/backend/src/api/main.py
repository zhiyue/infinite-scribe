"""API Gateway main entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import settings
from .routes import health, v1

app = FastAPI(
    title="Infinite Scribe API Gateway",
    description="API Gateway for the Infinite Scribe platform",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(v1.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    import logging

    from ..common.services.neo4j_service import neo4j_service
    from ..common.services.postgres_service import postgres_service

    logger = logging.getLogger(__name__)

    try:
        # Initialize database connections
        logger.info("Initializing database connections...")
        await postgres_service.connect()
        await neo4j_service.connect()

        # Verify connections
        postgres_ok = await postgres_service.check_connection()
        neo4j_ok = await neo4j_service.check_connection()

        if postgres_ok:
            logger.info("PostgreSQL connection established successfully")
        else:
            logger.error("Failed to establish PostgreSQL connection")

        if neo4j_ok:
            logger.info("Neo4j connection established successfully")
        else:
            logger.error("Failed to establish Neo4j connection")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Don't prevent startup, let health checks handle it


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    import logging

    from ..common.services.neo4j_service import neo4j_service
    from ..common.services.postgres_service import postgres_service

    logger = logging.getLogger(__name__)

    try:
        logger.info("Shutting down database connections...")
        await postgres_service.disconnect()
        await neo4j_service.disconnect()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
