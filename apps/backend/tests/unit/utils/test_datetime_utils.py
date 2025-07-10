"""Unit tests for datetime utility functions."""

import pytest
from datetime import UTC, datetime, timezone, timedelta

from src.common.utils.datetime_utils import (
    utc_now,
    from_timestamp_utc,
    ensure_utc,
    to_timestamp,
    parse_iso_datetime,
    format_iso_datetime,
)


class TestDatetimeUtils:
    """Test cases for datetime utility functions."""

    def test_utc_now(self):
        """Test utc_now returns current UTC time with timezone info."""
        # Act
        result = utc_now()
        
        # Assert
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC
        
        # Verify it's close to the actual current time (within 1 second)
        current_time = datetime.now(UTC)
        time_diff = abs((result - current_time).total_seconds())
        assert time_diff < 1.0

    def test_from_timestamp_utc(self):
        """Test converting Unix timestamp to UTC datetime."""
        # Arrange
        timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        
        # Act
        result = from_timestamp_utc(timestamp)
        
        # Assert
        assert isinstance(result, datetime)
        assert result.tzinfo == UTC
        assert result.year == 2021
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_from_timestamp_utc_with_fractional_seconds(self):
        """Test converting timestamp with fractional seconds."""
        # Arrange
        timestamp = 1609459200.123456
        
        # Act
        result = from_timestamp_utc(timestamp)
        
        # Assert
        assert result.tzinfo == UTC
        assert result.microsecond == 123456

    def test_ensure_utc_with_naive_datetime(self):
        """Test ensure_utc with timezone-naive datetime."""
        # Arrange
        naive_dt = datetime(2021, 1, 1, 12, 0, 0)
        
        # Act
        result = ensure_utc(naive_dt)
        
        # Assert
        assert result.tzinfo == UTC
        assert result.year == 2021
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 0
        assert result.second == 0

    def test_ensure_utc_with_utc_datetime(self):
        """Test ensure_utc with already UTC datetime."""
        # Arrange
        utc_dt = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
        
        # Act
        result = ensure_utc(utc_dt)
        
        # Assert
        assert result.tzinfo == UTC
        assert result == utc_dt  # Should be identical

    def test_ensure_utc_with_other_timezone(self):
        """Test ensure_utc converts from other timezone to UTC."""
        # Arrange
        est = timezone(timedelta(hours=-5))  # EST timezone
        est_dt = datetime(2021, 1, 1, 7, 0, 0, tzinfo=est)  # 7 AM EST = 12 PM UTC
        
        # Act
        result = ensure_utc(est_dt)
        
        # Assert
        assert result.tzinfo == UTC
        assert result.hour == 12  # Converted to UTC
        assert result.minute == 0

    def test_to_timestamp_with_utc_datetime(self):
        """Test converting UTC datetime to timestamp."""
        # Arrange
        utc_dt = datetime(2021, 1, 1, 0, 0, 0, tzinfo=UTC)
        expected_timestamp = 1609459200.0
        
        # Act
        result = to_timestamp(utc_dt)
        
        # Assert
        assert abs(result - expected_timestamp) < 0.001  # Allow small floating point differences

    def test_to_timestamp_with_naive_datetime(self):
        """Test converting naive datetime to timestamp (assumes UTC)."""
        # Arrange
        naive_dt = datetime(2021, 1, 1, 0, 0, 0)
        expected_timestamp = 1609459200.0
        
        # Act
        result = to_timestamp(naive_dt)
        
        # Assert
        assert abs(result - expected_timestamp) < 0.001

    def test_to_timestamp_with_other_timezone(self):
        """Test converting datetime with different timezone to timestamp."""
        # Arrange
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2020, 12, 31, 19, 0, 0, tzinfo=est)  # 7 PM EST = 12 AM UTC next day
        expected_timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        
        # Act
        result = to_timestamp(est_dt)
        
        # Assert
        assert abs(result - expected_timestamp) < 0.001

    def test_parse_iso_datetime_valid_utc(self):
        """Test parsing valid ISO datetime string with UTC."""
        # Arrange
        iso_string = "2021-01-01T12:00:00Z"
        
        # Act
        result = parse_iso_datetime(iso_string)
        
        # Assert
        assert result is not None
        assert result.tzinfo == UTC
        assert result.year == 2021
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12

    def test_parse_iso_datetime_valid_with_timezone(self):
        """Test parsing ISO datetime string with timezone offset."""
        # Arrange
        iso_string = "2021-01-01T12:00:00+05:00"
        
        # Act
        result = parse_iso_datetime(iso_string)
        
        # Assert
        assert result is not None
        assert result.tzinfo is not None
        assert result.year == 2021
        assert result.hour == 12

    def test_parse_iso_datetime_naive(self):
        """Test parsing ISO datetime string without timezone (adds UTC)."""
        # Arrange
        iso_string = "2021-01-01T12:00:00"
        
        # Act
        result = parse_iso_datetime(iso_string)
        
        # Assert
        assert result is not None
        assert result.tzinfo == UTC
        assert result.year == 2021
        assert result.hour == 12

    def test_parse_iso_datetime_with_microseconds(self):
        """Test parsing ISO datetime string with microseconds."""
        # Arrange
        iso_string = "2021-01-01T12:00:00.123456Z"
        
        # Act
        result = parse_iso_datetime(iso_string)
        
        # Assert
        assert result is not None
        assert result.tzinfo == UTC
        assert result.microsecond == 123456

    def test_parse_iso_datetime_invalid(self):
        """Test parsing invalid ISO datetime string returns None."""
        # Arrange
        invalid_strings = [
            "invalid-date",
            "2021-13-01T12:00:00Z",  # Invalid month
            "2021-01-32T12:00:00Z",  # Invalid day
            "2021-01-01T25:00:00Z",  # Invalid hour
            "",
            None,
        ]
        
        for invalid_string in invalid_strings:
            # Act
            result = parse_iso_datetime(invalid_string)
            
            # Assert
            assert result is None, f"Expected None for invalid string: {invalid_string}"

    def test_format_iso_datetime_with_utc(self):
        """Test formatting UTC datetime to ISO string."""
        # Arrange
        utc_dt = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
        
        # Act
        result = format_iso_datetime(utc_dt)
        
        # Assert
        assert isinstance(result, str)
        assert "2021-01-01T12:00:00" in result
        assert "+00:00" in result or "Z" in result  # UTC timezone indicator

    def test_format_iso_datetime_with_naive(self):
        """Test formatting naive datetime to ISO string (converts to UTC)."""
        # Arrange
        naive_dt = datetime(2021, 1, 1, 12, 0, 0)
        
        # Act
        result = format_iso_datetime(naive_dt)
        
        # Assert
        assert isinstance(result, str)
        assert "2021-01-01T12:00:00" in result
        assert "+00:00" in result or "Z" in result

    def test_format_iso_datetime_with_other_timezone(self):
        """Test formatting datetime with other timezone to ISO string."""
        # Arrange
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2021, 1, 1, 7, 0, 0, tzinfo=est)  # 7 AM EST = 12 PM UTC
        
        # Act
        result = format_iso_datetime(est_dt)
        
        # Assert
        assert isinstance(result, str)
        # Should be converted to UTC (12:00)
        assert "12:00:00" in result
        assert "+00:00" in result or "Z" in result

    def test_format_iso_datetime_with_microseconds(self):
        """Test formatting datetime with microseconds."""
        # Arrange
        dt_with_microseconds = datetime(2021, 1, 1, 12, 0, 0, 123456, tzinfo=UTC)
        
        # Act
        result = format_iso_datetime(dt_with_microseconds)
        
        # Assert
        assert isinstance(result, str)
        assert "123456" in result

    def test_roundtrip_parse_and_format(self):
        """Test that parsing and formatting are consistent."""
        # Arrange
        original_dt = datetime(2021, 1, 1, 12, 30, 45, 123456, tzinfo=UTC)
        
        # Act
        iso_string = format_iso_datetime(original_dt)
        parsed_dt = parse_iso_datetime(iso_string)
        
        # Assert
        assert parsed_dt is not None
        assert parsed_dt == original_dt

    def test_ensure_utc_preserves_utc_offset(self):
        """Test that ensure_utc correctly converts different timezones."""
        # Test multiple timezone offsets
        timezones_and_expected_utc_hours = [
            (timezone(timedelta(hours=0)), 12),    # UTC
            (timezone(timedelta(hours=3)), 9),     # UTC+3 -> 9 AM UTC
            (timezone(timedelta(hours=-8)), 20),   # UTC-8 -> 8 PM UTC
            (timezone(timedelta(hours=5, minutes=30)), 6, 30),  # UTC+5:30 -> 6:30 AM UTC
        ]
        
        for tz_info in timezones_and_expected_utc_hours:
            tz = tz_info[0]
            expected_hour = tz_info[1]
            expected_minute = tz_info[2] if len(tz_info) > 2 else 0
            
            # Arrange
            local_dt = datetime(2021, 1, 1, 12, 0, 0, tzinfo=tz)
            
            # Act
            utc_dt = ensure_utc(local_dt)
            
            # Assert
            assert utc_dt.tzinfo == UTC
            assert utc_dt.hour == expected_hour
            assert utc_dt.minute == expected_minute