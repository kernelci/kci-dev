#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
from functools import wraps

import click
from tabulate import tabulate

from kcidev.libs.common import kci_msg, kci_msg_green, kci_msg_json, kci_msg_red
from kcidev.libs.dashboard import (
    dashboard_fetch_boot_issues,
    dashboard_fetch_boots,
    dashboard_fetch_build,
    dashboard_fetch_build_issues,
    dashboard_fetch_builds,
    dashboard_fetch_commits_history,
    dashboard_fetch_issue,
    dashboard_fetch_issue_builds,
    dashboard_fetch_issue_list,
    dashboard_fetch_issue_tests,
    dashboard_fetch_issues_extra,
    dashboard_fetch_summary,
    dashboard_fetch_test,
    dashboard_fetch_tests,
    dashboard_fetch_tree_report,
)
from kcidev.libs.git_repo import get_tree_name, set_giturl_branch_commit
from kcidev.libs.regression import CATEGORIES
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
    cmd_tree_report,
    print_issue,
    print_issues,
    print_missing_data,
)


@click.group(
    help="""Query and display test results from the KernelCI dashboard.

This command group provides various ways to retrieve and analyze kernel test
results from the KernelCI dashboard. You can query results by tree, branch,
commit, architecture, and more.

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
@click.option(
    "--error-verbose",
    default=True,
    help="Print error returned from dashboard API",
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
    error_verbose,
):
    """Display build results."""
    giturl, branch, commit = set_giturl_branch_commit(
        origin, giturl, branch, commit, latest, git_folder
    )
    data = dashboard_fetch_builds(
        origin,
        giturl,
        branch,
        commit,
        arch,
        tree,
        start_date,
        end_date,
        use_json,
        error_verbose,
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
@click.option(
    "--error-verbose",
    default=True,
    help="Print error returned from dashboard API",
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
    error_verbose,
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
        error_verbose,
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


def _resolve_latest_two(client, origin, giturl, branch):
    """Return BASE, HEAD and resolved repository details from history."""
    from kcidev.api import KciDevError

    giturl, branch, latest = set_giturl_branch_commit(
        origin, giturl, branch, None, True, None
    )
    history = client.get_commits_history(origin, giturl, branch, latest)
    commits = history if isinstance(history, list) else history.get("commits", [])
    if len(commits) < 2:
        raise KciDevError("fewer than two checkouts are available")
    return (
        commits[1]["git_commit_hash"],
        commits[0]["git_commit_hash"],
        giturl,
        branch,
    )


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
    help="Use latest two checkouts (retained for compatibility; this is the default)",
    default=True,
)
@click.argument("commits", nargs=-1, required=False)
@click.option(
    "--format", "output_format", type=click.Choice(["human", "json"]), default="human"
)
@click.option("--json", "use_json", is_flag=True, hidden=True)
@click.option(
    "--include-issues",
    is_flag=True,
    help="Look up known issues (one request per regression/persistent failure)",
)
@click.pass_context
def compare(
    ctx,
    origin,
    giturl,
    branch,
    latest,
    commits,
    output_format,
    use_json,
    include_issues,
):
    """Compare test results between commits with summary and regressions.

    Compares test results between commits showing summary statistics
    and identifying tests that transitioned from PASS to FAIL status.
    This helps identify genuine regressions while distinguishing them
    from boot-related infrastructure issues.

    With no COMMIT arguments, compares history index 1 (BASE) with index 0
    (HEAD). Alternatively, provide exactly two commit hashes as BASE HEAD.

    \b
    Examples:
      # Compare latest two commits
      kci-dev results compare --giturl https://git.kernel.org/...

      # The legacy --latest spelling remains supported
      kci-dev results compare --giturl https://git.kernel.org/... --latest

      # Compare specific commits
      kci-dev results compare --giturl https://git.kernel.org/... abc123 def456
    """
    from kcidev.api import KciDevError, KernelCIClient

    json_output = use_json or output_format == "json"
    if len(commits) not in (0, 2):
        raise click.UsageError("provide either zero commits or exactly BASE and HEAD")
    try:
        options = ctx.obj or {}
        client = KernelCIClient(
            cfg=options.get("CFG"), instance=options.get("INSTANCE")
        )
        if commits:
            base, head = commits
        else:
            base, head, giturl, branch = _resolve_latest_two(
                client, origin, giturl, branch
            )
        report = client.compare_results(
            base,
            head,
            giturl,
            branch,
            origin,
            include_issues=include_issues,
        )
    except (KciDevError, click.Abort) as exc:
        if json_output:
            click.echo(json.dumps({"error": str(exc), "incomplete": True}))
        else:
            click.echo(f"Incomplete comparison: {exc}", err=True)
        raise click.exceptions.Exit(2) from exc
    if json_output:
        # This is deliberately the only stdout write in JSON mode.
        click.echo(json.dumps(report, sort_keys=True))

    else:
        click.echo(f"Compared {base} -> {head}")
        for category, count in report["counts"].items():
            click.echo(f"  {category}: {count}")
    if report["incomplete"]:
        raise click.exceptions.Exit(2)
    if report["counts"]["regression"]:
        raise click.exceptions.Exit(1)


@results.command()
@click.option("--origin", default="maestro", help="Select KCIDB origin")
@click.option("--giturl", required=True, help="Git repository URL")
@click.option("--branch", required=True, help="Git branch name")
@click.option("--base", help="Baseline checkout commit (defaults to previous)")
@click.option("--head", help="Candidate checkout commit (defaults to latest)")
@click.option(
    "--fail-on",
    default="regression",
    show_default=True,
    help="Comma-separated report categories which fail the gate",
)
@click.option(
    "--format", "output_format", type=click.Choice(["human", "json"]), default="human"
)
@click.pass_context
def gate(ctx, origin, giturl, branch, base, head, fail_on, output_format):
    """Gate a checkout using the regression comparison policy."""
    from kcidev.api import KciDevError, KernelCIClient

    policies = {value.strip() for value in fail_on.split(",") if value.strip()}
    unknown_policies = policies.difference(CATEGORIES)
    if unknown_policies:
        unknown = ", ".join(sorted(unknown_policies))
        raise click.UsageError(f"unknown --fail-on categories: {unknown}")

    try:
        options = ctx.obj or {}
        client = KernelCIClient(
            cfg=options.get("CFG"), instance=options.get("INSTANCE")
        )
        if bool(base) != bool(head):
            raise click.UsageError("provide both --base and --head, or neither")
        if not base:
            base, head, giturl, branch = _resolve_latest_two(
                client, origin, giturl, branch
            )
        report = client.compare_results(base, head, giturl, branch, origin)
    except (KciDevError, click.Abort) as exc:
        if output_format == "json":
            click.echo(json.dumps({"error": str(exc), "incomplete": True}))
        else:
            click.echo(f"Incomplete comparison: {exc}", err=True)
        raise click.exceptions.Exit(2) from exc
    click.echo(
        json.dumps(report, sort_keys=True)
        if output_format == "json"
        else "\n".join(f"{key}: {value}" for key, value in report["counts"].items())
    )
    if report["incomplete"]:
        raise click.exceptions.Exit(2)
    if any(report["counts"].get(value, 0) for value in policies):
        raise click.exceptions.Exit(1)


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


def _fetch_checkout_issues(
    origin, tree_name, giturl, branch, commit, arch, new_only=False
):
    """Fetch distinct issue versions reported by a checkout."""
    summary = dashboard_fetch_summary(origin, giturl, branch, commit, arch, True)[
        "summary"
    ]
    keys = dict.fromkeys(
        (issue["id"], issue["version"])
        for kind in ("builds", "boots", "tests")
        for issue in summary[kind]["issues"]
    )
    if not keys:
        return [], set()
    extras = dashboard_fetch_issues_extra([list(key) for key in keys], True)["issues"]
    new_keys = set()
    for issue_id, version in keys:
        extra = extras.get(issue_id) or {}
        incident = extra.get("first_incident") or {}
        version_info = (extra.get("versions") or {}).get(str(version))
        # First-incident data belongs to the issue ID; it may describe another
        # version. Missing versions and versions without incidents are not new.
        if (
            version_info
            and version_info.get("trees")
            and incident.get("issue_version") == version
            and incident.get("git_commit_hash") == commit
            and incident.get("git_repository_url") == giturl
            and incident.get("git_repository_branch") == branch
            and incident.get("tree_name") == tree_name
        ):
            new_keys.add((issue_id, version))
    data = [
        dashboard_fetch_issue(issue_id, True, version=version)
        for issue_id, version in keys
        if not new_only or (issue_id, version) in new_keys
    ]
    return data, new_keys


def get_new_issues(
    origin, tree_name, giturl, branch, commit, arch, use_json=False, *, display=True
):
    """Get issue versions first observed on this checkout."""
    data, _ = _fetch_checkout_issues(
        origin, tree_name, giturl, branch, commit, arch, new_only=True
    )
    if display:
        if use_json:
            kci_msg_json(data)
        else:
            kci_msg_green(f"{tree_name}/{branch}:{commit}")
            if not data:
                kci_msg("No new issues found")
            for item in data:
                print_issue(item)
    return data


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


def get_missing_issue_items(
    ctx, origin, item_type, giturl, branch, commit, tree_name, arch
):
    """Get information of failed or inconclusive builds/boots for which KCIDB
    issues don't exist"""
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
            error_verbose=False,
        )

        missing_ids = []
        for item in dashboard_items:
            # Exclude passed builds/boots
            if item["status"] == "PASS":
                continue
            item_id = item["id"]
            try:
                _ = dashboard_func(item_id, False, error_verbose=False)
            except click.ClickException as e:
                if "No issues" in e.message:
                    missing_ids.append({item_id: item["status"]})
        if missing_ids:
            return [f"{tree_name}/{branch}", commit, missing_ids]
        return []
    except click.Abort:
        kci_msg_red(
            f"{tree_name}/{branch}: Aborted while fetching dashboard builds/boots"
        )
        return []
    except click.ClickException as e:
        kci_msg_red(f"{tree_name}/{branch}: {e.message}")
        return []


