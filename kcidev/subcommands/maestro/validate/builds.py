import sys

import click

from kcidev.libs.git_repo import get_tree_name, set_giturl_branch_commit
from kcidev.subcommands.results import trees

from .helper import (
    get_build_stats,
    get_builds_history_stats,
    print_simple_list,
    print_table_stats,
    print_validation_json,
    validation_rows_to_json,
)


@click.command(
    name="builds",
    help="""Validate dashboard build results with maestro.

Provide --all-checkouts flag to pull all builds of available
checkouts from dashboard and compare them with results from maestro.
It also supports --days option to specify number of days to get builds for.

Build validation for a specific checkout can be performed by
using all three options: --giturl, --branch, and --commit
If above options are not provided, if will take latest/provided commit
checkout from the git folder specified.

Builds history validation, i.e. checking if number of builds is consistent
for different checkouts of the same git tree/branch, can be performed by the command
by providing --history option.

\b
Examples:
    # Build validation
    kci-dev maestro validate builds --all-checkouts --days <number-of-days>
    kci-dev maestro validate builds --commit <git-commit> --giturl <git-url> --branch <git-branch>
    # Build history validation
    kci-dev maestro validate builds --history --all-checkouts --days <number-of-days>
    kci-dev maestro validate builds --history --giturl <git-url> --branch <git-branch> --days <number-of-days>
""",
)
@click.option(
    "--all-checkouts",
    is_flag=True,
    help="Get build validation stats for all available checkouts",
)
@click.option(
    "--days",
    help="Provide a period of time in days to get results for",
    type=int,
    default="7",
)
@click.option(
    "--origin",
    help="Select KCIDB origin",
    default="maestro",
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
)
@click.option(
    "--latest",
    is_flag=True,
    help="Select latest results available",
)
@click.option("--arch", help="Filter by arch")
@click.option(
    "--history",
    is_flag=True,
    help="Check if number of builds is consistent for different checkouts of the same git tree/branch",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Get detailed output",
)
@click.option(
    "--table-output",
    is_flag=True,
    default=False,
    help="Display results in table format instead of simple list",
)
@click.option(
    "--json",
    "use_json",
    is_flag=True,
    default=False,
    help="Print validation results as JSON",
)
@click.option(
    "--fail-on-mismatch",
    is_flag=True,
    default=False,
    help="Exit with status 1 when validation finds mismatches",
)
@click.pass_context
def builds(
    ctx,
    all_checkouts,
    origin,
    giturl,
    branch,
    commit,
    git_folder,
    latest,
    arch,
    days,
    history,
    verbose,
    table_output,
    use_json,
    fail_on_mismatch,
):
    final_stats = []
    stdout = sys.stdout
    if use_json:
        sys.stdout = sys.stderr
    try:
        if not use_json:
            print("Fetching build information...")
        if all_checkouts:
            if giturl or branch or commit:
                raise click.UsageError(
                    "Cannot use --all-checkouts with --giturl, --branch, or --commit"
                )
            if history:
                trees_list = ctx.invoke(trees, origin=origin, days=days, verbose=False)
                for tree in trees_list:
                    giturl = tree["git_repository_url"]
                    branch = tree["git_repository_branch"]
                    tree_name = tree["tree_name"]
                    stats = get_builds_history_stats(
                        ctx, giturl, branch, tree_name, arch, days, verbose, use_json
                    )
                    if stats:
                        final_stats.extend(stats)
            else:
                trees_list = ctx.invoke(trees, origin=origin, days=days, verbose=False)
                for tree in trees_list:
                    giturl = tree["git_repository_url"]
                    branch = tree["git_repository_branch"]
                    commit = tree["git_commit_hash"]
                    tree_name = tree["tree_name"]
                    stats = get_build_stats(
                        ctx, giturl, branch, commit, tree_name, verbose, arch, use_json
                    )
                    if stats:
                        final_stats.append(stats)
        elif history:
            tree_name = get_tree_name(origin, giturl, branch)
            final_stats = get_builds_history_stats(
                ctx, giturl, branch, tree_name, arch, days, verbose, use_json
            )
        else:
            giturl, branch, commit = set_giturl_branch_commit(
                origin, giturl, branch, commit, latest, git_folder
            )
            tree_name = get_tree_name(origin, giturl, branch)
            stats = get_build_stats(
                ctx, giturl, branch, commit, tree_name, verbose, arch, use_json
            )
            if stats:
                final_stats.append(stats)
    finally:
        sys.stdout = stdout
    if use_json:
        report = print_validation_json(
            "builds", final_stats, history, origin, days, arch
        )
        if fail_on_mismatch and not report["summary"]["ok"]:
            ctx.exit(1)
        return
    if final_stats:
        if history:
            headers = [
                "tree/branch",
                "Commit",
                "Maestro\nbuilds",
                "Dashboard\nbuilds",
                "Build count\ncomparison",
                "Missing build IDs",
            ]
            max_col_width = [None, 40, 3, 3, 2, 30]

        else:
            headers = [
                "tree/branch",
                "Commit",
                "Maestro\nbuilds",
                "Dashboard\nbuilds",
                "Build count\ncomparison",
                "Missing build IDs",
                "Builds with\nstatus mismatch",
            ]
            max_col_width = [None, 40, 3, 3, 2, 30, 30]
        table_fmt = "simple_grid"
        if table_output:
            print_table_stats(final_stats, headers, max_col_width, table_fmt)
        else:
            print_simple_list(final_stats, "builds", history)
    if fail_on_mismatch:
        report = validation_rows_to_json(
            "builds", final_stats, history, origin, days, arch
        )
        if not report["summary"]["ok"]:
            ctx.exit(1)
