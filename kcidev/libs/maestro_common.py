#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import click

from kcidev.libs.common import *


def maestro_print_api_call(host, data=None):
    click.secho("maestro api endpoint: " + host, fg="green")
    if data:
        kci_log(json.dumps(data, indent=4))
