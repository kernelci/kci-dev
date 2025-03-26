import click
from libs.dashboard import dashboard_fetch_hardware_list
from subcommands.results.options import results_display_options
from subcommands.results.parser import cmd_hardware_list


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
