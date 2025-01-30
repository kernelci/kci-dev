#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import click
import requests

from kcidev.libs.common import *


def maestro_print_api_call(host, data=None):
    click.secho("maestro api endpoint: " + host, fg="green")
    if data:
        kci_log(json.dumps(data, indent=4))


def maestro_api_error(response):
    kci_err(f"API response error code: {response.status_code}")
    try:
        kci_err(response.json())
    except json.decoder.JSONDecodeError:
        kci_warning(f"No JSON response. Plain text: {response.text}")
    except Exception as e:
        kci_err(f"API response error: {e}: {response.text}")
    return


def maestro_print_nodes(nodes, field):
    res = []
    if not isinstance(nodes, list):
        nodes = [nodes]
    for node in nodes:
        if field:
            data = {}
            for f in field:
                data[f] = node.get(f)
            res.append(data)
        else:
            res.append(node)
        kci_msg(json.dumps(res, sort_keys=True, indent=4))


def maestro_get_node(url, nodeid):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    url = url + "latest/node/" + nodeid
    maestro_print_api_call(url)
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        kci_err(ex.response.json().get("detail"))
        return None
    except Exception as ex:
        kci_err(ex)
        return None

    return response.json()


def maestro_get_nodes(url, limit, offset, filter):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    url = url + "latest/nodes/fast?limit=" + str(limit) + "&offset=" + str(offset)
    maestro_print_api_call(url)
    if filter:
        for f in filter:
            # TBD: We need to add translate filter to API
            # if we need anything more complex than eq(=)
            url = url + "&" + f

    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        kci_err(ex.response.json().get("detail"))
        return None
    except Exception as ex:
        kci_err(ex)
        return None

    return response.json()
