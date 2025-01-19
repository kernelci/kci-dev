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


@click.command(help="Retry a test(job) on KernelCI")
@click.option(
    "--nodeid",
    help="define the node id of the (test)job to retry",
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
