#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

import click

from kcidev.libs.common import kci_msg, kci_msg_cyan, kci_msg_green, kci_msg_nonl
from kcidev.libs.maestro_common import maestro_get_nodes
from kcidev.subcommands.maestro.results import results
from kcidev.subcommands.maestro.validate import validate


@click.group(
    help="""Maestro-specific commands for interacting with KernelCI's Maestro API.

This command group provides access to various Maestro operations including
querying test results and in the future will include other maestro-specific
commands.

\b
Available subcommands:
  results   - Query test results from Maestro API

\b
Examples:
  # Query test results
  kci-dev maestro results --nodeid <NODE_ID>
  kci-dev maestro results --nodes --limit 10
""",
    invoke_without_command=True,
)
@click.pass_context
def maestro(ctx):
    """Maestro-specific commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        sys.exit(0)


@maestro.command(
    name="coverage",
    help="""Fetch coverage information for maestro results on chromiumos tree
\b
Examples:
  # Get coverage information
  kci-dev maestro coverage
  # Use command with filters
  kci-dev maestro coverage --start-date 2025-09-02
""",
)
@click.option(
    "--branch",
    help="Filter results by branch name",
)
@click.option(
    "--commit",
    help="Commit to get results for",
)
@click.option(
    "--limit",
    default=1000,
    help="Maximum number of nodes to retrieve (default: 1000)",
)
@click.option(
    "--offset",
    default=0,
    help="Starting position for pagination (default: 0)",
)
@click.option(
    "--start-date",
    help="Filter results after this date (ISO format: YYYY-MM-DD or full timestamp)",
)
@click.option(
    "--end-date",
    help="Filter results before this date (ISO format: YYYY-MM-DD or full timestamp)",
)
@click.pass_context
def coverage(ctx, branch, commit, limit, offset, start_date, end_date):
    """Get coverage handler"""
    config_data = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    api_url = config_data[instance]["api"]
    filters = [
        "kind=kbuild",
        "state=done",
        "result=pass",
        "data.kernel_revision.tree=chromiumos",
    ]
    if branch:
        filters.append(f"data.kernel_revision.branch={branch}")
    if commit:
        filters.append(f"data.kernel_revision.commit={commit}")
    if start_date:
        filters.append(f"created__gt={start_date}")
    if end_date:
        filters.append(f"created__lt={end_date}")
    build_nodes = maestro_get_nodes(api_url, limit, offset, filters, True)
    for build_node in build_nodes:
        child_nodes = maestro_get_nodes(
            api_url,
            limit,
            offset,
            [f"parent={build_node['id']}", "kind=process", "state=done", "result=pass"],
            True,
        )
        for child in child_nodes:
            if not child["name"].startswith("coverage-report"):
                continue
            artifacts = child.get("artifacts")
            if artifacts:
                coverage_tests = maestro_get_nodes(
                    api_url, 50, 0, [f"parent={child['id']}", "kind=test"], True
                )
                if not coverage_tests:
                    continue
                b = child["data"].get("kernel_revision", {}).get("branch")
                c = child["data"].get("kernel_revision", {}).get("commit")
                kci_msg_nonl("- Tree/branch: ")
                kci_msg_cyan(f"chromiumos/{b}")
                kci_msg(f"  Commit: {c}")
                kci_msg(f"  Build: {api_url}viewer?node_id={build_node['id']}")
                for test in coverage_tests:
                    if test["name"] == "coverage.functions":
                        func_coverage = test["data"].get("misc", {}).get("measurement")
                        kci_msg_nonl("  Function coverage: ")
                        kci_msg_green(f"{func_coverage}%")
                    if test["name"] == "coverage.lines":
                        line_coverage = test["data"].get("misc", {}).get("measurement")
                        kci_msg_nonl("  Line coverage: ")
                        kci_msg_green(f"{line_coverage}%")
                kci_msg(f"  Coverage report: {artifacts.get('coverage_report')}")
                kci_msg(f"  Coverage logs: {artifacts.get('log')}")
                kci_msg("")


# Add subcommands to the maestro group
maestro.add_command(results)
maestro.add_command(validate)

if __name__ == "__main__":
    from kcidev.libs.common import main_kcidev

    main_kcidev()
