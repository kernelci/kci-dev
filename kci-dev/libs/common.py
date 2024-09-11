#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import toml


def load_toml(settings):
    with open(settings) as fp:
        config = toml.load(fp)
    return config
