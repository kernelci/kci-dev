"""Unified filter functionality for kci-dev commands."""

import fnmatch
import logging
from datetime import datetime


class BaseFilter:
    """Base class for all filters."""

    def __init__(self, value):
        self.value = value
        logging.debug(f"Created {self.__class__.__name__} with value: {value}")

    def matches(self, item):
        """Check if item matches the filter criteria."""
        raise NotImplementedError


class StatusFilter(BaseFilter):
    """Filter by status (pass, fail, inconclusive)."""

    def matches(self, item):
        if self.value == "all":
            return True

        status = item.get("status", "").upper()
        result = False

        if self.value == "pass":
            result = status == "PASS"
        elif self.value == "fail":
            result = status == "FAIL"
        elif self.value == "inconclusive":
            result = status in ["ERROR", "SKIP", "MISS", "DONE", "NULL"]

        if not result:
            logging.debug(f"StatusFilter: {status} does not match {self.value}")
        return result


class DateRangeFilter(BaseFilter):
    """Filter by date range."""

    def __init__(self, start_date=None, end_date=None):
        self.start_date = start_date
        self.end_date = end_date
        logging.debug(f"Created DateRangeFilter: {start_date} to {end_date}")

    def matches(self, item):
        if not self.start_date and not self.end_date:
            return True

        # Get the timestamp field from the item
        timestamp_field = None
        for field in ["start_time", "created", "updated"]:
            if field in item:
                timestamp_field = item[field]
                break

        if not timestamp_field:
            return True

        # Parse the timestamp
        try:
            item_date = datetime.fromisoformat(timestamp_field.replace("Z", "+00:00"))

            if self.start_date:
                # If start_date is just a date (no time), parse it at start of day
                if len(self.start_date) == 10:  # YYYY-MM-DD format
                    start_dt = datetime.fromisoformat(
                        self.start_date + "T00:00:00+00:00"
                    )
                else:
                    start_dt = datetime.fromisoformat(
                        self.start_date.replace("Z", "+00:00")
                    )
                if item_date < start_dt:
                    logging.debug(
                        f"DateRangeFilter: {timestamp_field} before start date {self.start_date}"
                    )
                    return False

            if self.end_date:
                # If end_date is just a date (no time), parse it at end of day
                if len(self.end_date) == 10:  # YYYY-MM-DD format
                    end_dt = datetime.fromisoformat(self.end_date + "T23:59:59+00:00")
                else:
                    end_dt = datetime.fromisoformat(
                        self.end_date.replace("Z", "+00:00")
                    )
                if item_date > end_dt:
                    logging.debug(
                        f"DateRangeFilter: {timestamp_field} after end date {self.end_date}"
                    )
                    return False

        except Exception as e:
            # If we can't parse the date, include the item
            logging.debug(
                f"DateRangeFilter: Failed to parse date {timestamp_field}: {e}"
            )
            return True

        return True


class CompilerFilter(BaseFilter):
    """Filter by compiler."""

    def matches(self, item):
        if not self.value:
            return True

        if "compiler" not in item:
            logging.debug("CompilerFilter: No compiler field in item")
            return False

        result = item["compiler"].lower() == self.value.lower()
        if not result:
            logging.debug(
                f"CompilerFilter: {item['compiler']} does not match {self.value}"
            )
        return result


class ConfigFilter(BaseFilter):
    """Filter by config name."""

    def matches(self, item):
        if not self.value:
            return True

        # Check both config_name and config fields
        config_value = item.get("config_name") or item.get("config")

        if not config_value:
            logging.debug("ConfigFilter: No config field in item")
            return False

        # Support wildcards
        result = fnmatch.fnmatch(config_value, self.value)
        if not result:
            logging.debug(
                f"ConfigFilter: {config_value} does not match pattern {self.value}"
            )
        return result


