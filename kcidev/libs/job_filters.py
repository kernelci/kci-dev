"""Filter classes specific to Maestro job results."""

import re

from kcidev.libs.filters import BaseFilter


class TreeFilter(BaseFilter):
    """Filter by tree name using regex pattern."""

    def __init__(self, pattern):
        self.pattern = re.compile(pattern) if pattern else None

    def matches(self, item):
        if not self.pattern:
            return True

        tree_name = item.get("tree_name", "")
        return bool(self.pattern.match(tree_name))


class HardwareRegexFilter(BaseFilter):
    """Filter by hardware using regex pattern (for YAML file filters)."""

    def __init__(self, pattern):
        self.pattern = re.compile(pattern) if pattern else None

    def matches(self, item):
        if not self.pattern:
            return True

        # Check platform name
        if "environment_misc" in item and "platform" in item["environment_misc"]:
            if self.pattern.match(item["environment_misc"]["platform"]):
                return True

        # Check compatibles
        if "environment_compatible" in item and item["environment_compatible"]:
            for compatible in item["environment_compatible"]:
                if self.pattern.match(compatible):
                    return True

        return False


class TestRegexFilter(BaseFilter):
    """Filter by test path using regex pattern (for YAML file filters)."""

    def __init__(self, pattern):
        self.pattern = re.compile(pattern) if pattern else None

    def matches(self, item):
        if not self.pattern:
            return True

        test_path = item.get("path", "")
        return bool(self.pattern.match(test_path))
