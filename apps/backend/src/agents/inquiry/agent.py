#!/usr/bin/env python
"""
Inquiry Agent - Handle query requests

Responsible for processing user queries and questions.
Includes:
- Novel progress queries
- Character information queries
- World setting queries
- System function explanations
- Creation status queries
"""

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.agents.errors import NonRetriableError
from src.external.clients.llm import ChatMessage, LLMRequest
from src.services.llm import LLMService, LLMServiceFactory

logger = logging.getLogger(__name__)


class InquiryAgent(BaseAgent):
    """Query Assistant Agent - Handle all query requests"""

    def __init__(
        self,
        name: str | None = None,
        consume_topics: list[str] | None = None,
        produce_topics: list[str] | None = None,
        llm_service: LLMService | None = None,
    ):
        """
        Initialize InquiryAgent

        Args:
            name: Agent name (provided by launcher, defaults to "inquiry")
            consume_topics: Topics to consume (provided by launcher, falls back to config)
            produce_topics: Topics to produce (provided by launcher, falls back to config)
            llm_service: LLM service instance for understanding queries and generating responses
        """
        # Read topic mapping from centralized configuration (single source of truth)
        from src.agents.agent_config import get_agent_topics

        config_consume, config_produce = get_agent_topics("inquiry")
        # Use provided topics if available (from launcher), otherwise use config
        final_consume = consume_topics if consume_topics is not None else config_consume
        final_produce = produce_topics if produce_topics is not None else config_produce
        final_name = name or "inquiry"

        super().__init__(name=final_name, consume_topics=final_consume, produce_topics=final_produce)

        # Initialize LLM service
        self.llm_service = llm_service or LLMServiceFactory().create_service()

        # Query handlers mapping
        self.query_handlers = {
            "progress": self._handle_progress_query,
            "character": self._handle_character_query,
            "world": self._handle_world_query,
            "system": self._handle_system_query,
            "general": self._handle_general_query,
        }

        logger.info("InquiryAgent initialized")

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """
        Process query message

        Args:
            message: Input message containing query content
            context: Message context

        Returns:
            Query result dictionary
        """
        # Debug: log message structure
        message_type = (context or {}).get("meta", {}).get("type") or message.get("type")
        logger.info(
            f"InquiryAgent processing message: {message_type}",
            extra={
                "message_keys": list(message.keys()),
                "context_keys": list(context.keys()) if context else [],
                "has_meta": "meta" in (context or {}),
                "meta_type": (context or {}).get("meta", {}).get("type") if context else None,
                "message_type": message.get("type"),
            },
        )

        # Extract query content
        query = self._extract_query(message)
        if not query:
            raise NonRetriableError("No query content found in message")

        # Extract relevant context information
        session_id = message.get("session_id")
        user_id = context.get("user_id") if context else None
        novel_id = context.get("novel_id") if context else None

        # Analyze query type
        query_type = await self._analyze_query_type(query)
        logger.info(f"Query type identified: {query_type}")

        # Route to corresponding handler
        handler = self.query_handlers.get(query_type, self._handle_general_query)

        # Execute query processing
        response = await handler(
            query=query, session_id=session_id, user_id=user_id, novel_id=novel_id, context=context
        )

        # Build response message
        # IMPORTANT: Use "type" not "event_type" - this is the Agent system convention
        return {
            "type": "Inquiry.Response.Generated",  # Agent消息类型字段
            "status": "success",
            "agent": self.name,
            "query_type": query_type,
            "query": query,
            "response": response,
            "session_id": session_id,
            "metadata": {
                "user_id": user_id,
                "novel_id": novel_id,
                "timestamp": self._get_timestamp(),
            },
        }

    def _extract_query(self, message: dict[str, Any]) -> str | None:
        """Extract query content from message"""
        # Try multiple possible fields
        candidates = [
            message.get("query"),
            message.get("input", {}).get("user_input") if isinstance(message.get("input"), dict) else None,
            message.get("input", {}).get("query") if isinstance(message.get("input"), dict) else None,
            message.get("content"),
            message.get("text"),
            message.get("user_input"),  # Direct user_input field
        ]

        # Debug: log extraction attempt
        logger.debug(
            f"_extract_query: message_keys={list(message.keys())}, "
            f"has_input={'input' in message}, "
            f"input_keys={list(message.get('input', {}).keys()) if isinstance(message.get('input'), dict) else 'N/A'}"
        )

        for idx, candidate in enumerate(candidates):
            if isinstance(candidate, str) and candidate.strip():
                logger.info(f"Query extracted from candidate[{idx}]: {candidate[:50]}...")
                return candidate.strip()

        logger.warning("No query content found in any candidate field")
        return None

    async def _analyze_query_type(self, query: str) -> str:
        """
        Analyze query type

        Args:
            query: Query content

        Returns:
            Query type: progress/character/world/system/general
        """
        # Use simple keyword matching
        query_lower = query.lower()

        if any(keyword in query_lower for keyword in ["progress", "status"]):
            return "progress"
        elif any(keyword in query_lower for keyword in ["character", "protagonist", "hero"]):
            return "character"
        elif any(keyword in query_lower for keyword in ["world", "setting", "universe"]):
            return "world"
        elif any(keyword in query_lower for keyword in ["system", "function", "how", "work"]):
            return "system"
        else:
            return "general"

    async def _handle_progress_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle progress query"""
        # TODO: Implementation needs to query database for real progress
        response_text = await self._generate_response(
            query=query,
            query_type="progress",
            context_info={
                "session_id": session_id,
                "novel_id": novel_id,
                "message": "This is a query about creation progress",
            },
        )

        return {
            "type": "progress",
            "text": response_text,
            "data": {
                # Simulated progress data
                "current_stage": "character_design",
                "completion": 30,
                "chapters_written": 0,
                "characters_created": 2,
            },
        }

    async def _handle_character_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle character query"""
        # TODO: Implementation needs to get character info from knowledge base
        response_text = await self._generate_response(
            query=query,
            query_type="character",
            context_info={
                "session_id": session_id,
                "novel_id": novel_id,
                "message": "This is a query about characters",
            },
        )

        return {
            "type": "character",
            "text": response_text,
            "data": {
                # Simulated character data
                "characters": [],
                "main_character": None,
            },
        }

    async def _handle_world_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle world setting query"""
        # TODO: Implementation needs to get world info from knowledge base
        response_text = await self._generate_response(
            query=query,
            query_type="world",
            context_info={
                "session_id": session_id,
                "novel_id": novel_id,
                "message": "This is a query about world settings",
            },
        )

        return {
            "type": "world",
            "text": response_text,
            "data": {
                # Simulated world data
                "setting": None,
                "locations": [],
            },
        }

    async def _handle_system_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle system function query"""
        response_text = await self._generate_response(
            query=query, query_type="system", context_info={"message": "This is a query about system functions"}
        )

        return {
            "type": "system",
            "text": response_text,
            "data": {
                "features": [
                    "Character generation",
                    "World building",
                    "Plot design",
                    "Chapter writing",
                    "Dialogue generation",
                ]
            },
        }

    async def _handle_general_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle general query"""
        response_text = await self._generate_response(
            query=query,
            query_type="general",
            context_info={
                "session_id": session_id,
                "novel_id": novel_id,
            },
        )

        return {"type": "general", "text": response_text, "data": {}}

    async def _generate_response(self, query: str, query_type: str, context_info: dict[str, Any]) -> str:
        """
        Generate query response using LLM

        Args:
            query: Original query
            query_type: Query type
            context_info: Context information

        Returns:
            Generated response text
        """
        # Build system prompt
        system_prompt = f"""You are InfiniteScribe's query assistant, specialized in answering user queries about novel creation.

