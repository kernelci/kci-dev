#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import toml


def load_toml(settings):
    if not settings:
        if os.path.exists(".kci-dev.toml"):
            settings = ".kci-dev.toml"
        else:
            homedir = os.path.expanduser("~")
            settings = os.path.join(homedir, ".config", "kci-dev.toml")
    if not os.path.exists(settings):
        raise FileNotFoundError(f"Settings file {settings} not found")
    with open(settings) as fp:
        config = toml.load(fp)
    return config
