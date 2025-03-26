from functools import wraps

import click


def results_display_options(func):
    @click.option("--json", "use_json", is_flag=True, help="Displays results as json")
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def common_options(func):
    @click.option(
        "--origin",
        help="Select KCIDB origin",
        default="maestro",
    )
    @click.option(
        "--giturl",
        help="Git URL of kernel tree ",
    )
    @click.option(
        "--branch",
        help="Branch to get results for",
    )
    @click.option(
        "--git-folder",
        help="Path of git repository folder",
    )
    @click.option(
        "--commit",
        help="Commit or tag to get results for",
    )
    @click.option(
        "--latest",
        is_flag=True,
        help="Select latest results available",
    )
    @click.option("--arch", help="Filter by arch")
    @results_display_options
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def builds_and_tests_options(func):
    @click.option(
        "--download-logs",
        is_flag=True,
        help="Select desired results action",
    )
    @click.option(
        "--status",
        type=click.Choice(["all", "pass", "fail", "inconclusive"], case_sensitive=True),
        help="Status of test result",
        default="all",
    )
    @click.option(
        "--filter",
        type=click.File("r"),
        help="Pass filter file for builds, boot and tests results.",
    )
    @click.option(
        "--count", is_flag=True, help="Display the number of matching results"
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def single_build_and_test_options(func):
    @click.option(
        "--id",
        "op_id",
        required=True,
        help="Pass an id filter to get specific results",
    )
    @click.option(
        "--download-logs",
        is_flag=True,
        help="Select desired results action",
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
