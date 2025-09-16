#!/usr/bin/env python3

"""
Debug script to test round creation and see the exact error.
"""

import asyncio
import sys
import logging
from pathlib import Path
from uuid import UUID

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_round_creation():
    """Debug round creation to see exactly what's failing."""

    try:
        # Setup database connection
        from src.db.sql.service import PostgresService
        from src.core.config import settings

        # Mock database settings for local testing
        settings.database.postgres_host = "localhost"
        settings.database.postgres_port = 5432
        settings.database.postgres_user = "postgres"
        settings.database.postgres_password = "postgres"
        settings.database.postgres_db = "infinite_scribe"

        postgres_service = PostgresService()
        await postgres_service.connect()

        async with postgres_service.get_session() as db:
            # Import the service
            from src.common.services.conversation.conversation_round_creation_service import ConversationRoundCreationService
            from src.schemas.novel.dialogue import DialogueRole

            service = ConversationRoundCreationService()

            # Create a test scenario
            user_id = 123
            session_id = UUID("12345678-1234-5678-1234-567812345678")

            result = await service.create_round(
                db,
                user_id,
                session_id,
                role=DialogueRole.USER,
                input_data={"message": "Hello, test"},
                model="gpt-4",
                correlation_id="test-correlation-123"
            )

            logger.info(f"Round creation result: {result}")

            if not result.get("success"):
                logger.error(f"Failed to create round: {result.get('error')}")
                logger.error(f"Error code: {result.get('code')}")

    except Exception as e:
        logger.error(f"Debug error: {e}", exc_info=True)
    finally:
        await postgres_service.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_round_creation())