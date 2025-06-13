import io
from datetime import datetime, timedelta

import pytest
import yaml

from kcidev.libs.filters import (
    CompatibleFilter,
    CompilerFilter,
    ConfigFilter,
    DateRangeFilter,
    DurationFilter,
    GitBranchFilter,
    HardwareFilter,
    PathFilter,
)
from kcidev.libs.job_filters import TreeFilter
from kcidev.subcommands.results.parser import parse_filter_file


class TestTreeFilter:
    """Test tree filter functionality"""

    def test_tree_filter_matching(self):
        """Test tree filter with matching tree name"""
        test_data = {"tree_name": "mainline"}
        filter_obj = TreeFilter("^(mainline)$")

        # Should match when tree matches
        assert filter_obj.matches(test_data) is True

    def test_tree_filter_not_matching(self):
        """Test tree filter with non-matching tree name"""
        test_data = {"tree_name": "linux-next"}
        filter_obj = TreeFilter("^(mainline)$")

        # Should not match when tree doesn't match
        assert filter_obj.matches(test_data) is False

    def test_tree_filter_missing_tree_in_data(self):
        """Test tree filter when tree_name is missing in test data"""
        test_data = {}
        filter_obj = TreeFilter("^(mainline)$")

        # Should not match when tree_name is missing
        assert filter_obj.matches(test_data) is False

    def test_tree_filter_no_pattern(self):
        """Test tree filter when no pattern is specified"""
        test_data = {"tree_name": "mainline"}
        filter_obj = TreeFilter(None)

        # Should match when no pattern is specified
        assert filter_obj.matches(test_data) is True

    def test_tree_filter_wildcard(self):
        """Test tree filter with wildcard pattern"""
        test_data = {"tree_name": "linux-next"}
        filter_obj = TreeFilter("^(linux.*)$")

        # Should match when pattern matches with wildcard
        assert filter_obj.matches(test_data) is True

    def test_tree_filter_multiple_options(self):
        """Test tree filter with multiple tree options"""
        test_data = {"tree_name": "stable"}
        filter_obj = TreeFilter("^(mainline|linux-next|stable)$")

        # Should match when tree matches one of the options
        assert filter_obj.matches(test_data) is True

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

    def test_date_filter_with_start_date(self):
        """Test filtering with start date only"""
        filter_obj = DateRangeFilter("2025-01-15", None)

        # Item with date before start date - should not match
        item_old = {"start_time": "2025-01-01T10:00:00Z"}
        assert filter_obj.matches(item_old) is False

        # Item with date after start date - should match
        item_new = {"start_time": "2025-01-20T10:00:00Z"}
        assert filter_obj.matches(item_new) is True

    def test_date_filter_with_end_date(self):
        """Test filtering with end date only"""
        filter_obj = DateRangeFilter(None, "2025-01-15")

        # Item with date before end date - should match
        item_old = {"start_time": "2025-01-01T10:00:00Z"}
        assert filter_obj.matches(item_old) is True

        # Item with date after end date - should not match
        item_new = {"start_time": "2025-01-20T10:00:00Z"}
        assert filter_obj.matches(item_new) is False

    def test_date_filter_with_date_range(self):
        """Test filtering with both start and end dates"""
        filter_obj = DateRangeFilter("2025-01-10", "2025-01-20")

        # Item within range - should match
        item_in_range = {"start_time": "2025-01-15T10:00:00Z"}
        assert filter_obj.matches(item_in_range) is True

        # Item before range - should not match
        item_before = {"start_time": "2025-01-05T10:00:00Z"}
        assert filter_obj.matches(item_before) is False

        # Item after range - should not match
        item_after = {"start_time": "2025-01-25T10:00:00Z"}
        assert filter_obj.matches(item_after) is False

    def test_date_filter_with_different_timestamp_fields(self):
        """Test that different timestamp fields are handled correctly"""
        filter_obj = DateRangeFilter("2025-01-10", "2025-01-20")

        # Test with 'created' field
        item_created = {"created": "2025-01-15T10:00:00Z"}
        assert filter_obj.matches(item_created) is True

        # Test with 'updated' field
        item_updated = {"updated": "2025-01-15T10:00:00Z"}
        assert filter_obj.matches(item_updated) is True

    def test_date_filter_with_no_timestamp(self):
        """Test that items without timestamp fields are included"""
        filter_obj = DateRangeFilter("2025-01-10", "2025-01-20")
        item = {"other_field": "value"}
        assert filter_obj.matches(item) is True

    def test_date_filter_with_no_filters(self):
        """Test that no filtering occurs when no date filters are provided"""
        filter_obj = DateRangeFilter(None, None)
        item = {"start_time": "2025-01-15T10:00:00Z"}
        assert filter_obj.matches(item) is True

        filter_obj2 = DateRangeFilter("", "")
        assert filter_obj2.matches(item) is True


