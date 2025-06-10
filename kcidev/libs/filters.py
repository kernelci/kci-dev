"""Unified filter functionality for kci-dev commands."""

import fnmatch
from datetime import datetime


class BaseFilter:
    """Base class for all filters."""

    def __init__(self, value):
        self.value = value

    def matches(self, item):
        """Check if item matches the filter criteria."""
        raise NotImplementedError


class StatusFilter(BaseFilter):
    """Filter by status (pass, fail, inconclusive)."""

    def matches(self, item):
        if self.value == "all":
            return True

        status = item.get("status", "").upper()

        if self.value == "pass":
            return status == "PASS"
        elif self.value == "fail":
            return status == "FAIL"
        elif self.value == "inconclusive":
            return status in ["ERROR", "SKIP", "MISS", "DONE", "NULL"]

        return False


class DateRangeFilter(BaseFilter):
    """Filter by date range."""

    def __init__(self, start_date=None, end_date=None):
        self.start_date = start_date
        self.end_date = end_date

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
                    return False

        except Exception:
            # If we can't parse the date, include the item
            return True

        return True


class CompilerFilter(BaseFilter):
    """Filter by compiler."""

    def matches(self, item):
        if not self.value:
            return True

        if "compiler" not in item:
            return False

        return item["compiler"].lower() == self.value.lower()


class ConfigFilter(BaseFilter):
    """Filter by config name."""

    def matches(self, item):
        if not self.value:
            return True

        # Check both config_name and config fields
        config_value = item.get("config_name") or item.get("config")

        if not config_value:
            return False

        # Support wildcards
        return fnmatch.fnmatch(config_value, self.value)


class GitBranchFilter(BaseFilter):
    """Filter by git branch."""

    def matches(self, item):
        if not self.value:
            return True

        if "git_repository_branch" not in item:
            return False

        # Support wildcards
        return fnmatch.fnmatch(item["git_repository_branch"], self.value)


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

        return False


class PathFilter(BaseFilter):
    """Filter by test path."""

    def matches(self, item):
        if not self.value:
            return True

        if "path" not in item:
            return False

        # Support wildcards
        return fnmatch.fnmatch(item["path"], self.value)


class CompatibleFilter(BaseFilter):
    """Filter by device tree compatible string."""

    def matches(self, item):
        if not self.value:
            return True

        if "environment_compatible" not in item or not item["environment_compatible"]:
            return False

        # Check if filter string is contained in any compatible string
        for compatible in item["environment_compatible"]:
            if self.value.lower() in compatible.lower():
                return True

        return False


class DurationFilter(BaseFilter):
    """Filter by test duration."""

    def __init__(self, min_duration=None, max_duration=None):
        self.min_duration = min_duration
        self.max_duration = max_duration

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
            return False
        if self.max_duration and duration > self.max_duration:
            return False

        return True


class FilterSet:
    """Collection of filters to apply to items."""

    def __init__(self, filters=None):
        self.filters = filters or []

    def add_filter(self, filter_obj):
        """Add a filter to the set."""
        if filter_obj:
            self.filters.append(filter_obj)

    def matches(self, item):
        """Check if item matches all filters."""
        for filter_obj in self.filters:
            if not filter_obj.matches(item):
                return False
        return True

    def filter_items(self, items):
        """Filter a list of items."""
        return [item for item in items if self.matches(item)]
