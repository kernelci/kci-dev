#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import click

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
