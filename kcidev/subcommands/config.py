#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import shutil

import click

from kcidev.libs.common import *


def check_configuration(settings):
    fname = "kci-dev.toml"
    logging.debug(f"Checking for existing configuration files")

    if os.path.exists(settings):
        logging.warning(f"Config file already exists at: {settings}")
        kci_err("Config file already present at: " + settings)
        raise click.Abort()

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    if os.path.exists(user_path):
        logging.warning(f"Config file already exists at: {user_path}")
        kci_err("Config file already present at: " + user_path)
        raise click.Abort()

    global_path = os.path.join("/", "etc", fname)
    if os.path.exists(global_path):
        logging.warning(f"Config file already exists at: {global_path}")
        kci_err("Config file already present at: " + global_path)
        raise click.Abort()

    logging.debug("No existing configuration files found")


def add_config(fpath):
    config = None
    example_configuration = ".kci-dev.toml.example"
    fpath = os.path.expandvars(fpath)
    fpath = os.path.expanduser(fpath)
    fpath = os.path.join(fpath)
    dpath = os.path.dirname(fpath)

    logging.info(f"Adding configuration file to: {fpath}")

    if os.path.isdir(fpath) or fpath.endswith(os.sep):
        logging.error(f"Target path is a directory: {fpath}")
        kci_err(fpath + " is a directory and not a config file")
        raise click.Abort()

    if os.path.exists(fpath):
        logging.error(f"Config file already exists: {fpath}")
        kci_err("A config file already exist at: " + fpath)
        raise click.Abort()

    kci_msg("Config file not present, adding a config file to " + fpath)
    # Installed with Poetry
    poetry_example_configuration = os.path.join(
        os.path.dirname(__file__), "../..", example_configuration
    )
    poetry_example_configuration = os.path.normpath(poetry_example_configuration)
    logging.debug(f"Checking for Poetry template at: {poetry_example_configuration}")
    if os.path.isfile(poetry_example_configuration):
        logging.info(f"Found Poetry template configuration")
        config = True
        if not os.path.exists(dpath) and dpath != "":
            # copy config
            logging.debug(f"Creating directory: {dpath}")
            os.makedirs(dpath)
        logging.info(f"Copying template configuration to: {fpath}")
        shutil.copyfile(poetry_example_configuration, fpath)

    # Installed with PyPI
    pypi_example_configuration = os.path.join(
        os.path.dirname(__file__), "..", example_configuration
    )
    pypi_example_configuration = os.path.normpath(pypi_example_configuration)
    logging.debug(f"Checking for PyPI template at: {pypi_example_configuration}")
    if os.path.isfile(pypi_example_configuration):
        logging.info(f"Found PyPI template configuration")
        config = True
        if not os.path.exists(dpath) and dpath != "":
            # copy config
            logging.debug(f"Creating directory: {dpath}")
            os.makedirs(dpath)
        logging.info(f"Copying template configuration to: {fpath}")
        shutil.copyfile(pypi_example_configuration, fpath)

    if not config:
        logging.error("No template configuration file found")
        logging.error(f"Searched at: {poetry_example_configuration}")
        logging.error(f"Searched at: {pypi_example_configuration}")
        kci_err(f"No template configfile found at:")
        kci_err(poetry_example_configuration)
        kci_err(pypi_example_configuration)
        raise click.Abort()
    else:
        logging.info(f"Configuration file successfully created at: {fpath}")


@click.command(
    help="""Create a configuration file for kci-dev.

This command helps you set up a configuration file by copying a template
configuration to your specified location. The configuration file contains
settings for connecting to KernelCI instances, including API URLs and tokens.

The command will check for existing configuration files in standard locations
and prevent overwriting them. If no file path is specified, it will create
the config at ~/.config/kci-dev/kci-dev.toml.

\b
Examples:
  # Create config at default location
  kci-dev config

  # Create config at custom location
  kci-dev config --file-path ~/my-kci-config.toml

  # Create config in current directory
  kci-dev config --file-path ./kci-dev.toml
"""
)
@click.option(
    "--file-path",
    default="~/.config/kci-dev/kci-dev.toml",
    help="Path where the config file will be created (default: ~/.config/kci-dev/kci-dev.toml)",
    type=click.Path(),
)
@click.pass_context
def config(
    ctx,
    file_path,
):
    logging.info("Starting config command")
    logging.debug(f"Target file path: {file_path}")

    settings = ctx.obj.get("SETTINGS")
    logging.debug(f"Current settings file: {settings}")

    check_configuration(settings)
    add_config(file_path)


if __name__ == "__main__":
    main_kcidev()
