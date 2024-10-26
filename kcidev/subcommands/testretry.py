#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import click
import requests
from git import Repo

from kcidev.libs.common import *


def api_connection(host):
    click.secho("api connect: " + host, fg="green")
    return host


def display_api_error(response):
    click.secho(f"API response error code: {response.status_code}", fg="red")
    try:
        click.secho(response.json(), fg="red")
    except json.decoder.JSONDecodeError:
        click.secho(f"No JSON response. Plain text: {response.text}", fg="yellow")
    return


def send_jobretry(baseurl, jobid, token):
    url = baseurl + "api/jobretry"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"{token}",
    }
    data = {"nodeid": jobid}
    jdata = json.dumps(data)
    try:
        response = requests.post(url, headers=headers, data=jdata)
    except requests.exceptions.RequestException as e:
        click.secho(f"API connection error: {e}", fg="red")
        return

    if response.status_code != 200:
        display_api_error(response)
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
    url = api_connection(cfg[instance]["pipeline"])
    resp = send_jobretry(url, nodeid, cfg[instance]["token"])
    if resp and "message" in resp:
        click.secho(resp["message"], fg="green")


if __name__ == "__main__":
    main_kcidev()
