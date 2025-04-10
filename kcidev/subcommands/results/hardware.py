from functools import wraps

import click

from kcidev.libs.dashboard import (
    dashboard_fetch_hardware_boots,
    dashboard_fetch_hardware_builds,
    dashboard_fetch_hardware_list,
    dashboard_fetch_hardware_summary,
    dashboard_fetch_hardware_tests,
)
from kcidev.subcommands.results.options import (
    builds_and_tests_options,
    results_display_options,
)
from kcidev.subcommands.results.parser import (
    cmd_builds,
    cmd_hardware_list,
    cmd_summary,
    cmd_tests,
)


def hardware_common_opt(func):
    @click.option("--name", required=True, help="Name of the hardware")
    @click.option("--origin", default="maestro", help="Select KCIDB origin")
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


@click.group(chain=True, help="Get hardware related information from the dashboard")
def hardware():
    """Commands related to hardware"""
    pass


@hardware.command()
@click.option("--origin", default="maestro", help="Select KCIDB origin")
@results_display_options
def list(origin, use_json):
    data = dashboard_fetch_hardware_list(origin, use_json)
    cmd_hardware_list(data, use_json)


@hardware.command()
@hardware_common_opt
@results_display_options
def summary(name, origin, use_json):
    data = dashboard_fetch_hardware_summary(name, origin, use_json)
    cmd_summary(data, use_json)


@hardware.command()
@hardware_common_opt
@results_display_options
@builds_and_tests_options
def boots(name, origin, use_json, download_logs, status, filter, count):
    data = dashboard_fetch_hardware_boots(name, origin, use_json)
    cmd_tests(data["boots"], name, download_logs, status, filter, count, use_json)


@hardware.command()
@hardware_common_opt
@results_display_options
@builds_and_tests_options
def builds(name, origin, use_json, download_logs, status, filter, count):
    data = dashboard_fetch_hardware_builds(name, origin, use_json)
    cmd_builds(data, name, download_logs, status, count, use_json)


@hardware.command()
@hardware_common_opt
@results_display_options
@builds_and_tests_options
def tests(name, origin, use_json, download_logs, status, filter, count):
    data = dashboard_fetch_hardware_tests(name, origin, use_json)
    cmd_tests(data["tests"], name, download_logs, status, filter, count, use_json)
