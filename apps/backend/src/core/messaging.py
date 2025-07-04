"""Messaging configuration for Kafka integration."""

import logging
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from src.core.config import settings

logger = logging.getLogger(__name__)


class KafkaManager:
    """Kafka connection and producer management."""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        
    async def start(self):
        """Start Kafka producer."""
        if self.producer is not None:
            return
            
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else v,
                key_serializer=lambda k: k.encode('utf-8') if isinstance(k, str) else k,
                acks='all',  # Wait for all replicas
                retries=3,
                retry_backoff_ms=300,
                request_timeout_ms=60000,
                max_request_size=10485760,  # 10MB
                compression_type='gzip'
            )
            await self.producer.start()
            logger.info(f"Kafka producer started successfully. Bootstrap servers: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            self.producer = None
            raise
    
    async def stop(self):
        """Stop Kafka producer."""
        if self.producer is not None:
            try:
                await self.producer.stop()
                logger.info("Kafka producer stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {e}")
            finally:
                self.producer = None
    
    async def send_message(
        self,
        topic: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        headers: Optional[Dict[str, bytes]] = None,
        partition: Optional[int] = None,
    ) -> bool:
        """
        Send a message to Kafka topic.
        
        Args:
            topic: Kafka topic name
            key: Message key
            value: Message value
            headers: Message headers
            partition: Target partition (optional)
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if self.producer is None:
            logger.error("Kafka producer not started")
            return False
            
        try:
            # Convert headers to bytes if provided
            kafka_headers = None
            if headers:
                kafka_headers = [(k, v.encode('utf-8') if isinstance(v, str) else v) 
                               for k, v in headers.items()]
            
            # Send message
            await self.producer.send_and_wait(
                topic=topic,
                key=key,
                value=value,
                headers=kafka_headers,
                partition=partition
            )
            
            logger.debug(f"Message sent to topic {topic} with key {key}")
            return True
            
        except KafkaError as e:
            logger.error(f"Kafka error sending message to topic {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to topic {topic}: {e}")
            return False
    
    async def check_health(self) -> bool:
        """Check Kafka connection health."""
        if self.producer is None:
            return False
            
        try:
            # Get cluster metadata as health check
            metadata = await self.producer.client.fetch_metadata()
            return len(metadata.brokers) > 0
        except Exception as e:
            logger.error(f"Kafka health check failed: {e}")
            return False


# Global Kafka manager instance
kafka_manager = KafkaManager()