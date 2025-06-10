import io
from datetime import datetime, timedelta

import pytest
import yaml

from kcidev.subcommands.results.parser import (
    filter_out_by_compiler,
    filter_out_by_date,
    filter_out_by_tree,
    parse_filter_file,
)


class TestTreeFilter:
    """Test tree filter functionality"""

    def test_filter_out_by_tree_matching(self):
        """Test tree filter with matching tree name"""
        test_data = {"tree_name": "mainline"}
        filter_data = {"tree": "^(mainline)$"}

        # Should not filter out (return False) when tree matches
        assert filter_out_by_tree(test_data, filter_data) is False

    def test_filter_out_by_tree_not_matching(self):
        """Test tree filter with non-matching tree name"""
        test_data = {"tree_name": "linux-next"}
        filter_data = {"tree": "^(mainline)$"}

        # Should filter out (return True) when tree doesn't match
        assert filter_out_by_tree(test_data, filter_data) is True

    def test_filter_out_by_tree_missing_tree_in_data(self):
        """Test tree filter when tree_name is missing in test data"""
        test_data = {}
        filter_data = {"tree": "^(mainline)$"}

        # Should filter out when tree_name is missing
        assert filter_out_by_tree(test_data, filter_data) is True

    def test_filter_out_by_tree_no_filter(self):
        """Test tree filter when no tree filter is specified"""
        test_data = {"tree_name": "mainline"}
        filter_data = {}

        # Should not filter out when no tree filter is specified
        assert filter_out_by_tree(test_data, filter_data) is False

    def test_filter_out_by_tree_wildcard(self):
        """Test tree filter with wildcard pattern"""
        test_data = {"tree_name": "linux-next"}
        filter_data = {"tree": "^(linux.*)$"}

        # Should not filter out when pattern matches with wildcard
        assert filter_out_by_tree(test_data, filter_data) is False

    def test_filter_out_by_tree_multiple_options(self):
        """Test tree filter with multiple tree options"""
        test_data = {"tree_name": "stable"}
        filter_data = {"tree": "^(mainline|linux-next|stable)$"}

        # Should not filter out when tree matches one of the options
        assert filter_out_by_tree(test_data, filter_data) is False

    def test_parse_filter_file_with_tree(self):
        """Test parsing filter file with tree filter"""
        filter_yaml = """
hardware:
  - "rk3399-rock-pi-4b"
test:
  - "baseline.*"
tree:
  - "mainline"
  - "linux-next"
"""
        filter_file = io.StringIO(filter_yaml)
        parsed = parse_filter_file(filter_file)

        assert "tree" in parsed
        assert parsed["tree"] == "^(mainline|linux-next)$"

    def test_parse_filter_file_tree_only(self):
        """Test parsing filter file with only tree filter"""
        filter_yaml = """
tree:
  - "stable"
"""
        filter_file = io.StringIO(filter_yaml)
        parsed = parse_filter_file(filter_file)

        assert "tree" in parsed
        assert parsed["tree"] == "^(stable)$"
        assert "hardware" not in parsed
        assert "test" not in parsed


class TestDateFilter:
    """Test date filter functionality"""

    def test_filter_out_by_date_with_start_date(self):
        """Test filtering with start date only"""
        # Item with date before start date - should be filtered out
        item_old = {"start_time": "2025-01-01T10:00:00Z"}
        assert filter_out_by_date(item_old, "2025-01-15", None)

        # Item with date after start date - should not be filtered out
        item_new = {"start_time": "2025-01-20T10:00:00Z"}
        assert not filter_out_by_date(item_new, "2025-01-15", None)

    def test_filter_out_by_date_with_end_date(self):
        """Test filtering with end date only"""
        # Item with date before end date - should not be filtered out
        item_old = {"start_time": "2025-01-01T10:00:00Z"}
        assert not filter_out_by_date(item_old, None, "2025-01-15")

        # Item with date after end date - should be filtered out
        item_new = {"start_time": "2025-01-20T10:00:00Z"}
        assert filter_out_by_date(item_new, None, "2025-01-15")

    def test_filter_out_by_date_with_date_range(self):
        """Test filtering with both start and end dates"""
        # Item within range - should not be filtered out
        item_in_range = {"start_time": "2025-01-15T10:00:00Z"}
        assert not filter_out_by_date(item_in_range, "2025-01-10", "2025-01-20")

        # Item before range - should be filtered out
        item_before = {"start_time": "2025-01-05T10:00:00Z"}
        assert filter_out_by_date(item_before, "2025-01-10", "2025-01-20")

        # Item after range - should be filtered out
        item_after = {"start_time": "2025-01-25T10:00:00Z"}
        assert filter_out_by_date(item_after, "2025-01-10", "2025-01-20")

    def test_filter_out_by_date_with_different_timestamp_fields(self):
        """Test that different timestamp fields are handled correctly"""
        # Test with 'created' field
        item_created = {"created": "2025-01-15T10:00:00Z"}
        assert not filter_out_by_date(item_created, "2025-01-10", "2025-01-20")

        # Test with 'updated' field
        item_updated = {"updated": "2025-01-15T10:00:00Z"}
        assert not filter_out_by_date(item_updated, "2025-01-10", "2025-01-20")

    def test_filter_out_by_date_with_no_timestamp(self):
        """Test that items without timestamp fields are not filtered out"""
        item = {"other_field": "value"}
        assert not filter_out_by_date(item, "2025-01-10", "2025-01-20")

    def test_filter_out_by_date_with_no_filters(self):
        """Test that no filtering occurs when no date filters are provided"""
        item = {"start_time": "2025-01-15T10:00:00Z"}
        assert not filter_out_by_date(item, None, None)
        assert not filter_out_by_date(item, "", "")


class TestCompilerFilter:
    """Test compiler filter functionality"""

    def test_filter_out_by_compiler_matching(self):
        """Test that items with matching compiler are not filtered out"""
        item = {"compiler": "gcc", "other_field": "value"}
        assert not filter_out_by_compiler(item, "gcc")

    def test_filter_out_by_compiler_non_matching(self):
        """Test that items with non-matching compiler are filtered out"""
        item = {"compiler": "gcc", "other_field": "value"}
        assert filter_out_by_compiler(item, "clang")

    def test_filter_out_by_compiler_case_insensitive(self):
        """Test that compiler filter is case insensitive"""
        item = {"compiler": "GCC"}
        assert not filter_out_by_compiler(item, "gcc")

        item = {"compiler": "gcc"}
        assert not filter_out_by_compiler(item, "GCC")

    def test_filter_out_by_compiler_no_filter(self):
        """Test that no filtering occurs when compiler filter is None"""
        item = {"compiler": "gcc"}
        assert not filter_out_by_compiler(item, None)
        assert not filter_out_by_compiler(item, "")

    def test_filter_out_by_compiler_missing_field(self):
        """Test that items without compiler field are filtered out when filter is active"""
        item = {"other_field": "value"}
        assert filter_out_by_compiler(item, "gcc")
