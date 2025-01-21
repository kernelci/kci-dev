#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil

import click

from kcidev.libs.common import *


def check_configuration(settings):
    fname = "kci-dev.toml"

    if os.path.exists(settings):
        kci_err("Config file already present at: " + settings)
        raise click.Abort()

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    if os.path.exists(user_path):
        kci_err("Config file already present at: " + user_path)
        raise click.Abort()

    global_path = os.path.join("/", "etc", fname)
    if os.path.exists(global_path):
        kci_err("Config file already present at: " + global_path)
        raise click.Abort()


def add_config(fpath):
    config = None
    example_configuration = ".kci-dev.toml.example"
    fpath = os.path.expandvars(fpath)
    fpath = os.path.expanduser(fpath)
    fpath = os.path.join(fpath)
    dpath = os.path.dirname(fpath)

    if os.path.isdir(fpath) or fpath.endswith(os.sep):
        kci_err(fpath + " is a directory and not a config file")
        raise click.Abort()

    if os.path.exists(fpath):
        kci_err("A config file already exist at: " + fpath)
        raise click.Abort()

    kci_msg("Config file not present, adding a config file to " + fpath)
    # Installed with Poetry
    poetry_example_configuration = os.path.join(
        os.path.dirname(__file__), "../..", example_configuration
    )
    poetry_example_configuration = os.path.normpath(poetry_example_configuration)
    if os.path.isfile(poetry_example_configuration):
        kci_msg("here1")
        config = True
        if not os.path.exists(dpath) and dpath != "":
            # copy config
            os.makedirs(dpath)
        shutil.copyfile(poetry_example_configuration, fpath)

    # Installed with PyPI
    pypi_example_configuration = os.path.join(
        os.path.dirname(__file__), "..", example_configuration
    )
    pypi_example_configuration = os.path.normpath(pypi_example_configuration)
    if os.path.isfile(pypi_example_configuration):
        kci_msg("here2")
        config = True
        if not os.path.exists(dpath) and dpath != "":
            # copy config
            os.makedirs(dpath)
        shutil.copyfile(pypi_example_configuration, fpath)

    if not config:
        kci_err(f"No template configfile found at:")
        kci_err(poetry_example_configuration)
        kci_err(pypi_example_configuration)
        raise click.Abort()


@click.command(help="Config tool for creating a config file")
@click.option(
    "--file-path",
    default="~/.config/kci-dev/kci-dev.toml",
    help="File path for creating a config file, if none is provided ~/config/kci-dev/kci-dev.toml is used",
)
@click.pass_context
def config(
    ctx,
    file_path,
):
    settings = ctx.obj.get("SETTINGS")
    check_configuration(settings)
    add_config(file_path)


if __name__ == "__main__":
    main_kcidev()
