#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import click
import requests
from git import Repo

from kcidev.libs.common import *
from kcidev.libs.maestro_common import *


def send_jobretry(baseurl, jobid, token):
    url = baseurl + "api/jobretry"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"{token}",
    }
    data = {"nodeid": jobid}
    jdata = json.dumps(data)
    maestro_print_api_call(url, data)
    try:
        response = requests.post(url, headers=headers, data=jdata)
    except requests.exceptions.RequestException as e:
        kci_err(f"API connection error: {e}")
        return

    if response.status_code != 200:
        maestro_api_error(response)
        return None
    return response.json()


@click.command(
    help="""Retry a failed or incomplete test job on KernelCI.

This command allows you to rerun a specific test job by providing its node ID.
This is useful when a test fails due to infrastructure issues, timeouts, or
other transient problems that might be resolved on a retry.

The node ID can be obtained from test results or from the KernelCI dashboard.

\b
Examples:
  # Retry a test job using its node ID
  kci-dev testretry --nodeid 65a5c89f1234567890abcdef

  # Get node ID from maestro-results and retry
  kci-dev maestro-results --nodes --filter "status=fail" --field id --field name
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
    cfg = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = cfg[instance]["pipeline"]
    resp = send_jobretry(url, nodeid, cfg[instance]["token"])
    if resp and "message" in resp:
        click.secho(resp["message"], fg="green")


if __name__ == "__main__":
    main_kcidev()
