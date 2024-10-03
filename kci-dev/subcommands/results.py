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


def get_nodes(url):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    url = url + "/nodes"
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
    required=False,
    help="Get last nodes results",
)
@click.pass_context
def results(ctx, nodeid, nodes):
    config = ctx.obj.get("CFG")
    instance = ctx.obj.get("INSTANCE")
    url = api_connection(config[instance]["host"])
    if nodeid:
        get_node(url, nodeid)
    if nodes:
        get_nodes(url)


if __name__ == "__main__":
    main_kcidev()
