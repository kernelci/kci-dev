import sys

import click

from kcidev.libs.dashboard import (
    dashboard_fetch_issue,
    dashboard_fetch_issue_builds,
    dashboard_fetch_issue_list,
    dashboard_fetch_issue_tests,
)
from kcidev.subcommands.results.options import results_display_options
from kcidev.subcommands.results.parser import cmd_issue_list, print_data


@click.group(
    help="""Get KCIDB issues from the dashboard

\b
Subcommands:
    results issues list   - Get all KCIDB issues
    results issues get    - Get an issue matching ID
    results issues builds - Get builds associated with an issue
    results issues tests  - Get tests associated with an issue
    results issues detect - Detect KCIDB issues for builds and boots

\b
Examples:
    # Get issues
    kci-dev results issues list --days <number-of-days> --origin <origin>
    # Get an issue information matching issue ID
    kci-dev results issues get --id <id>
    # Get builds associated with an issue ID
    kci-dev results issues builds --id <id> --origin <origin>
    # Get tests associated with an issue ID
    kci-dev results issues tests --id <id> --origin <origin>
    # Detect build issues
    kci-dev issues detect --builds --id <build-id>
    kci-dev issues detect --builds --all-checkouts --days <number-of-days> --origin <origin>
    # Detect boot issues
    kci-dev issues detect --boots --id <boot-id>
    kci-dev issues detect --boots --all-checkouts --days <number-of-days> --origin <origin>
""",
    invoke_without_command=True,
)
@click.pass_context
def issues(ctx):
    """Commands related to KCIDB issues"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        sys.exit(0)


@issues.command(
    name="list",
    help="""Fetch KCIDB issues from the dashboard

\b
Examples:
  kci-dev results issues list --origin <origin> --days <number-of-days>
""",
)
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@click.option(
    "--days",
    help="Provide a period of time in days to get results for",
    type=int,
    default="5",
)
@results_display_options
def issues_list(origin, days, use_json):
    """Issue list command handler"""
    data = dashboard_fetch_issue_list(origin, days, use_json)
    cmd_issue_list(data, use_json)


@issues.command(
    name="get",
    help="""Fetch KCIDB issue matching provided ID

\b
Examples:
  kci-dev results issues get --id <id>
""",
)
@click.option(
    "--id",
    "issue_id",
    required=True,
    help="Issue ID to get information for",
)
@results_display_options
def get(issue_id, use_json):
    """Get issue command handler"""
    data = dashboard_fetch_issue(issue_id, use_json)
    print_data(data, use_json)


@issues.command(
    name="builds",
    help="""Fetch builds associated with KCIDB issue

\b
Examples:
  kci-dev results issues builds --id <id> --origin <origin>
""",
)
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@click.option(
    "--id",
    "issue_id",
    required=True,
    help="Issue ID to get information for",
)
@results_display_options
def builds(origin, issue_id, use_json):
    """Builds command handler"""
    data = dashboard_fetch_issue_builds(origin, issue_id, use_json)
    print_data(data, use_json)


@issues.command(
    name="tests",
    help="""Fetch tests associated with KCIDB issue

\b
Examples:
  kci-dev results issues tests --id <id> --origin <origin>
""",
)
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@click.option(
    "--id",
    "issue_id",
    required=True,
    help="Issue ID to get information for",
)
@results_display_options
def tests(origin, issue_id, use_json):
    """Tests command handler"""
    data = dashboard_fetch_issue_tests(origin, issue_id, use_json)
    print_data(data, use_json)