Current query type: {query_type}
Context information: {context_info}

Please provide accurate and helpful answers based on the query content. If specific data or status is involved, please note that this is sample data (as the system is still in development).
"""

        # Build user message
        user_message = f"User query: {query}"

        try:
            # Call LLM
            request = LLMRequest(
                model="deepseek-chat",  # Use fast model
                messages=[
                    ChatMessage(role="system", content=system_prompt),
                    ChatMessage(role="user", content=user_message),
                ],
                temperature=0.7,
                max_tokens=500,
            )

            response = await self.llm_service.generate(request)
            return response.content or "Sorry, I couldn't understand your query."

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return self._get_fallback_response(query_type)

    def _get_fallback_response(self, query_type: str) -> str:
        """Get fallback response"""
        fallback_responses = {
            "progress": "Current creation is in progress, please check back later for detailed progress.",
            "character": "Character information is being organized, please check back later.",
            "world": "World settings are being built, please check back later.",
            "system": "InfiniteScribe provides intelligent novel creation assistance, including character design, world building, plot generation, etc.",
            "general": "Thank you for your query, I'm processing it.",
        }
        return fallback_responses.get(query_type, "Sorry, I'm unable to answer your question at the moment.")

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()

    async def on_start(self):
        """Initialize on startup"""
        logger.info("InquiryAgent starting...")
        # TODO: Initialize knowledge base connections, cache, etc.

    async def on_stop(self):
        """Cleanup on stop"""
        logger.info("InquiryAgent stopping...")
        # TODO: Clean up resources, close connections, etc.
