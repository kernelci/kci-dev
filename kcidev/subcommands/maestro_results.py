#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from git import Repo

from kcidev.libs.common import *
from kcidev.libs.maestro_common import *


@click.command(help="Get results directly from KernelCI's Maestro")
@click.option(
    "--nodeid",
    required=False,
    help="select node_id",
)
@click.option(
    "--nodes",
    is_flag=True,
    required=False,
    help="Get last nodes results",
)
@click.option(
    "--limit",
    default=50,
    required=False,
    help="Pagination limit for nodes",
)
@click.option(
    "--offset",
    default=0,
    required=False,
    help="Offset of the pagination",
)
@click.option(
    "--filter",
    required=False,
    multiple=True,
    help="Filter nodes by conditions",
)
@click.option(
    "--field",
    required=False,
    multiple=True,
    help="Print only particular field(s) from node data",
)
@click.pass_context
def maestro_results(ctx, nodeid, nodes, limit, offset, filter, field):
    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = config[instance]["api"]
    if not nodeid and not nodes:
        kci_err("--nodes or --nodes needs to be supplied")
        sys.exit(-1)
    if nodeid:
        results = maestro_get_node(url, nodeid)
    if nodes:
        results = maestro_get_nodes(url, limit, offset, filter)
    maestro_print_nodes(results, field)


if __name__ == "__main__":
    main_kcidev()
