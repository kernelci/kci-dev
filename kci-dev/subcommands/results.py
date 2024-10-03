#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pprint

import click
import requests
import toml
from git import Repo


def api_connection(host):
    click.secho("api connect: " + host, fg="green")
    return host


def get_node(url, nodeid):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    url = url + "/node/" + nodeid
    click.secho(url)
    response = requests.get(url, headers=headers)
    click.secho(response.status_code, fg="green")
    try:
        click.secho(pprint.pprint(response.json()), fg="green")
    except:
        click.secho(pprint.pprint(response.text), fg="green")


def get_nodes(url, limit, offset):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    url = url + "/nodes?limit=" + str(limit) + "&offset=" + str(offset)
    click.secho(url)
    response = requests.get(url, headers=headers)
    click.secho(response.status_code, fg="green")
    try:
        click.secho(pprint.pprint(response.json()), fg="green")
    except:
        click.secho(pprint.pprint(response.text), fg="green")


@click.command(help="Get results")
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
@click.pass_context
def results(ctx, nodeid, nodes, limit, offset):
    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = api_connection(config[instance]["host"])
    if nodeid:
        get_node(url, nodeid)
    if nodes:
        get_nodes(url, limit, offset)


if __name__ == "__main__":
    main_kcidev()
