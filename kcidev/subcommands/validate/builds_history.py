import click

from kcidev.libs.git_repo import get_tree_name
from kcidev.subcommands.results import trees

from .helper import get_builds_history_stats, print_stats


@click.command(
    name="builds-history",
    help="""Validate dashboard builds history with maestro.

The command can be used to check if number of builds is consitent
for different checkouts of the same git tree/branch.
`--days` option is used to fetch checkouts created during the mentioned days.
Default is `7` days.

\b
Examples:
    kci-dev validate builds-history --all-checkouts --days <number-of-days>
    kci-dev validate builds-history --giturl <git-url> --branch <git-branch> --days <number-of-days>
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
@click.option("--arch", help="Filter by arch")
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Get detailed output",
)
@click.pass_context
def builds_history(
    ctx,
    all_checkouts,
    origin,
    giturl,
    branch,
    arch,
    days,
    verbose,
):
    final_stats = []
    print("Fetching builds history information...")
    if all_checkouts:
        if giturl or branch:
            raise click.UsageError(
                "Cannot use --all-checkouts with --giturl or --branch"
            )
        trees_list = ctx.invoke(trees, origin=origin, days=days, verbose=False)
        for tree in trees_list:
            giturl = tree["git_repository_url"]
            branch = tree["git_repository_branch"]
            tree_name = tree["tree_name"]
            stats = get_builds_history_stats(
                ctx, giturl, branch, tree_name, arch, days, verbose
            )
            if stats:
                final_stats.extend(stats)
    else:
        tree_name = get_tree_name(origin, giturl, branch)
        final_stats = get_builds_history_stats(
            ctx, giturl, branch, tree_name, arch, days, verbose
        )
    if final_stats:
        headers = [
            "tree/branch",
            "Commit",
            "Maestro\nbuilds",
            "Dashboard\nbuilds",
            "Build count\ncomparison",
            "Missing build IDs",
        ]
        max_col_width = [None, 40, 3, 3, 2, 30]
        table_fmt = "simple_grid"
        print_stats(final_stats, headers, max_col_width, table_fmt)
