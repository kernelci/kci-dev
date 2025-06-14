"""Filter classes specific to Maestro job results."""

import logging
import re

from kcidev.libs.filters import BaseFilter


class TreeFilter(BaseFilter):
    """Filter by tree name using regex pattern."""

    def __init__(self, pattern):
        self.pattern = re.compile(pattern) if pattern else None
        logging.debug(f"Created TreeFilter with regex pattern: {pattern}")

    def matches(self, item):
        if not self.pattern:
            return True

        tree_name = item.get("tree_name", "")
        result = bool(self.pattern.match(tree_name))
        if not result:
            logging.debug(
                f"TreeFilter: {tree_name} does not match pattern {self.pattern.pattern}"
            )
        return result


class HardwareRegexFilter(BaseFilter):
    """Filter by hardware using regex pattern (for YAML file filters)."""

    def __init__(self, pattern):
        self.pattern = re.compile(pattern) if pattern else None
        logging.debug(f"Created HardwareRegexFilter with regex pattern: {pattern}")

    def matches(self, item):
        if not self.pattern:
            return True

        # Check platform name
        if "environment_misc" in item and "platform" in item["environment_misc"]:
            platform = item["environment_misc"]["platform"]
            if self.pattern.match(platform):
                logging.debug(f"HardwareRegexFilter: Matched platform {platform}")
                return True

        # Check compatibles
        if "environment_compatible" in item and item["environment_compatible"]:
            for compatible in item["environment_compatible"]:
                if self.pattern.match(compatible):
                    logging.debug(
                        f"HardwareRegexFilter: Matched compatible {compatible}"
                    )
                    return True

        logging.debug(
            f"HardwareRegexFilter: No match for pattern {self.pattern.pattern}"
        )
        return False


class TestRegexFilter(BaseFilter):
    """Filter by test path using regex pattern (for YAML file filters)."""

    def __init__(self, pattern):
        self.pattern = re.compile(pattern) if pattern else None
        logging.debug(f"Created TestRegexFilter with regex pattern: {pattern}")

    def matches(self, item):
        if not self.pattern:
            return True

        test_path = item.get("path", "")
        result = bool(self.pattern.match(test_path))
        if not result:
            logging.debug(
                f"TestRegexFilter: {test_path} does not match pattern {self.pattern.pattern}"
            )
        return result
