#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click

from kcidev.libs.common import *
from kcidev.libs.maestro_common import *


@click.command(help="Watch completion of a test job")
@click.option(
    "--nodeid",
    help="define the node id of the job to watch for",
    required=True,
)
@click.option(
    "--job-filter",
    help="Job filter to trigger",
    multiple=True,
)
@click.option(
    "--test",
    help="Return 0 if the test name supplied passed, 1 otherwise",
)
@click.pass_context
def watch(ctx, nodeid, job_filter, test):
    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = cfg[instance]["pipeline"]
    apiurl = cfg[instance]["api"]
    token = cfg[instance]["token"]

    node = maestro_get_node(apiurl, nodeid)
    if not node:
        kci_err(f"node id {nodeid} not found.")
        sys.exit(errno.ENOENT)
    maestro_watch_jobs(apiurl, token, node["treeid"], job_filter, test)


if __name__ == "__main__":
    main_kcidev()