class TestCompilerFilter:
    """Test compiler filter functionality"""

    def test_compiler_filter_matching(self):
        """Test that items with matching compiler match"""
        filter_obj = CompilerFilter("gcc")
        item = {"compiler": "gcc", "other_field": "value"}
        assert filter_obj.matches(item) is True

    def test_compiler_filter_non_matching(self):
        """Test that items with non-matching compiler don't match"""
        filter_obj = CompilerFilter("clang")
        item = {"compiler": "gcc", "other_field": "value"}
        assert filter_obj.matches(item) is False

    def test_compiler_filter_case_insensitive(self):
        """Test that compiler filter is case insensitive"""
        filter_obj = CompilerFilter("gcc")
        item = {"compiler": "GCC"}
        assert filter_obj.matches(item) is True

        filter_obj2 = CompilerFilter("GCC")
        item2 = {"compiler": "gcc"}
        assert filter_obj2.matches(item2) is True

    def test_compiler_filter_no_filter(self):
        """Test that no filtering occurs when compiler filter is None"""
        filter_obj = CompilerFilter(None)
        item = {"compiler": "gcc"}
        assert filter_obj.matches(item) is True

        filter_obj2 = CompilerFilter("")
        assert filter_obj2.matches(item) is True

    def test_compiler_filter_missing_field(self):
        """Test that items without compiler field don't match when filter is active"""
        filter_obj = CompilerFilter("gcc")
        item = {"other_field": "value"}
        assert filter_obj.matches(item) is False


class TestConfigFilter:
    """Test config filter functionality"""

    def test_config_filter_matching(self):
        """Test that items with matching config match"""
        filter_obj = ConfigFilter("defconfig")
        item = {"config_name": "defconfig", "other_field": "value"}
        assert filter_obj.matches(item) is True

    def test_config_filter_non_matching(self):
        """Test that items with non-matching config don't match"""
        filter_obj = ConfigFilter("allmodconfig")
        item = {"config_name": "defconfig", "other_field": "value"}
        assert filter_obj.matches(item) is False

    def test_config_filter_wildcard(self):
        """Test that config filter supports wildcards"""
        filter_obj = ConfigFilter("*modconfig")
        item = {"config_name": "allmodconfig"}
        assert filter_obj.matches(item) is True

        filter_obj2 = ConfigFilter("def*")
        item2 = {"config_name": "defconfig"}
        assert filter_obj2.matches(item2) is True

        item3 = {"config_name": "tinyconfig"}
        assert filter_obj2.matches(item3) is False

    def test_config_filter_both_fields(self):
        """Test that filter checks both config_name and config fields"""
        filter_obj = ConfigFilter("defconfig")

        # Test with config_name field
        item = {"config_name": "defconfig"}
        assert filter_obj.matches(item) is True

        # Test with config field
        item = {"config": "defconfig"}
        assert filter_obj.matches(item) is True

        # Test with both fields (config_name takes precedence)
        item = {"config_name": "defconfig", "config": "allmodconfig"}
        assert filter_obj.matches(item) is True

    def test_config_filter_no_filter(self):
        """Test that no filtering occurs when config filter is None"""
        filter_obj = ConfigFilter(None)
        item = {"config_name": "defconfig"}
        assert filter_obj.matches(item) is True

        filter_obj2 = ConfigFilter("")
        assert filter_obj2.matches(item) is True

    def test_config_filter_missing_field(self):
        """Test that items without config fields don't match when filter is active"""
        filter_obj = ConfigFilter("defconfig")
        item = {"other_field": "value"}
        assert filter_obj.matches(item) is False

    def test_config_filter_case_sensitive(self):
        """Test that config filter is case sensitive"""
        filter_obj = ConfigFilter("defconfig")
        item = {"config_name": "DEFCONFIG"}
        assert filter_obj.matches(item) is False

        filter_obj2 = ConfigFilter("DEFCONFIG")
        item2 = {"config_name": "defconfig"}
        assert filter_obj2.matches(item2) is False


