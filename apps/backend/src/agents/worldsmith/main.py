"""Worldsmith Agent main entry point."""

import asyncio
import logging

from src.core.config import settings

logger = logging.getLogger(__name__)


async def main():
    """Main function for Worldsmith Agent."""
    logger.info(f"Starting Worldsmith Agent with config: {settings.service_type}")
    # TODO: Implement agent logic
    # - Connect to Kafka
    # - Subscribe to relevant topics
    # - Process messages
    # - Send results


def run():
    """Run the Worldsmith Agent."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
