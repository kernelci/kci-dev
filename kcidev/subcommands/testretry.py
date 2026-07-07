#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import click
from git import Repo

from kcidev.libs.common import *
from kcidev.libs.maestro_common import *


@click.command(
    help="""Retry a failed or incomplete test job on KernelCI.

This command allows you to rerun a specific test job by providing its node ID.
This is useful when a test fails due to infrastructure issues, timeouts, or
other transient problems that might be resolved on a retry.

The node ID can be obtained from test results or from the KernelCI dashboard.

\b
Examples:
    kci-dev testretry --nodeid 65a5c89f1234567890abcdef
    # If the user doesn't know the node id, they can query it using maestro results command
    # for example, for failed tests:
    kci-dev maestro results --nodes --filter "status=fail" --field id --field name
    kci-dev testretry --nodeid <NODE_ID_FROM_ABOVE>
"""
)
@click.option(
    "--nodeid",
    help="Node ID of the test job to retry (obtained from test results)",
    required=True,
)
@click.pass_context
def testretry(ctx, nodeid):
    logging.info(f"Starting testretry command for node: {nodeid}")

    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = cfg[instance]["pipeline"]

    logging.debug(f"Using instance: {instance}")
    logging.debug(f"Pipeline URL: {url}")

    resp = send_jobretry(url, nodeid, cfg[instance]["token"])
    if resp and "message" in resp:
        logging.info("Test retry initiated successfully")
        click.secho(resp["message"], fg="green")
    else:
        logging.warning("No response message from retry request")


if __name__ == "__main__":
    main_kcidev()
