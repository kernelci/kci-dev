#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from functools import wraps

import click

from kcidev.libs.dashboard import (
    dashboard_fetch_boots,
    dashboard_fetch_build,
    dashboard_fetch_builds,
    dashboard_fetch_summary,
    dashboard_fetch_test,
    dashboard_fetch_tests,
)
from kcidev.libs.git_repo import set_giturl_branch_commit
from kcidev.subcommands.results.hardware import hardware
from kcidev.subcommands.results.options import (
    builds_and_tests_options,
    common_options,
    results_display_options,
    single_build_and_test_options,
)
from kcidev.subcommands.results.parser import (
    cmd_builds,
    cmd_list_trees,
    cmd_single_build,
    cmd_single_test,
    cmd_summary,
    cmd_tests,
)


@click.group(
    help="""[Experimental] Query and display test results from the KernelCI dashboard.

This command group provides various ways to retrieve and analyze kernel test
results from the KernelCI dashboard. You can query results by tree, branch,
commit, architecture, and more.

\b
Available subcommands:
  summary   - Display a summary of test results
  trees     - List available kernel trees
  builds    - Display build results
  boots     - Display boot test results
  tests     - Display test suite results
  build     - Display details for a specific build
  boot      - Display details for a specific boot test
  test      - Display details for a specific test
  hardware  - Query hardware-specific results

\b
Examples:
  # Show summary for latest mainline commit
  kci-dev results summary --giturl mainline --latest

  # List all available trees
  kci-dev results trees

  # Show build results for a specific commit
  kci-dev results builds --commit abc123def456

  # Show test results with filtering
  kci-dev results tests --status fail --arch x86_64
""",
    commands={"hardware": hardware},
    invoke_without_command=True,
)
@click.pass_context
def results(ctx):
    """Commands related to results."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        sys.exit(0)


@results.command()
@common_options
def summary(origin, git_folder, giturl, branch, commit, latest, arch, tree, use_json):
    """Display a summary of results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_summary(origin, giturl, branch, commit, arch, use_json)
    cmd_summary(data, use_json)


@results.command()
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@results_display_options
def trees(origin, use_json):
    """List trees from a give origin."""
    cmd_list_trees(origin, use_json)


@results.command()
@common_options
@builds_and_tests_options
def builds(
    origin,
    git_folder,
    giturl,
    branch,
    commit,
    latest,
    arch,
    tree,
    download_logs,
    status,
    filter,
    start_date,
    end_date,
    compiler,
    config,
    count,
    use_json,
):
    """Display build results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_builds(
        origin, giturl, branch, commit, arch, tree, start_date, end_date, use_json
    )
    cmd_builds(data, commit, download_logs, status, compiler, config, count, use_json)


@results.command()
@common_options
@builds_and_tests_options
def boots(
    origin,
    git_folder,
    giturl,
    branch,
    commit,
    latest,
    arch,
    tree,
    download_logs,
    status,
    filter,
    start_date,
    end_date,
    compiler,
    config,
    count,
    use_json,
):
    """Display boot results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_boots(
        origin, giturl, branch, commit, arch, tree, start_date, end_date, use_json
    )
    cmd_tests(
        data["boots"],
        commit,
        download_logs,
        status,
        filter,
        start_date,
        end_date,
        compiler,
        config,
        count,
        use_json,
    )


@results.command()
@common_options
@builds_and_tests_options
def tests(
    origin,
    git_folder,
    giturl,
    branch,
    commit,
    latest,
    arch,
    tree,
    download_logs,
    status,
    filter,
    start_date,
    end_date,
    compiler,
    config,
    count,
    use_json,
):
    """Display test results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_tests(
        origin, giturl, branch, commit, arch, tree, start_date, end_date, use_json
    )
    cmd_tests(
        data["tests"],
        commit,
        download_logs,
        status,
        filter,
        start_date,
        end_date,
        compiler,
        config,
        count,
        use_json,
    )


@results.command()
@single_build_and_test_options
@results_display_options
def test(op_id, download_logs, use_json):
    data = dashboard_fetch_test(op_id, use_json)
    cmd_single_test(data, download_logs, use_json)


@results.command()
@single_build_and_test_options
@results_display_options
def build(op_id, download_logs, use_json):
    data = dashboard_fetch_build(op_id, use_json)
    cmd_single_build(data, download_logs, use_json)


@results.command()
@single_build_and_test_options
@results_display_options
def boot(op_id, download_logs, use_json):
    data = dashboard_fetch_test(op_id, use_json)
    cmd_single_test(data, download_logs, use_json)


if __name__ == "__main__":
    main_kcidev()