class TestHardwareFilter:
    """Test hardware filter functionality"""

    def test_hardware_filter_matching_platform(self):
        """Test that items with matching platform match"""
        filter_obj = HardwareFilter("rk3399-rock-pi-4b")
        test = {"environment_misc": {"platform": "rk3399-rock-pi-4b"}}
        assert filter_obj.matches(test) is True

    def test_hardware_filter_non_matching_platform(self):
        """Test that items with non-matching platform don't match"""
        filter_obj = HardwareFilter("bcm2711-rpi-4-b")
        test = {"environment_misc": {"platform": "rk3399-rock-pi-4b"}}
        assert filter_obj.matches(test) is False

    def test_hardware_filter_wildcard_platform(self):
        """Test that hardware filter supports wildcards for platform"""
        test = {"environment_misc": {"platform": "rk3399-rock-pi-4b"}}

        filter_obj1 = HardwareFilter("rk3399*")
        assert filter_obj1.matches(test) is True

        filter_obj2 = HardwareFilter("*rock-pi*")
        assert filter_obj2.matches(test) is True

        filter_obj3 = HardwareFilter("bcm*")
        assert filter_obj3.matches(test) is False

    def test_hardware_filter_matching_compatible(self):
        """Test that items with matching compatible match"""
        filter_obj = HardwareFilter("rockchip,rk3399")
        test = {
            "environment_misc": {"platform": "generic-platform"},
            "environment_compatible": ["rockchip,rk3399", "rockchip,rk3399-rock-pi-4b"],
        }
        assert filter_obj.matches(test) is True

    def test_hardware_filter_wildcard_compatible(self):
        """Test that hardware filter supports wildcards for compatibles"""
        test = {
            "environment_misc": {"platform": "generic-platform"},
            "environment_compatible": ["rockchip,rk3399", "rockchip,rk3399-rock-pi-4b"],
        }

        filter_obj1 = HardwareFilter("rockchip,*")
        assert filter_obj1.matches(test) is True

        filter_obj2 = HardwareFilter("*rock-pi*")
        assert filter_obj2.matches(test) is True

    def test_hardware_filter_no_filter(self):
        """Test that no filtering occurs when hardware filter is None"""
        filter_obj1 = HardwareFilter(None)
        test = {"environment_misc": {"platform": "rk3399-rock-pi-4b"}}
        assert filter_obj1.matches(test) is True

        filter_obj2 = HardwareFilter("")
        assert filter_obj2.matches(test) is True

    def test_hardware_filter_missing_fields(self):
        """Test that items without hardware fields don't match when filter is active"""
        filter_obj = HardwareFilter("rk3399*")
        test = {"other_field": "value"}
        assert filter_obj.matches(test) is False

    def test_hardware_filter_empty_compatible(self):
        """Test handling of empty compatible list"""
        filter_obj = HardwareFilter("rockchip,*")
        test = {
            "environment_misc": {"platform": "generic-platform"},
            "environment_compatible": [],
        }
        assert filter_obj.matches(test) is False

    def test_hardware_filter_platform_or_compatible(self):
        """Test that filter matches either platform OR compatible"""
        test = {
            "environment_misc": {"platform": "rk3399-rock-pi-4b"},
            "environment_compatible": ["ti,am625", "ti,am62"],
        }
        # Matches platform
        filter_obj1 = HardwareFilter("rk3399*")
        assert filter_obj1.matches(test) is True

        # Matches compatible
        filter_obj2 = HardwareFilter("ti,*")
        assert filter_obj2.matches(test) is True

        # Matches neither
        filter_obj3 = HardwareFilter("bcm*")
        assert filter_obj3.matches(test) is False


