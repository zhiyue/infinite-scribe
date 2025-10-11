#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test Intent Classification System"""

import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_intent_classifier():
    """Test IntentClassifier basic functionality"""
    from src.agents.orchestrator.intent_classifier import IntentClassifier

    # Create classifier instance (without LLM for heuristic testing)
    classifier = IntentClassifier(llm_service=None, logger=logger)

    # Test cases
    test_cases = [
        # Inquiry test cases
        ("What is the current progress?", "inquiry"),
        ("Show me all created characters", "inquiry"),
        ("How does this system work?", "inquiry"),
        ("What is the main character personality?", "inquiry"),
        ("List the world settings", "inquiry"),

        # Generation test cases
        ("Generate a new character", "generation"),
        ("Create the first chapter plot", "generation"),
        ("Continue writing the next paragraph", "generation"),
        ("Design a magic system", "generation"),
        ("Write an opening scene", "generation"),
    ]

    print("\n=== Test Heuristic Intent Classification ===\n")

    for text, expected_intent in test_cases:
        result = await classifier.classify(user_input=text)

        status = "PASS" if result.intent == expected_intent else "FAIL"
        print(f"[{status}] Input: {text}")
        print(f"      Expected: {expected_intent}, Actual: {result.intent}")
        print(f"      Confidence: {result.confidence:.2f}, Source: {result.source}")
        if result.reasoning:
            print(f"      Reasoning: {result.reasoning}")
        print()


async def test_domain_event_processor():
    """Test DomainEventProcessor intent routing"""
    from src.agents.orchestrator.domain_event_processor import DomainEventProcessor
    from src.agents.orchestrator.intent_classifier import IntentClassifier

    # Create processor instance
    classifier = IntentClassifier(llm_service=None, logger=logger)
    processor = DomainEventProcessor(logger=logger, intent_classifier=classifier)

    # Simulate domain events
    test_events = [
        {
            "system": {
                "event_type": "Genesis.Session.Command.Received",
                "aggregate_id": "test-session-123",
                "metadata": {
                    "user_id": "user-456",
                    "novel_id": "novel-789",
                },
            },
            "data": {
                "command_type": "Command.Genesis.Session.Details.Request",
                "payload": {
                    "user_input": "What is the current progress?"
                }
            }
        },
        {
            "system": {
                "event_type": "Genesis.Session.Command.Received",
                "aggregate_id": "test-session-456",
                "metadata": {
                    "user_id": "user-456",
                    "novel_id": "novel-789",
                },
            },
            "data": {
                "command_type": "Command.Genesis.Session.Details.Request",
                "payload": {
                    "user_input": "Generate a new character"
                }
            }
        }
    ]

    print("\n=== Test Domain Event Processing ===\n")

    for i, event in enumerate(test_events, 1):
        print(f"Test Event {i}:")
        user_input = event["data"]["payload"]["user_input"]
        print(f"User Input: {user_input}")

        result = await processor.handle_domain_event(event)

        if result:
            mapping = result.get("mapping")
            enriched_payload = result.get("enriched_payload", {})

            print(f"Routing Result:")
            print(f"  - Requested Action: {mapping.requested_action}")
            print(f"  - Capability Type: {mapping.capability_message.get('type')}")
            print(f"  - Topic: {mapping.capability_message.get('_topic')}")

            if "intent" in enriched_payload:
                print(f"Intent Classification:")
                print(f"  - Intent: {enriched_payload['intent']}")
                print(f"  - Confidence: {enriched_payload.get('intent_confidence', 'N/A')}")
                print(f"  - Source: {enriched_payload.get('intent_source', 'N/A')}")
        else:
            print("Event processing failed")

        print("-" * 50)


async def main():
    """Main test function"""
    print("=" * 60)
    print("Intent Classification System Test")
    print("=" * 60)

    # Test classifier
    await test_intent_classifier()

    # Test event processor
    await test_domain_event_processor()

    print("\nTest completed!")


if __name__ == "__main__":
    asyncio.run(main())
