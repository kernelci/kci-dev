"""Click option decorators for filters."""

import click


def add_filter_options(func):
    """Add standard filter options to a command."""
    decorators = [
        click.option(
            "--status",
            default="all",
            type=click.Choice(["all", "pass", "fail", "inconclusive"]),
            help="Filter by status",
        ),
        click.option(
            "--start-date",
            help="Filter results after this date (ISO format: YYYY-MM-DD or full timestamp)",
        ),
        click.option("--end-date", help="Filter results before this date"),
        click.option("--compiler", help="Filter by compiler (e.g., gcc, clang)"),
        click.option("--config", help="Filter by config name (supports wildcards)"),
        click.option("--git-branch", help="Filter by git branch (supports wildcards)"),
    ]

    for decorator in reversed(decorators):
        func = decorator(func)
    return func


def add_test_filter_options(func):
    """Add test-specific filter options to a command."""
    decorators = [
        click.option(
            "--hardware",
            help="Filter by hardware platform name or compatible (supports wildcards)",
        ),
        click.option("--test-path", help="Filter by test path (supports wildcards)"),
        click.option(
            "--compatible",
            help="Filter by device tree compatible string (substring match)",
        ),
        click.option(
            "--min-duration", type=float, help="Filter tests with duration >= N seconds"
        ),
        click.option(
            "--max-duration", type=float, help="Filter tests with duration <= N seconds"
        ),
    ]

    for decorator in reversed(decorators):
        func = decorator(func)
    return func


def add_build_filter_options(func):
    """Add build-specific filter options to a command."""
    # Currently no build-specific filters beyond the common ones
    return func
