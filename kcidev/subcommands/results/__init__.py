#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from functools import wraps

import click

from kcidev.libs.dashboard import (
    dashboard_fetch_boots,
    dashboard_fetch_build,
    dashboard_fetch_builds,
    dashboard_fetch_commits_history,
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
    cmd_commits_history,
    cmd_list_trees,
    cmd_regressions,
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
  regressions - Find test regressions between commits

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
@click.option("--history", is_flag=True, help="Show commit history data")
def summary(
    origin, git_folder, giturl, branch, commit, latest, arch, tree, history, use_json
):
    """Display a summary of results."""
    if history:
        # For history, always use latest commit
        giturl, branch, commit = set_giturl_branch_commit(
            origin, giturl, branch, commit, True, git_folder
        )
        data = dashboard_fetch_commits_history(origin, giturl, branch, commit, use_json)
        cmd_commits_history(data, use_json)
    else:
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
@click.option(
    "--days",
    help="Provide a period of time in days to get results for",
    type=int,
    default=7,
)
@click.option(
    "--verbose",
    is_flag=True,
    default=True,
    help="Print tree details",
)
@results_display_options
def trees(origin, use_json, days, verbose):
    """List trees from a give origin."""
    return cmd_list_trees(origin, use_json, days, verbose)


@results.command()
@common_options
@builds_and_tests_options
@click.option(
    "--verbose",
    is_flag=True,
    default=True,
    help="Print build details",
)
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
    git_branch,
    count,
    use_json,
    hardware,
    test_path,
    compatible,
    min_duration,
    max_duration,
    verbose,
):
    """Display build results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_builds(
        origin, giturl, branch, commit, arch, tree, start_date, end_date, use_json
    )
    return cmd_builds(
        data,
        commit,
        download_logs,
        status,
        compiler,
        config,
        git_branch,
        count,
        use_json,
        verbose,
    )


@results.command()
@common_options
@builds_and_tests_options
@click.option(
    "--verbose",
    is_flag=True,
    default=True,
    help="Print boot details",
)
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
    hardware,
    test_path,
    git_branch,
    compatible,
    min_duration,
    max_duration,
    count,
    use_json,
    verbose,
):
    """Display boot results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_boots(
        origin, giturl, branch, commit, arch, tree, start_date, end_date, use_json
    )
    return cmd_tests(
        data["boots"],
        commit,
        download_logs,
        status,
        filter,
        start_date,
        end_date,
        compiler,
        config,
        hardware,
        test_path,
        git_branch,
        compatible,
        min_duration,
        max_duration,
        count,
        use_json,
        verbose,
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
    hardware,
    test_path,
    git_branch,
    compatible,
    min_duration,
    max_duration,
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
        hardware,
        test_path,
        git_branch,
        compatible,
        min_duration,
        max_duration,
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


@results.command()
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@click.option(
    "--giturl",
    help="Git repository URL or alias (e.g., mainline, linux-next)",
    required=True,
)
@click.option(
    "--branch",
    help="Git branch name",
    required=True,
)
@click.option(
    "--latest",
    is_flag=True,
    help="Use latest commits from history (default: compare latest 2 commits)",
    default=True,
)
@click.argument("commits", nargs=-1, required=False)
@results_display_options
def regressions(origin, giturl, branch, latest, commits, use_json):
    """Find test regressions (PASS->FAIL transitions) between commits.

    Compares test results between commits and identifies tests that
    transitioned from PASS to FAIL status. This helps identify genuine
    regressions while distinguishing them from boot-related infrastructure
    issues.

    By default, compares the latest two commits from history. You can also
    specify two specific commit hashes to compare.

    \b
    Examples:
      # Find regressions between latest two commits
      kci-dev results regressions --giturl https://git.kernel.org/...

      # Find regressions between specific commits
      kci-dev results regressions --giturl https://git.kernel.org/... abc123 def456
    """
    if latest and not commits:
        # Use latest commits from history
        cmd_regressions(origin, giturl, branch, None, use_json)
    elif len(commits) == 2:
        # Use specific commits provided
        cmd_regressions(origin, giturl, branch, list(commits), use_json)
    else:
        click.echo("Error: Provide either --latest flag or exactly 2 commit hashes")
        raise click.Abort()


if __name__ == "__main__":
    main_kcidev()
