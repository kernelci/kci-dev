import io

import pytest
import yaml

from kcidev.subcommands.results.parser import filter_out_by_tree, parse_filter_file


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
