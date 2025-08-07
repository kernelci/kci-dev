#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from functools import wraps

import click
from tabulate import tabulate

from kcidev.libs.common import kci_msg_green, kci_msg_red
from kcidev.libs.dashboard import (
    dashboard_fetch_boot_issues,
    dashboard_fetch_boots,
    dashboard_fetch_build,
    dashboard_fetch_build_issues,
    dashboard_fetch_builds,
    dashboard_fetch_commits_history,
    dashboard_fetch_issues_extra,
    dashboard_fetch_summary,
    dashboard_fetch_test,
    dashboard_fetch_tests,
)
from kcidev.libs.git_repo import get_tree_name, set_giturl_branch_commit
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
    cmd_compare,
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
  compare   - Compare test results between commits
  issues    - Query KCIDB issues

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
  # Display KCIDB issues
  kci-dev results issues list
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
@click.option(
    "--boot-origin",
    help="Select KCIDB boot origin",
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
    boot_origin,
):
    """Display boot results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_boots(
        origin,
        giturl,
        branch,
        commit,
        arch,
        tree,
        start_date,
        end_date,
        use_json,
        boot_origin,
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
def compare(origin, giturl, branch, latest, commits, use_json):
    """Compare test results between commits with summary and regressions.

    Compares test results between commits showing summary statistics
    and identifying tests that transitioned from PASS to FAIL status.
    This helps identify genuine regressions while distinguishing them
    from boot-related infrastructure issues.

    By default, compares the latest two commits from history. You can also
    specify two specific commit hashes to compare.

    \b
    Examples:
      # Compare latest two commits
      kci-dev results compare --giturl https://git.kernel.org/...

      # Compare specific commits
      kci-dev results compare --giturl https://git.kernel.org/... abc123 def456
    """
    if latest and not commits:
        # Use latest commits from history
        cmd_compare(origin, giturl, branch, None, use_json)
    elif len(commits) == 2:
        # Use specific commits provided
        cmd_compare(origin, giturl, branch, list(commits), use_json)
    else:
        click.echo("Error: Provide either --latest flag or exactly 2 commit hashes")
        raise click.Abort()


def get_issues(ctx, origin, item_type, giturl, branch, commit, tree_name, arch):
    """Get KCIDB issues for builds/boots"""
    try:
        if item_type == "builds":
            results_cmd = builds
            dashboard_func = dashboard_fetch_build_issues
        elif item_type == "boots":
            results_cmd = boots
            dashboard_func = dashboard_fetch_boot_issues
        else:
            kci_msg_red("Please specify 'builds' or 'boots' as items type")
            return []

        dashboard_items = ctx.invoke(
            results_cmd,
            origin=origin,
            giturl=giturl,
            branch=branch,
            commit=commit,
            status="all",
            count=True,
            verbose=False,
            arch=arch,
        )
        final_stats = []
        for item in dashboard_items:
            # Exclude passed builds/boots
            if item["status"] == "PASS":
                continue
            item_id = item["id"]
            try:
                issues = dashboard_func(item_id, False)
                issue_ids = []
                for issue in issues:
                    issue_ids.append(issue["id"])
                final_stats.append([f"{tree_name}/{branch}", item_id, issue_ids])
            except click.ClickException as e:
                if e.message in (
                    "No issues were found for this build",
                    "No issues were found for this test",
                ):
                    final_stats.append([f"{tree_name}/{branch}", item_id, []])
        return final_stats
    except click.Abort:
        kci_msg_red(
            f"{tree_name}/{branch}: Aborted while fetching dashboard builds/boots"
        )
        return []
    except click.ClickException as e:
        kci_msg_red(f"{tree_name}/{branch}: {e.message}")
        return []


def get_issues_for_specific_item(item_type, item_id):
    """Get KCIDB issues for a specific build/boot matching provided ID"""
    try:
        if item_type == "builds":
            dashboard_func = dashboard_fetch_build_issues
        elif item_type == "boots":
            dashboard_func = dashboard_fetch_boot_issues
        else:
            kci_msg_red("Please specify 'builds' or 'boots' as items type")
            return []
        issues = dashboard_func(item_id, False)
        issue_ids = []
        for issue in issues:
            issue_ids.append(issue["id"])
        stats = [[item_id, issue_ids]]
        return stats
    except click.ClickException as e:
        if e.message == "No issues were found for this build":
            stats = [[item_id, []]]
            return stats
        return None


def print_stats(data, headers, max_col_width, table_fmt):
    """Print build statistics in tabular format"""
    print("Creating a stats report...")
    print(
        tabulate(data, headers=headers, maxcolwidths=max_col_width, tablefmt=table_fmt)
    )


def get_new_issues(origin, tree_name, giturl, branch, commit, arch):
    """Get new KCIDB issue for a checkout"""
    try:
        data = dashboard_fetch_summary(origin, giturl, branch, commit, arch, True)
        tree_summary = data["summary"]
        items = ["builds", "boots", "tests"]
        all_issues = []
        new_issues = []
        for item in items:
            for i in tree_summary[item]["issues"]:
                all_issues.append([i["id"], i["version"]])
        if not all_issues:
            kci_msg_red(f"{tree_name}/{branch}:{commit} No issues found")
            return
        issue_extras = dashboard_fetch_issues_extra(all_issues, True)["issues"]
        for issue_id, extras in issue_extras.items():
            first_incident = extras.get("first_incident")
            if first_incident:
                if all(
                    [
                        first_incident["git_commit_hash"] == commit,
                        first_incident["git_repository_url"] == giturl,
                        first_incident["git_repository_branch"] == branch,
                    ]
                ):
                    new_issues.append(issue_id)
        if not new_issues:
            kci_msg_red(f"{tree_name}/{branch}:{commit} No new issues found")
        else:
            kci_msg_green(f"{tree_name}/{branch}:{commit} New issues: {new_issues}")
    except click.ClickException as e:
        print("Exception:", e.message)


@click.command(
    name="detect",
    help="""Detect KCIDB issues for builds and boots