class TestTestPathFilter:
    """Test test-path filter functionality"""

    def test_test_path_filter_matching(self):
        """Test that items with matching test path match"""
        filter_obj = PathFilter("baseline.login")
        test = {"path": "baseline.login"}
        assert filter_obj.matches(test) is True

    def test_test_path_filter_non_matching(self):
        """Test that items with non-matching test path don't match"""
        filter_obj = PathFilter("baseline.dmesg")
        test = {"path": "baseline.login"}
        assert filter_obj.matches(test) is False

    def test_test_path_filter_wildcard(self):
        """Test that test path filter supports wildcards"""
        test = {"path": "baseline.login"}

        filter_obj1 = PathFilter("baseline.*")
        assert filter_obj1.matches(test) is True

        filter_obj2 = PathFilter("*login")
        assert filter_obj2.matches(test) is True

        filter_obj3 = PathFilter("base*")
        assert filter_obj3.matches(test) is True

        filter_obj4 = PathFilter("kunit.*")
        assert filter_obj4.matches(test) is False

    def test_test_path_filter_no_filter(self):
        """Test that no filtering occurs when test path filter is None"""
        test = {"path": "baseline.login"}

        filter_obj1 = PathFilter(None)
        assert filter_obj1.matches(test) is True

        filter_obj2 = PathFilter("")
        assert filter_obj2.matches(test) is True

    def test_test_path_filter_missing_field(self):
        """Test that items without path field don't match when filter is active"""
        filter_obj = PathFilter("baseline.*")
        test = {"other_field": "value"}
        assert filter_obj.matches(test) is False

    def test_test_path_filter_complex_paths(self):
        """Test filtering with complex test paths"""
        test = {"path": "kselftest.alsa.pcm-test"}

        filter_obj1 = PathFilter("kselftest.alsa.pcm-test")
        assert filter_obj1.matches(test) is True

        filter_obj2 = PathFilter("kselftest.alsa.*")
        assert filter_obj2.matches(test) is True

        filter_obj3 = PathFilter("kselftest.*")
        assert filter_obj3.matches(test) is True

        filter_obj4 = PathFilter("*pcm-test")
        assert filter_obj4.matches(test) is True

        filter_obj5 = PathFilter("baseline.*")
        assert filter_obj5.matches(test) is False


class TestGitBranchFilter:
    """Test git-branch filter functionality"""

    def test_git_branch_filter_matching(self):
        """Test that items with matching git branch match"""
        filter_obj = GitBranchFilter("master")
        item = {"git_repository_branch": "master"}
        assert filter_obj.matches(item) is True

    def test_git_branch_filter_non_matching(self):
        """Test that items with non-matching git branch don't match"""
        filter_obj = GitBranchFilter("develop")
        item = {"git_repository_branch": "master"}
        assert filter_obj.matches(item) is False

    def test_git_branch_filter_wildcard(self):
        """Test that git branch filter supports wildcards"""
        item = {"git_repository_branch": "linux-6.1.y"}

        filter_obj1 = GitBranchFilter("linux-*")
        assert filter_obj1.matches(item) is True

        filter_obj2 = GitBranchFilter("*-6.1.y")
        assert filter_obj2.matches(item) is True

        filter_obj3 = GitBranchFilter("linux-6.*.y")
        assert filter_obj3.matches(item) is True

        filter_obj4 = GitBranchFilter("linux-5.*")
        assert filter_obj4.matches(item) is False

    def test_git_branch_filter_no_filter(self):
        """Test that no filtering occurs when git branch filter is None"""
        item = {"git_repository_branch": "master"}

        filter_obj1 = GitBranchFilter(None)
        assert filter_obj1.matches(item) is True

        filter_obj2 = GitBranchFilter("")
        assert filter_obj2.matches(item) is True

    def test_git_branch_filter_missing_field(self):
        """Test that items without git_repository_branch field don't match when filter is active"""
        filter_obj = GitBranchFilter("master")
        item = {"other_field": "value"}
        assert filter_obj.matches(item) is False