def get_filtered_issues(
    origin, tree_name, giturl, branch, commit, arch, use_json=False
):
    """Get the exact KCIDB issue versions reported by a checkout."""
    data, new_keys = _fetch_checkout_issues(
        origin, tree_name, giturl, branch, commit, arch
    )
    if use_json:
        kci_msg_json(data)
    else:
        kci_msg_green(f"{tree_name}/{branch}:{commit}")
        if not data:
            kci_msg("No issues found")
        for item in data:
            print_issue(item, (item["id"], item["version"]) in new_keys)
    return data


@results.command(
    name="issues",
    help="""Fetch KCIDB issues from the dashboard

\b
Examples:
  # Get issues
  kci-dev results issues --origin <origin> --days <number-of-days>
  # Get issues within exact UTC boundaries
  kci-dev results issues --start-date 2026-08-01T00:00:00Z --end-date 2026-08-08T00:00:00Z
  # Get new issues for all checkouts
  kci-dev results issues --new --days <number-of-days> --origin <origin>
  # Get new issues for a checkout
  kci-dev results issues --new --giturl <git-url> --branch <git-branch> --commit <commit> --origin <origin>
  # Get failed or inconclusive builds and boots without any issue for all checkouts
  kci-dev results issues --missing
  # Get failed or inconclusive builds and boots without any issue for specific checkout
  kci-dev results issues --missing --giturl <git-url> --branch <git-branch> --commit <commit> --origin <origin>
  # Get failed/inconclusive builds without issues
  kci-dev results issues --missing --builds
  # Get failed/inconclusive boots without issues
  kci-dev results issues --missing --boots
""",
)
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@click.option(
    "--days",
    help="Get results for the last N days (default: 5); cannot be combined with a date range",
    type=int,
    default=None,
)
@click.option(
    "--start-date",
    help="Issue listing start: YYYY-MM-DD (UTC midnight) or timezone-aware ISO 8601; requires --end-date",
)
@click.option(
    "--end-date",
    help="Issue listing end: YYYY-MM-DD (UTC midnight) or timezone-aware ISO 8601; requires --start-date",
)
@click.option(
    "--new",
    is_flag=True,
    help="Fetch new KCIDB issues for a checkout",
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
@click.option(
    "--missing",
    is_flag=True,
    help="List all failed/incomplete builds and boots without any issue associated to them",
)
@click.option(
    "--builds",
    is_flag=True,
    help="The option can be used along with '--missing' to list only builds",
)
@click.option(
    "--boots",
    is_flag=True,
    help="The option can be used along with '--missing' to list only boots",
)
@click.option("--arch", help="Filter by arch")
@click.option("--tree", help="Filter by tree name")
@click.pass_context
@results_display_options
def issues(
    ctx,
    origin,
    days,
    start_date,
    end_date,
    new,
    giturl,
    branch,
    commit,
    use_json,
    latest,
    git_folder,
    arch,
    tree,
    missing,
    builds,
    boots,
):
    """Issues command handler"""
    has_date_range = start_date is not None or end_date is not None
    if has_date_range and any(
        [
            new,
            missing,
            giturl,
            branch,
            commit,
            git_folder,
            latest,
            arch,
            tree,
            builds,
            boots,
        ]
    ):
        raise click.UsageError(
            "--start-date and --end-date are only supported for the unfiltered issue "
            "listing (with optional --origin and --json)"
        )
    if not has_date_range and days is None:
        days = 5
    if not new and not missing:
        if not any([giturl, branch, commit]):
            data = dashboard_fetch_issue_list(
                origin, days, use_json, start_date, end_date
            )
            print_issues(data, use_json)
            return
        if not all([giturl, branch, commit]):
            raise click.UsageError(
                "Please provide --giturl, --branch and --commit to get issues for"
            )
        if not tree:
            tree = get_tree_name(origin, giturl, branch)
        giturl, branch, commit = set_giturl_branch_commit(
            origin, giturl, branch, commit, latest, git_folder, quiet=use_json
        )
        get_filtered_issues(origin, tree, giturl, branch, commit, arch, use_json)
    if new:
        if not any([giturl, branch, commit]):
            if not use_json:
                kci_msg("Fetching new issues for all checkouts...")
            trees_list = ctx.invoke(trees, origin=origin, days=days, verbose=False)
            new_issues = {}
            for t in trees_list:
                giturl = t["git_repository_url"]
                branch = t["git_repository_branch"]
                commit = t["git_commit_hash"]
                tree_name = t["tree_name"]
                data = get_new_issues(
                    origin,
                    tree_name,
                    giturl,
                    branch,
                    commit,
                    arch,
                    use_json,
                    display=not use_json,
                )
                for item in data:
                    new_issues[(item["id"], item["version"])] = item
            if use_json:
                kci_msg_json(list(new_issues.values()))
            return
        if not all([giturl, branch, commit]):
            raise click.UsageError(
                "Please provide --giturl, --branch, and --commit to fetch new issues for "
                "a checkout or else omit all these options to fetch new issues for all the "
                "checkouts"
            )
        if not use_json:
            kci_msg("Fetching new issues for the checkout...")
        giturl, branch, commit = set_giturl_branch_commit(
            origin, giturl, branch, commit, latest, git_folder, quiet=use_json
        )
        if not tree:
            tree = get_tree_name(origin, giturl, branch)
        get_new_issues(origin, tree, giturl, branch, commit, arch, use_json)
    if missing:
        if builds:
            item_types = ["builds"]
        elif boots:
            item_types = ["boots"]
        else:
            item_types = ["builds", "boots"]

        if all([giturl, branch, commit]):
            if not tree:
                tree = get_tree_name(origin, giturl, branch)
            for item_type in item_types:
                final_stats = []
                kci_msg("")
                kci_msg_green(f"Fetching data for {item_type}...")
                stats = get_missing_issue_items(
                    ctx, origin, item_type, giturl, branch, commit, tree, arch
                )
                if stats:
                    final_stats.append(stats)
                if final_stats:
                    print_missing_data(item_type, final_stats)

        else:
            trees_list = ctx.invoke(trees, origin=origin, days=days, verbose=False)
            for item_type in item_types:
                kci_msg("")
                kci_msg_green(f"Fetching data for {item_type}...")
                final_stats = []
                for tree in trees_list:
                    giturl = tree["git_repository_url"]
                    branch = tree["git_repository_branch"]
                    commit = tree["git_commit_hash"]
                    tree_name = tree["tree_name"]
                    stats = get_missing_issue_items(
                        ctx, origin, item_type, giturl, branch, commit, tree_name, arch
                    )
                    if stats:
                        final_stats.append(stats)
                if final_stats:
                    print_missing_data(item_type, final_stats)


@results.command(
    name="issue",
    help="""Fetch KCIDB issue matching provided ID.
Also get associated builds and tests.

\b
Examples:
  # Get issue information and associated builds/tests
  kci-dev results issue --id <id> --origin <origin>
""",
)
@click.option(
    "--id",
    "issue_id",
    required=True,
    help="Issue ID to get information for",
)
@click.option(
    "--origin",
    help="Select KCIDB origin",
)
@click.option(
    "--version", type=click.IntRange(min=0), help="Issue version (default: latest)"
)
@results_display_options
def issue(issue_id, origin, version, use_json):
    """Get an issue and its associated builds/tests at the same version."""
    data = dashboard_fetch_issue(issue_id, use_json, version=version)
    related = {}
    for item_type, fetch in (
        ("builds", dashboard_fetch_issue_builds),
        ("tests", dashboard_fetch_issue_tests),
    ):
        try:
            related[item_type] = fetch(
                origin, issue_id, use_json, error_verbose=False, version=data["version"]
            )
        except click.ClickException as exc:
            if exc.message != f"No {item_type} found for this issue":
                raise
            related[item_type] = []
    if use_json:
        kci_msg_json({"issue": data, **related})
        return
    kci_msg_green("Issue information:")
    print_issue(data)
    for item_type, items in related.items():
        kci_msg_green(f"Associated {item_type}:")
        if not items:
            kci_msg(f"No associated {item_type} found")
        for item in items:
            kci_msg(f"- {item['id']}")
        kci_msg("")


@results.command(
    name="tree-report",
    help="""Fetch tree report

\b
The command is used to fetch tree report using dashboard API.
The report will consist of build, boot, and tests summary along with regression
and unstable tests information.

\b
Examples:
  # Get report by providing url and branch
  kci-dev results tree-report --giturl <giturl> --branch <branch>
""",
)
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
)
@click.option(
    "--giturl",
    help="Git URL of kernel tree ",
    required=True,
)
@click.option(
    "--branch",
    help="Branch to get results for",
    required=True,
)
@click.option(
    "--path",
    multiple=True,
    help="A list of test paths to query for. SQL Wildcard can be used.",
)
@click.option(
    "--history-size",
    default=3,
    help="Maximum number of entries to be retrieved in a test history.",
)
@click.option(
    "--max-age",
    default=24,
    help="Maximum age for the queried checkout and related tests in hours",
)
@click.option(
    "--min-age", default=0, help="Minimum age of the queried checkout in hours."
)
@click.option(
    "--no-emoji",
    is_flag=True,
    help="Use ASCII labels instead of emoji in status histories. JSON is unchanged.",
)
@results_display_options
def tree_report(
    origin,
    giturl,
    branch,
    path,
    history_size,
    max_age,
    min_age,
    use_json,
    no_emoji=False,
):
    """Fetch tree report"""
    data = dashboard_fetch_tree_report(
        origin, branch, giturl, use_json, path, history_size, max_age, min_age
    )
    cmd_tree_report(data, use_json, no_emoji=no_emoji)


if __name__ == "__main__":
    main_kcidev()