\b
The command is used to fetch KCIDB issues associated with builds and boots.
It can also detect new issues i.e. issues observed for the first time for
a checkout.
Provide `--builds` and `--boots` option for builds issue detection and boots
issue detection respectively.
`--all-checkouts` option can be used to fetch KCIDB issues for all the
failed and inconclusive builds/boots from all available trees on the dashboard.
Issues for a single build/boot can be retrieved by providing `--id`
option.

\b
Examples:
  # Detect build issues
  kci-dev issues detect --builds --id <build-id>
  kci-dev issues detect --builds --all-checkouts --days <number-of-days> --origin <origin>
  # Detect boot issues
  kci-dev issues detect --boots --id <boot-id>
  kci-dev issues detect --boots --all-checkouts --days <number-of-days> --origin <origin>
  # Detect new issues for a checkout
  kci-dev issues detect --new --all-checkouts --days <number-of-days> --origin <origin>
  kci-dev issues detect --new --giturl <git-url> --branch <git-branch> --commit <commit> --origin <origin>
""",
)
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@click.option(
    "--builds",
    is_flag=True,
    help="Fetch KCIDB issues for builds",
)
@click.option(
    "--boots",
    is_flag=True,
    help="Fetch KCIDB issues for boots",
)
@click.option(
    "--new",
    is_flag=True,
    help="Fetch new KCIDB issues for a checkout",
)
@click.option(
    "--id",
    "item_id",
    help="Build/boot id to get issues for",
)
@click.option(
    "--all-checkouts",
    is_flag=True,
    help="Fetch KCIDB issues for all failed/inconclusive builds/boots of all available checkouts",
)
@click.option("--arch", help="Filter by arch")
@click.option(
    "--days",
    help="Provide a period of time in days to get results for",
    type=int,
    default="7",
)
@click.option(
    "--giturl",
    help="Git URL of kernel tree",
)
@click.option(
    "--branch",
    help="Branch to get results for",
)
@click.option(
    "--commit",
    help="Commit or tag to get results for",
)
@click.option(
    "--git-folder",
    help="Path of git repository folder",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--latest",
    is_flag=True,
    help="Select latest results available",
)
@click.pass_context
def detect(
    ctx,
    origin,
    builds,
    boots,
    new,
    item_id,
    all_checkouts,
    arch,
    days,
    giturl,
    branch,
    commit,
    latest,
    git_folder,
):

    if not (builds or boots or new):
        raise click.UsageError(
            "Provide --builds or --boots or --new to fetch issues for"
        )

    if new:
        if all_checkouts:
            print("Fetching new issues for all checkouts...")
            trees_list = ctx.invoke(trees, origin=origin, days=days, verbose=False)
            for tree in trees_list:
                giturl = tree["git_repository_url"]
                branch = tree["git_repository_branch"]
                commit = tree["git_commit_hash"]
                tree_name = tree["tree_name"]
                get_new_issues(origin, tree_name, giturl, branch, commit, arch)
            return

        print("Fetching new issues for the checkout...")
        giturl, branch, commit = set_giturl_branch_commit(
            origin, giturl, branch, commit, latest, git_folder
        )
        tree_name = get_tree_name(origin, giturl, branch)
        get_new_issues(origin, tree_name, giturl, branch, commit, arch)
        return

    if builds and boots:
        raise click.UsageError("Specify only one option from --builds and --boots")

    item_type = "builds" if builds else "boots"

    if not (all_checkouts or item_id):
        raise click.UsageError("Provide --all-checkouts or --id")

    print("Fetching KCIDB issues...")
    if all_checkouts:
        if item_id:
            raise click.UsageError("Cannot use --all-checkouts with --id")
        final_stats = []
        trees_list = ctx.invoke(trees, origin=origin, days=days, verbose=False)
        for tree in trees_list:
            giturl = tree["git_repository_url"]
            branch = tree["git_repository_branch"]
            commit = tree["git_commit_hash"]
            tree_name = tree["tree_name"]
            stats = get_issues(
                ctx, origin, item_type, giturl, branch, commit, tree_name, arch
            )
            final_stats.extend(stats)
        if final_stats:
            headers = [
                "tree/branch",
                "ID",
                "Issues",
            ]
            max_col_width = [None, None, None]
            table_fmt = "simple_grid"
            print_stats(final_stats, headers, max_col_width, table_fmt)

    elif item_id:
        stats = get_issues_for_specific_item(item_type, item_id)
        if stats:
            headers = [
                "ID",
                "Issues",
            ]
            max_col_width = [None, None]
            table_fmt = "simple_grid"
            print_stats(stats, headers, max_col_width, table_fmt)


if __name__ == "__main__":
    main_kcidev()
