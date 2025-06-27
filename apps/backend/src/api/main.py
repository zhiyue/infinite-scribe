"""API Gateway main entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.api.routes import health, v1


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    import logging

    from src.common.services.neo4j_service import neo4j_service
    from src.common.services.postgres_service import postgres_service

    logger = logging.getLogger(__name__)

    # Startup
    try:
        logger.info("Initializing database connections...")
        await postgres_service.connect()
        await neo4j_service.connect()

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

    yield

    # Shutdown
    try:
        logger.info("Shutting down database connections...")
        await postgres_service.disconnect()
        await neo4j_service.disconnect()
        logger.info("Database connections closed successfully")
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
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(v1.router, prefix="/api/v1")
