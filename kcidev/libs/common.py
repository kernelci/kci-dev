#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import click
import toml


def load_toml(settings, subcommand):
    fname = "kci-dev.toml"
    config = None

    if os.path.exists(settings):
        if os.path.isfile(settings):
            with open(settings, "r") as f:
                config = toml.load(f)
        else:
            kci_err("The --settings location is not a kci-dev config file")
            raise click.Abort()
        return config

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    if os.path.exists(user_path):
        with open(user_path, "r") as f:
            config = toml.load(f)
        return config

    global_path = os.path.join("/", "etc", fname)
    if os.path.exists(global_path):
        with open(global_path, "r") as f:
            config = toml.load(f)
        return config

    example_configuration = ".kci-dev.toml.example"
    # Installed with Poetry
    poetry_example_configuration = os.path.join(
        os.path.dirname(__file__), "../..", example_configuration
    )
    if os.path.exists(poetry_example_configuration):
        if subcommand != "config":
            kci_err(f"Please use `kci-dev config` to create a config file")
        with open(poetry_example_configuration, "r") as f:
            config = toml.load(f)
        return config

    # Installed with PyPI
    kci_err(f"Configuration not found")
    pypi_example_configuration = os.path.join(
        os.path.dirname(__file__), "..", example_configuration
    )
    if os.path.exists(pypi_example_configuration):
        if subcommand != "config":
            kci_err(f"Please use `kci-dev config` to create a config file")
        with open(pypi_example_configuration, "r") as f:
            config = toml.load(f)
        return config

    if not config:
        kci_err(
            f"No `{fname}` configuration file found at `{global_path}`, `{user_path}` or `{settings}`"
        )
        raise click.Abort()

    return config


def config_path(settings):
    fname = "kci-dev.toml"

    if os.path.exists(settings):
        return settings

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    if os.path.exists(user_path):
        return user_path

    global_path = os.path.join("/", "etc", fname)
    if os.path.exists(global_path):
        return global_path


def kci_msg(content):
    click.echo(content)


def kci_err(content):
    click.secho(content, fg="red", err=True)


def kci_msg_nonl(content):
    click.echo(content, nl=False)


def kci_msg_green_nonl(content):
    click.secho(content, fg="green", nl=False)


def kci_msg_red_nonl(content):
    click.secho(content, fg="red", nl=False)


def kci_msg_yellow_nonl(content):
    click.secho(content, fg="bright_yellow", nl=False)


def kci_msg_cyan_nonl(content):
    click.secho(content, fg="cyan", nl=False)
