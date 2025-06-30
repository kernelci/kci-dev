import sys

import click

from kcidev.subcommands.detect.issues import issues


@click.group(
    help="""Detect dashboard issues for builds and boots

\b
Subcommands:
  issues - Fetch KCIDB issues for builds/boots

\b
Examples:
  # Detect build issues
  kci-dev detect issues --builds --id <build-id>
  kci-dev detect issues --builds --all-checkouts --days <number-of-days> --origin <origin>
  # Detect boot issues
  kci-dev detect issues --boots --id <boot-id>
  kci-dev detect issues --boots --all-checkouts --days <number-of-days> --origin <origin>
""",
    invoke_without_command=True,
)
@click.pass_context
def detect(ctx):
    """Commands related to results validation"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        sys.exit(0)


# Add subcommands to the detect group
detect.add_command(issues)


if __name__ == "__main__":
    main_kcidev()
