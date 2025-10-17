#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys

import click
from git import Repo

from kcidev.libs.common import *
from kcidev.libs.filter_options import add_filter_options
from kcidev.libs.maestro_common import *


@click.command(
    name="results",
    help="""Query test results from KernelCI's Maestro API.

This command allows you to retrieve test results either by specific node ID
or by fetching the latest nodes with pagination and filtering options.

\b
Examples:
  kci-dev maestro results --nodeid <NODE_ID>
  kci-dev maestro results --nodes --limit 10
  kci-dev maestro results --nodes --filter "status=fail"
  kci-dev maestro results --nodes --field name --field status
""",
)
@click.option(
    "--nodeid",
    required=False,
    help="Retrieve results for a specific node ID",
)
@click.option(
    "--nodes",
    is_flag=True,
    required=False,
    help="Retrieve the latest test node results",
)
@click.option(
    "--limit",
    default=50,
    required=False,
    help="Maximum number of nodes to retrieve (default: 50)",
)
@click.option(
    "--offset",
    default=0,
    required=False,
    help="Starting position for pagination (default: 0)",
)
@click.option(
    "--filter",
    required=False,
    multiple=True,
    help="Filter nodes by conditions (e.g., 'status=fail', 'name=test_*'). Can be used multiple times",
)
@click.option(
    "--field",
    required=False,
    multiple=True,
    help="Display only specific field(s) from node data (e.g., 'name', 'status'). Can be used multiple times",
)
@click.option(
    "--tree",
    required=False,
    help="Filter results by tree name",
)
@click.option(
    "--count",
    is_flag=True,
    required=False,
    help="Print only count of nodes",
)
@click.option(
    "--paginate",
    is_flag=True,
    required=False,
    default=True,
    help="Set True if pagination is required in the output. Default is True",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=True,
    help="Print results on stdout",
)
@add_filter_options
@click.pass_context
def results(
    ctx,
    nodeid,
    nodes,
    limit,
    offset,
    filter,
    field,
    tree,
    status,
    start_date,
    end_date,
    compiler,
    config,
    git_branch,
    count,
    paginate,
    verbose,
):
    logging.info("Starting maestro results command")
    logging.debug(
        f"Parameters - nodeid: {nodeid}, nodes: {nodes}, limit: {limit}, offset: {offset}"
    )
    logging.debug(
        f"Filters - tree: {tree}, status: {status}, dates: {start_date} to {end_date}"
    )

    config_data = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = config_data[instance]["api"]

    logging.debug(f"Using instance: {instance}")
    logging.debug(f"API URL: {url}")

    if not nodeid and not nodes:
        logging.debug("No nodeid or nodes flag provided, showing help")
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        sys.exit(0)

    if nodeid:
        logging.info(f"Fetching single node: {nodeid}")
        results = maestro_get_node(url, nodeid)

    if nodes:
        # Add tree filter if provided
        filter = list(filter) if filter else []

        if tree:
            filter.append(f"data.kernel_revision.tree::{tree}")
            logging.debug(f"Added tree filter: {tree}")
        if start_date:
            filter.append(f"created__gte={start_date}")
            logging.debug(f"Added start date filter: {start_date}")
        if end_date:
            filter.append(f"created__lte={end_date}")
            logging.debug(f"Added end date filter: {end_date}")

        logging.info(
            f"Fetching nodes with {len(filter)} filters, limit: {limit}, offset: {offset}"
        )
        results = maestro_get_nodes(url, limit, offset, filter, paginate)
        if count:
            kci_msg(len(results))

    logging.debug(f"Displaying results with fields: {field if field else 'all'}")

    if verbose:
        maestro_print_nodes(results, field)
    return results


if __name__ == "__main__":
    main_kcidev()
