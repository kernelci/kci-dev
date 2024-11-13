#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import toml


def load_toml(settings):
    fname = "kci-dev.toml"
    config = None

    global_path = os.path.join("/", "etc", fname)
    if os.path.exists(global_path):
        with open(global_path, "r") as f:
            config = toml.load(f)

    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, ".config", "kci-dev", fname)
    if os.path.exists(user_path):
        with open(user_path, "r") as f:
            config = toml.load(f)

    if os.path.exists(settings):
        with open(settings, "r") as f:
            config = toml.load(f)

    if not config:
        raise FileNotFoundError("No configuration file found")

    return config
