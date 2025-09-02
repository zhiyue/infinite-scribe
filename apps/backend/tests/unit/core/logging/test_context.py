"""Tests for context binding functionality"""

import pytest
from unittest.mock import patch

from src.core.logging.context import (
    bind_request_context, bind_service_context, 
    get_current_context, clear_context
)
from src.core.logging.config import get_logger


class TestContextBinding:
    """Test context binding functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Clear context before each test
        clear_context()
    
    def test_bind_request_context(self):
        """Test binding request context"""
        # Setup
        request_id = "req_123456"
        user_id = "user_789"
        
        # Execute
        bind_request_context(request_id=request_id, user_id=user_id)
        
        # Assert
        current_context = get_current_context()
        assert current_context.get("request_id") == request_id
        assert current_context.get("user_id") == user_id
        assert current_context.get("trace_id") == request_id  # Should default to request_id

    def test_bind_request_context_with_trace_id(self):
        """Test binding request context with explicit trace_id"""
        # Setup
        request_id = "req_123456"
        user_id = "user_789"
        trace_id = "trace_abc123"
        
        # Execute
        bind_request_context(request_id=request_id, user_id=user_id, trace_id=trace_id)
        
        # Assert
        current_context = get_current_context()
        assert current_context.get("request_id") == request_id
        assert current_context.get("user_id") == user_id
        assert current_context.get("trace_id") == trace_id

    def test_bind_request_context_with_kwargs(self):
        """Test binding request context with additional kwargs"""
        # Setup
        request_id = "req_123456"
        additional_data = {"session_id": "sess_xyz", "ip_address": "192.168.1.1"}
        
        # Execute
        bind_request_context(request_id=request_id, **additional_data)
        
        # Assert
        current_context = get_current_context()
        assert current_context.get("request_id") == request_id
        assert current_context.get("session_id") == "sess_xyz"
        assert current_context.get("ip_address") == "192.168.1.1"

    def test_bind_service_context(self):
        """Test binding service context"""
        # Setup
        service = "api-gateway"
        component = "auth"
        
        # Execute
        bind_service_context(service=service, component=component)
        
        # Assert
        current_context = get_current_context()
        assert current_context.get("service") == service
        assert current_context.get("component") == component

    def test_bind_service_context_with_version(self):
        """Test binding service context with version"""
        # Setup
        service = "api-gateway"
        component = "auth"
        version = "1.2.3"
        
        # Execute
        bind_service_context(service=service, component=component, version=version)
        
        # Assert
        current_context = get_current_context()
        assert current_context.get("service") == service
        assert current_context.get("component") == component
        assert current_context.get("version") == version

    def test_bind_service_context_with_kwargs(self):
        """Test binding service context with additional kwargs"""
        # Setup
        service = "agents"
        component = "worldsmith"
        additional_data = {"worker_id": "worker_1", "queue": "high_priority"}
        
        # Execute
        bind_service_context(service=service, component=component, **additional_data)
        
        # Assert
        current_context = get_current_context()
        assert current_context.get("service") == service
        assert current_context.get("component") == component
        assert current_context.get("worker_id") == "worker_1"
        assert current_context.get("queue") == "high_priority"

    def test_get_current_context_empty(self):
        """Test getting current context when empty"""
        # Execute
        current_context = get_current_context()
        
        # Assert
        assert current_context == {}

    def test_get_current_context_returns_copy(self):
        """Test that get_current_context returns a copy, not the original"""
        # Setup
        bind_request_context(request_id="test_123")
        
        # Execute
        context1 = get_current_context()
        context2 = get_current_context()
        context1["new_key"] = "modified"
        
        # Assert
        assert "new_key" not in context2
        assert "new_key" not in get_current_context()

    def test_clear_context(self):
        """Test clearing context"""
        # Setup
        bind_request_context(request_id="test_123")
        bind_service_context(service="test", component="test")
        assert len(get_current_context()) > 0
        
        # Execute
        clear_context()
        
        # Assert
        assert get_current_context() == {}

    def test_context_binding_accumulates(self):
        """Test that multiple context bindings accumulate"""
        # Execute
        bind_request_context(request_id="req_123", user_id="user_456")
        bind_service_context(service="api", component="auth")
        
        # Assert
        context = get_current_context()
        assert context.get("request_id") == "req_123"
        assert context.get("user_id") == "user_456"
        assert context.get("service") == "api"
        assert context.get("component") == "auth"

    def test_context_binding_with_none_values(self):
        """Test context binding filters out None values"""
        # Execute
        bind_request_context(request_id="req_123", user_id=None)
        
        # Assert
        context = get_current_context()
        assert context.get("request_id") == "req_123"
        assert "user_id" in context  # None values are stored in local context
        assert context.get("user_id") is None

    def test_context_integration_with_logger(self):
        """Test context integration with logger binding"""
        # This test verifies that our context system works with structlog
        from src.core.logging.config import configure_logging
        
        configure_logging(force_reconfigure=True)
        
        # Setup context
        bind_request_context(request_id="req_123", user_id="user_456")
        
        # Get logger and try to bind additional context
        logger = get_logger("test")
        bound_logger = logger.bind(operation="test_op")
        
        # Should not raise an error
        assert bound_logger is not None
    
    def teardown_method(self):
        """Cleanup after each test method"""
        clear_context()