class TestCompatibleFilter:
    """Test compatible filter functionality"""

    def test_compatible_filter_matching(self):
        """Test that items with matching compatible string match"""
        filter_obj = CompatibleFilter("rk3399")
        test = {
            "environment_compatible": ["rockchip,rk3399", "rockchip,rk3399-rock-pi-4b"]
        }
        assert filter_obj.matches(test) is True

    def test_compatible_filter_non_matching(self):
        """Test that items with non-matching compatible string don't match"""
        filter_obj = CompatibleFilter("bcm2711")
        test = {
            "environment_compatible": ["rockchip,rk3399", "rockchip,rk3399-rock-pi-4b"]
        }
        assert filter_obj.matches(test) is False

    def test_compatible_filter_case_insensitive(self):
        """Test that compatible filter is case insensitive"""
        test = {
            "environment_compatible": ["Rockchip,RK3399", "ROCKCHIP,RK3399-ROCK-PI-4B"]
        }

        filter_obj1 = CompatibleFilter("rk3399")
        assert filter_obj1.matches(test) is True

        filter_obj2 = CompatibleFilter("RK3399")
        assert filter_obj2.matches(test) is True

    def test_compatible_filter_partial_match(self):
        """Test that compatible filter matches partial strings"""
        test = {"environment_compatible": ["ti,am625-sk", "ti,am62"]}

        filter_obj1 = CompatibleFilter("am625")
        assert filter_obj1.matches(test) is True

        filter_obj2 = CompatibleFilter("ti,am")
        assert filter_obj2.matches(test) is True

        filter_obj3 = CompatibleFilter("625")
        assert filter_obj3.matches(test) is True

    def test_compatible_filter_no_filter(self):
        """Test that no filtering occurs when compatible filter is None"""
        test = {"environment_compatible": ["rockchip,rk3399"]}

        filter_obj1 = CompatibleFilter(None)
        assert filter_obj1.matches(test) is True

        filter_obj2 = CompatibleFilter("")
        assert filter_obj2.matches(test) is True

    def test_compatible_filter_missing_field(self):
        """Test that items without environment_compatible field don't match when filter is active"""
        filter_obj = CompatibleFilter("rockchip")
        test = {"other_field": "value"}
        assert filter_obj.matches(test) is False

    def test_compatible_filter_empty_list(self):
        """Test that items with empty compatible list don't match"""
        filter_obj = CompatibleFilter("rockchip")
        test = {"environment_compatible": []}
        assert filter_obj.matches(test) is False


class TestDurationFilter:
    """Test duration filter functionality"""

    def test_duration_filter_with_duration_field(self):
        """Test filtering using the duration field"""
        # Test with min duration
        test = {"duration": 30.5}

        filter_obj1 = DurationFilter(20.0, None)
        assert filter_obj1.matches(test) is True

        filter_obj2 = DurationFilter(40.0, None)
        assert filter_obj2.matches(test) is False

        # Test with max duration
        filter_obj3 = DurationFilter(None, 40.0)
        assert filter_obj3.matches(test) is True

        filter_obj4 = DurationFilter(None, 20.0)
        assert filter_obj4.matches(test) is False

        # Test with both min and max
        filter_obj5 = DurationFilter(20.0, 40.0)
        assert filter_obj5.matches(test) is True

        filter_obj6 = DurationFilter(35.0, 40.0)
        assert filter_obj6.matches(test) is False

        filter_obj7 = DurationFilter(20.0, 25.0)
        assert filter_obj7.matches(test) is False

    def test_duration_filter_calculated_from_timestamps(self):
        """Test filtering with duration calculated from start_time and end_time"""
        test = {
            "start_time": "2025-01-06T10:00:00Z",
            "end_time": "2025-01-06T10:00:30Z",  # 30 seconds duration
        }

        filter_obj1 = DurationFilter(20.0, None)
        assert filter_obj1.matches(test) is True

        filter_obj2 = DurationFilter(40.0, None)
        assert filter_obj2.matches(test) is False

    def test_duration_filter_no_filter(self):
        """Test that no filtering occurs when duration filters are None"""
        filter_obj = DurationFilter(None, None)
        test = {"duration": 30.5}
        assert filter_obj.matches(test) is True

    def test_duration_filter_missing_duration_info(self):
        """Test that items without duration information match"""
        filter_obj = DurationFilter(10.0, 60.0)
        test = {"other_field": "value"}
        assert filter_obj.matches(test) is True

    def test_duration_filter_invalid_timestamps(self):
        """Test that items with invalid timestamps match"""
        filter_obj = DurationFilter(10.0, 60.0)
        test = {
            "start_time": "invalid-date",
            "end_time": "also-invalid",
        }
        assert filter_obj.matches(test) is True

    def test_duration_filter_priority(self):
        """Test that duration field takes priority over calculated duration"""
        test = {
            "duration": 30.0,  # Use this
            "start_time": "2025-01-06T10:00:00Z",
            "end_time": "2025-01-06T10:01:00Z",  # Would be 60 seconds
        }

        filter_obj1 = DurationFilter(20.0, 40.0)
        assert filter_obj1.matches(test) is True  # 30 is in range

        filter_obj2 = DurationFilter(40.0, 50.0)
        assert filter_obj2.matches(test) is False  # 30 is below range
