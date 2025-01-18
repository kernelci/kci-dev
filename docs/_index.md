+++
title = 'kci-dev'
date = 2024-01-14T07:07:07+01:00
description = 'Tool for interact programmatically with KernelCI instances.'
+++

Stand alone tool for Linux Kernel developers and maintainers to interact with KernelCI.

Purpose of this tool to provide an easy-to-use command line tool for developers and maintainers request test from KernelCI, view results, download logs, integrate with scripts, etc.

## Installation

You may want to use python virtual environment.
If you are not familiar with it, check [this](https://docs.python.org/3/library/venv.html).

To quickly setup it:

```sh
virtualenv .venv
source .venv/bin/activate
```

### Using package from PyPI

Simply install it using `pip`:

```sh
pip install kci-dev
```

### Development snapshot through poetry

Clone the `kci-dev` repo you want, select the desired branch and run:

```sh
virtualenv .venv
source .venv/bin/activate
pip install poetry
poetry install
```

Then, to execute kci-dev:

```sh
poetry run kci-dev <options>
```

## Configuration

> Configuration is only necessary if you are using any of the Maestro Commands listed in the Maestro section.

The following command will create a config file template under `~/.config/kci-dev/kci-dev.toml`   

```sh
kci-dev config
```

For more explanation about [`kci-dev config`](config)  
For more explantiion about the [config file](config_file)

### Config file parameters

Config file `kci-dev.toml` parameters and example can be seen [here](config_file)

### Configuration options

#### --instance
You can provide the instance name to use for the command.

Example:
```sh
kci-dev --instance staging
```

#### --settings

You can provide the configuration file path to use for the command.

Example:
```sh
kci-dev --settings /path/to/.kci-dev.toml
```

### General Commands

#### results

Pull results from the Dashboard. See detailed [documentation](results).

### Maestro Commands

#### checkout

- [config](config)

#### checkout

- [checkout](checkout)

#### testretry

- [testretry](testretry)

#### maestro-results

- [maestro-results](maestro-results)

