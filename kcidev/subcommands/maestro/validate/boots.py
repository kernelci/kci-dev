import click

from kcidev.libs.git_repo import get_tree_name, set_giturl_branch_commit
from kcidev.subcommands.results import trees

from .helper import get_boot_stats, print_simple_list, print_table_stats


@click.command(
    name="boots",
    help="""Validate dashboard boot results with maestro.

Provide --all-checkouts flag to pull all boot results of available
checkouts from dashboard and compare them with from maestro.
It supports --days option to specify number of days to get results for.

Boot validation for a specific checkout can be performed by
using all three options: --giturl, --branch, and --commit
If above options are not provided, if will take latest/provided commit
checkout from the git folder specified.

\b
Examples:
    kci-dev maestro validate boots --all-checkouts --days <number-of-days>
    kci-dev maestro validate boots -commit <git-commit> --giturl <git-url> --branch <git-branch>
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
    "--verbose",
    is_flag=True,
    default=False,
    help="Get detailed output",
)
@click.option(
    "--table-output",
    is_flag=True,
    default=False,
    help="Display results in table format",
)
@click.pass_context
def boots(
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
    verbose,
    table_output,
):
    final_stats = []
    print("Fetching boot information...")
    if all_checkouts:
        if giturl or branch or commit:
            raise click.UsageError(
                "Cannot use --all-checkouts with --giturl, --branch, or --commit"
            )
        trees_list = ctx.invoke(trees, origin=origin, days=days, verbose=False)
        for tree in trees_list:
            giturl = tree["git_repository_url"]
            branch = tree["git_repository_branch"]
            commit = tree["git_commit_hash"]
            tree_name = tree["tree_name"]
            stats = get_boot_stats(
                ctx, giturl, branch, commit, tree_name, verbose, arch
            )
            if stats:
                final_stats.append(stats)
    else:
        giturl, branch, commit = set_giturl_branch_commit(
            origin, giturl, branch, commit, latest, git_folder
        )
        tree_name = get_tree_name(origin, giturl, branch)
        stats = get_boot_stats(ctx, giturl, branch, commit, tree_name, verbose, arch)
        if stats:
            final_stats.append(stats)
    if final_stats:
        headers = [
            "tree/branch",
            "Commit",
            "Maestro\nboots",
            "Dashboard\nboots",
            "Boot count\ncomparison",
            "Missing boot IDs",
            "Boots with\nstatus mismatch",
        ]
        max_col_width = [None, 40, 3, 3, 2, 30, 30]
        table_fmt = "simple_grid"
        if table_output:
            print_table_stats(final_stats, headers, max_col_width, table_fmt)
        else:
            print_simple_list(final_stats, "boots", False)
