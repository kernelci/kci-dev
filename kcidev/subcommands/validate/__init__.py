import sys

import click

from kcidev.subcommands.validate.boots import boots
from kcidev.subcommands.validate.builds import builds
from kcidev.subcommands.validate.builds_history import builds_history


@click.group(
    help="""Get results from the dashboard and validate them with maestro.

\b
Subcommands:
    builds - Validate build results
    boots  - Validate boot results
    builds-history - Validate builds history

\b
Examples:
    # Validate builds
    kci-dev validate builds --all-checkouts --days <number-of-days>
    kci-dev validate builds -commit <git-commit> --giturl <git-url> --branch <git-branch>
    # Validate boots
    kci-dev validate boots --all-checkouts --days <number-of-days>
    kci-dev validate boots -commit <git-commit> --giturl <git-url> --branch <git-branch>
    # Validate builds history
    kci-dev validate builds-history --all-checkouts --days <number-of-days> --arch <architecture-filter>
    kci-dev validate builds-history -commit <git-commit> --giturl <git-url> --branch <git-branch> --days <number-of-days>
""",
    invoke_without_command=True,
)
@click.pass_context
def validate(ctx):
    """Commands related to results validation"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        sys.exit(0)


# Add subcommands to the validate group
validate.add_command(builds)
validate.add_command(boots)
validate.add_command(builds_history)


if __name__ == "__main__":
    main_kcidev()
