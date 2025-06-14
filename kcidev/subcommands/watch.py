#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import click

from kcidev.libs.common import *
from kcidev.libs.maestro_common import *


@click.command(
    help="""Watch and monitor the completion of test jobs in real-time.

This command allows you to track the progress of a test run by providing a
node ID. It will continuously poll for updates and display the status of jobs
as they complete. You can filter which jobs to watch and optionally check for
specific test results.

The command is useful for monitoring long-running test suites or when you need
to know immediately when specific tests complete.

\b
Examples:
  # Watch all jobs for a given node
  kci-dev watch --nodeid 65a5c89f1234567890abcdef

  # Watch only specific job types
  kci-dev watch --nodeid 65a5c89f1234567890abcdef \\
                --job-filter baseline --job-filter ltp

  # Watch and return exit code based on specific test result
  kci-dev watch --nodeid 65a5c89f1234567890abcdef \\
                --job-filter baseline --test baseline.login
"""
)
@click.option(
    "--nodeid",
    help="Node ID of the test run to watch (obtained from checkout or test results)",
    required=True,
)
@click.option(
    "--job-filter",
    help="Filter jobs to watch by name (e.g., baseline, ltp). Can be used multiple times",
    multiple=True,
)
@click.option(
    "--test",
    help="Watch for specific test result and set exit code (0=pass, 1=fail)",
)
@click.pass_context
def watch(ctx, nodeid, job_filter, test):
    logging.info(f"Starting watch command for node {nodeid}")
    if job_filter:
        logging.debug(f"Job filters: {job_filter}")
    if test:
        logging.debug(f"Watching for test: {test}")

    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = cfg[instance]["pipeline"]
    apiurl = cfg[instance]["api"]
    token = cfg[instance]["token"]

    logging.debug(f"Using instance: {instance}")
    logging.debug(f"API URL: {apiurl}")

    logging.info(f"Fetching node details for {nodeid}")
    node = maestro_get_node(apiurl, nodeid)
    if not node:
        logging.error(f"Node {nodeid} not found")
        kci_err(f"node id {nodeid} not found.")
        sys.exit(errno.ENOENT)

    tree_id = node["treeid"]
    logging.info(f"Found node {nodeid} with tree ID: {tree_id}")
    logging.info(f"Starting job watch for tree {tree_id}")

    maestro_watch_jobs(apiurl, token, tree_id, job_filter, test)


if __name__ == "__main__":
    main_kcidev()
