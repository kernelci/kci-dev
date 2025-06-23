#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

import click

from kcidev.subcommands.maestro.results import results


@click.group(
    help="""Maestro-specific commands for interacting with KernelCI's Maestro API.

This command group provides access to various Maestro operations including
querying test results and in the future will include other maestro-specific
commands.

\b
Available subcommands:
  results   - Query test results from Maestro API

\b
Examples:
  # Query test results
  kci-dev maestro results --nodeid <NODE_ID>
  kci-dev maestro results --nodes --limit 10
""",
    invoke_without_command=True,
)
@click.pass_context
def maestro(ctx):
    """Maestro-specific commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        sys.exit(0)


# Add subcommands to the maestro group
maestro.add_command(results)


if __name__ == "__main__":
    from kcidev.libs.common import main_kcidev

    main_kcidev()