class GitBranchFilter(BaseFilter):
    """Filter by git branch."""

    def matches(self, item):
        if not self.value:
            return True

        if "git_repository_branch" not in item:
            logging.debug("GitBranchFilter: No git_repository_branch field in item")
            return False

        # Support wildcards
        result = fnmatch.fnmatch(item["git_repository_branch"], self.value)
        if not result:
            logging.debug(
                f"GitBranchFilter: {item['git_repository_branch']} does not match pattern {self.value}"
            )
        return result


class HardwareFilter(BaseFilter):
    """Filter by hardware platform name or compatible."""

    def matches(self, item):
        if not self.value:
            return True

        # Check platform name
        if "environment_misc" in item and "platform" in item["environment_misc"]:
            platform = item["environment_misc"]["platform"]
            if fnmatch.fnmatch(platform, self.value):
                return True

        # Check compatibles
        if "environment_compatible" in item and item["environment_compatible"]:
            for compatible in item["environment_compatible"]:
                if fnmatch.fnmatch(compatible, self.value):
                    return True

        logging.debug(f"HardwareFilter: No match found for pattern {self.value}")
        return False


class PathFilter(BaseFilter):
    """Filter by test path."""

    def matches(self, item):
        if not self.value:
            return True

        if "path" not in item:
            logging.debug("PathFilter: No path field in item")
            return False

        # Support wildcards
        result = fnmatch.fnmatch(item["path"], self.value)
        if not result:
            logging.debug(
                f"PathFilter: {item['path']} does not match pattern {self.value}"
            )
        return result


class CompatibleFilter(BaseFilter):
    """Filter by device tree compatible string."""

    def matches(self, item):
        if not self.value:
            return True

        if "environment_compatible" not in item or not item["environment_compatible"]:
            logging.debug("CompatibleFilter: No environment_compatible field in item")
            return False

        # Check if filter string is contained in any compatible string
        for compatible in item["environment_compatible"]:
            if self.value.lower() in compatible.lower():
                return True

        logging.debug(f"CompatibleFilter: {self.value} not found in compatibles")
        return False


class DurationFilter(BaseFilter):
    """Filter by test duration."""

    def __init__(self, min_duration=None, max_duration=None):
        self.min_duration = min_duration
        self.max_duration = max_duration
        logging.debug(f"Created DurationFilter: {min_duration}s to {max_duration}s")

    def matches(self, item):
        if not self.min_duration and not self.max_duration:
            return True

        # Calculate duration from start_time and end_time, or use duration field
        duration = None

        if "duration" in item and item["duration"] is not None:
            duration = item["duration"]
        elif "start_time" in item and "end_time" in item:
            try:
                start = datetime.fromisoformat(
                    item["start_time"].replace("Z", "+00:00")
                )
                end = datetime.fromisoformat(item["end_time"].replace("Z", "+00:00"))
                duration = (end - start).total_seconds()
            except Exception:
                # If we can't parse the dates, include the item
                return True
        else:
            # No duration information available
            return True

        # Apply min/max filters
        if self.min_duration and duration < self.min_duration:
            logging.debug(
                f"DurationFilter: {duration}s below minimum {self.min_duration}s"
            )
            return False
        if self.max_duration and duration > self.max_duration:
            logging.debug(
                f"DurationFilter: {duration}s above maximum {self.max_duration}s"
            )
            return False

        return True


class FilterSet:
    """Collection of filters to apply to items."""

    def __init__(self, filters=None):
        self.filters = filters or []
        logging.debug(f"Created FilterSet with {len(self.filters)} initial filters")

    def add_filter(self, filter_obj):
        """Add a filter to the set."""
        if filter_obj:
            self.filters.append(filter_obj)
            logging.debug(f"Added {filter_obj.__class__.__name__} to filter set")

    def matches(self, item):
        """Check if item matches all filters."""
        for filter_obj in self.filters:
            if not filter_obj.matches(item):
                return False
        return True

    def filter_items(self, items):
        """Filter a list of items."""
        original_count = len(items)
        filtered = [item for item in items if self.matches(item)]
        logging.info(
            f"FilterSet: {len(filtered)} items passed from {original_count} total"
        )
        return filtered
