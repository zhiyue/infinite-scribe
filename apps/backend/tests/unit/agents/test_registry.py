"""Unit tests for agent registry and canonical ID functions"""

import pytest
from src.agents.agent_config import (
    canonical_id_from_config_key,
    canonicalize_agent_id,
    get_agent_topics,
    to_config_key,
)
from src.agents.base import BaseAgent
from src.agents.registry import (
    _REGISTRY,
    get_registered_agent,
    list_registered_agents,
    register_agent,
)


class TestAgentRegistry:
    """Test agent registry functionality"""

    def setup_method(self):
        """Clear registry before each test"""
        _REGISTRY.clear()

    def test_register_valid_agent(self):
        """Test registering a valid agent class"""

        class TestAgent(BaseAgent):
            pass

        register_agent("test_agent", TestAgent)
        assert get_registered_agent("test_agent") == TestAgent

    def test_register_invalid_class(self):
        """Test registering a non-BaseAgent class raises error"""

        class NotAnAgent:
            pass

        with pytest.raises(ValueError, match="must inherit from BaseAgent"):
            register_agent("invalid", NotAnAgent)

    def test_register_none_class(self):
        """Test registering None raises error"""
        with pytest.raises(ValueError, match="must inherit from BaseAgent"):
            register_agent("none_agent", None)  # type: ignore

    def test_register_duplicate_agent_id(self):
        """Test registering duplicate agent IDs overwrites previous"""

        class TestAgent1(BaseAgent):
            pass

        class TestAgent2(BaseAgent):
            pass

        register_agent("test", TestAgent1)
        assert get_registered_agent("test") == TestAgent1

        register_agent("test", TestAgent2)
        assert get_registered_agent("test") == TestAgent2

    def test_get_unregistered_agent(self):
        """Test getting unregistered agent returns None"""
        assert get_registered_agent("nonexistent") is None

    def test_list_registered_agents(self):
        """Test listing registered agents returns sorted list"""

        class Agent1(BaseAgent):
            pass

        class Agent2(BaseAgent):
            pass

        register_agent("zebra", Agent1)
        register_agent("alpha", Agent2)

        agents = list_registered_agents()
        assert agents == ["alpha", "zebra"]

    def test_canonical_registration(self):
        """Test agent registration uses canonical IDs"""

        class TestAgent(BaseAgent):
            pass

        # Register with different formats
        register_agent("character_expert", TestAgent)

        # All should resolve to the same agent
        assert get_registered_agent("character_expert") == TestAgent
        assert get_registered_agent("characterexpert") == TestAgent
        assert get_registered_agent("CHARACTER_EXPERT") == TestAgent
        assert get_registered_agent("Character-Expert") == TestAgent


class TestCanonicalIds:
    """Test canonical ID transformation functions"""

    def test_canonicalize_agent_id(self):
        """Test canonicalizing agent IDs"""
        # Basic canonicalization
        assert canonicalize_agent_id("test_agent") == "test_agent"
        assert canonicalize_agent_id("TEST_AGENT") == "test_agent"
        assert canonicalize_agent_id("Test-Agent") == "test_agent"
        assert canonicalize_agent_id("  test_agent  ") == "test_agent"

        # Alias handling
        assert canonicalize_agent_id("characterexpert") == "character_expert"
        assert canonicalize_agent_id("factchecker") == "fact_checker"

        # Edge cases
        assert canonicalize_agent_id("") == ""
        assert canonicalize_agent_id("_") == "_"
        assert canonicalize_agent_id("-") == "_"

    def test_to_config_key(self):
        """Test converting canonical IDs to config keys"""
        # Normal cases
        assert to_config_key("writer") == "writer"
        assert to_config_key("director") == "director"

        # Aliased cases
        assert to_config_key("character_expert") == "characterexpert"
        assert to_config_key("fact_checker") == "factchecker"

        # Case insensitive
        assert to_config_key("CHARACTER_EXPERT") == "characterexpert"

    def test_canonical_id_from_config_key(self):
        """Test converting config keys to canonical IDs"""
        # Normal cases
        assert canonical_id_from_config_key("writer") == "writer"
        assert canonical_id_from_config_key("director") == "director"

        # Aliased cases
        assert canonical_id_from_config_key("characterexpert") == "character_expert"
        assert canonical_id_from_config_key("factchecker") == "fact_checker"

    def test_bidirectional_conversion(self):
        """Test conversions are bidirectional"""
        # For aliased agents
        canonical = "character_expert"
        config = to_config_key(canonical)
        assert config == "characterexpert"
        assert canonical_id_from_config_key(config) == canonical

        # For non-aliased agents
        canonical = "writer"
        config = to_config_key(canonical)
        assert config == "writer"
        assert canonical_id_from_config_key(config) == canonical

    def test_get_agent_topics(self):
        """Test getting agent topics"""
        # Known agents
        consume, produce = get_agent_topics("director")
        assert isinstance(consume, list)
        assert isinstance(produce, list)
        assert len(consume) > 0  # Director has consume topics
        assert len(produce) > 0  # Director has produce topics

        # Aliased agent
        consume, produce = get_agent_topics("character_expert")
        assert isinstance(consume, list)
        assert isinstance(produce, list)

        # Unknown agent returns empty lists
        consume, produce = get_agent_topics("nonexistent")
        assert consume == []
        assert produce == []

    def test_get_agent_topics_edge_cases(self):
        """Test edge cases for get_agent_topics"""
        # Empty string
        consume, produce = get_agent_topics("")
        assert consume == []
        assert produce == []

        # None handling would require modification to function
        # Skipping as function expects string


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def setup_method(self):
        """Clear registry before each test"""
        _REGISTRY.clear()

    def test_register_with_special_characters(self):
        """Test registration with special characters in ID"""

        class TestAgent(BaseAgent):
            pass

        # These should all work due to canonicalization
        register_agent("test!@#agent", TestAgent)
        register_agent("test...agent", TestAgent)
        register_agent("test___agent", TestAgent)

    def test_concurrent_registration(self):
        """Test concurrent registration doesn't cause issues"""

        class TestAgent(BaseAgent):
            pass

        # Simulate multiple registrations
        for _ in range(10):
            register_agent("concurrent", TestAgent)

        assert get_registered_agent("concurrent") == TestAgent

    def test_registry_isolation(self):
        """Test that registry modifications are isolated"""

        class TestAgent(BaseAgent):
            pass

        initial_count = len(_REGISTRY)
        register_agent("isolated", TestAgent)
        assert len(_REGISTRY) == initial_count + 1

        _REGISTRY.clear()
        assert len(_REGISTRY) == 0
        assert get_registered_agent("isolated") is None
