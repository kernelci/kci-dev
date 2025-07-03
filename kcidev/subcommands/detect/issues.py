import click

from kcidev.subcommands.detect.helper import (
    get_issues,
    get_issues_for_specific_item,
    print_stats,
)
from kcidev.subcommands.results import trees


@click.command(
    name="issues",
    help="""Detect KCIDB issues for builds and boots

\b
The command is used to fetch KCIDB issues associated with builds and boots.
Provide `--builds` and `--boots` option for builds issue detection and boots
issue detection respectively.
`--all-checkouts` option can be used to fetch KCIDB issues for all the
failed and inconclusive builds/boots from all available trees on the dashboard.
Issues for a single build/boot can be retrieved by providing `--id`
option.
  
\b
Examples:
  # Detect build issues
  kci-dev detect issues --builds --id <build-id>
  kci-dev detect issues --builds --all-checkouts --days <number-of-days> --origin <origin>
  # Detect boot issues
  kci-dev detect issues --boots --id <boot-id>
  kci-dev detect issues --boots --all-checkouts --days <number-of-days> --origin <origin>
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
@click.pass_context
def issues(
    ctx,
    origin,
    builds,
    boots,
    item_id,
    all_checkouts,
    arch,
    days,
):

    if not (builds or boots):
        raise click.UsageError("Provide --builds or --boots to fetch issues for")

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
