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


def print_nodes(nodes, field):
    if not isinstance(nodes, list):
        nodes = [nodes]
    for node in nodes:
        if field:
            data = {}
            for f in field:
                data[f] = node.get(f)
            click.secho(pprint.pprint(data), fg="green", nl=False)
        else:
            click.secho(pprint.pprint(node), fg="green", nl=False)


def get_node(url, nodeid, field):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    url = url + "latest/node/" + nodeid
    click.secho(url)
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        click.secho(ex.response.json().get("detail"), fg="red")
        return None
    except Exception as ex:
        click.secho(ex, fg="red")
        return None
    print_nodes(response.json(), field)


def get_nodes(url, limit, offset, filter, field):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    url = url + "latest/nodes/fast?limit=" + str(limit) + "&offset=" + str(offset)
    if filter:
        for f in filter:
            # TBD: We need to add translate filter to API
            # if we need anything more complex than eq(=)
            url = url + "&" + f

    click.secho(url)
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        click.secho(ex.response.json().get("detail"), fg="red")
        return None
    except Exception as ex:
        click.secho(ex, fg="red")
        return None

    nodes = response.json()
    print_nodes(nodes, field)


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
def results(ctx, nodeid, nodes, limit, offset, filter, field):
    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = api_connection(config[instance]["api"])
    if nodeid:
        get_node(url, nodeid, field)
    if nodes:
        get_nodes(url, limit, offset, filter, field)


if __name__ == "__main__":
    main_kcidev()
