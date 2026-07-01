#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import contextlib
import sys
from functools import wraps

import click
import requests


class ToolExecutionError(Exception):
    """Raised when a KernelCI API call behind an MCP tool fails."""


def tool_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with contextlib.redirect_stdout(sys.stderr):
            try:
                return func(*args, **kwargs)
            except click.ClickException as e:
                raise ToolExecutionError(e.format_message()) from e
            except click.Abort as e:
                raise ToolExecutionError("KernelCI API request failed") from e
            except SystemExit as e:
                raise ToolExecutionError("KernelCI API request failed") from e
            except requests.exceptions.RequestException as e:
                raise ToolExecutionError(str(e)) from e

    return wrapper
