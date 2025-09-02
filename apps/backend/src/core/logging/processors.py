"""Custom processors for structured logging"""

from typing import Any


class SerializationFallbackProcessor:
    """Serialization fallback processor"""

    def __call__(self, logger, name, event_dict: dict[str, Any]) -> dict[str, Any]:
        """Process event dict and handle non-serializable objects"""
        has_fallback = False

        for key, value in event_dict.items():
            if not self._is_serializable(value):
                event_dict[key] = str(value)
                has_fallback = True

        if has_fallback:
            event_dict["serialization_fallback"] = True

        return event_dict

    def _is_serializable(self, obj: Any) -> bool:
        """Check if object is JSON serializable using safelist approach"""
        # Define safe types that are guaranteed to be JSON serializable
        safe_types = (str, int, float, bool, type(None))

        if isinstance(obj, safe_types):
            return True

        # Handle containers (list, dict) with recursive checking
        if isinstance(obj, list | tuple):
            try:
                # Check if all elements are safe types or serializable containers
                return all(self._is_serializable(item) for item in obj)
            except (TypeError, RecursionError):
                return False

        if isinstance(obj, dict):
            try:
                # Check if all keys and values are safe
                return all(isinstance(key, str | int | float) for key in obj) and all(
                    self._is_serializable(value) for value in obj.values()
                )
            except (TypeError, RecursionError):
                return False

        # All other types are considered non-serializable for security
        return False


class StandardFieldsProcessor:
    """
    Standard fields processor (default not enabled to avoid duplicate with TimeStamper)

    Note: Currently not used in default processor chain because:
    1. Timestamp is handled by TimeStamper uniformly
    2. Avoid duplicate addition of fields in processor chain
    3. Can be enabled on demand in specific scenarios
    """

    def __call__(self, logger, name, event_dict: dict[str, Any]) -> dict[str, Any]:
        """Add standard fields (excluding timestamp)"""
        # Example: Can add global standard fields
        # event_dict.setdefault('service_version', '1.0.0')
        # event_dict.setdefault('deployment', 'production')
        return event_dict
