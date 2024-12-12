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

kci-dev searches for and loads a configuration file in the following order of priority:
1) The global configuration file located at /etc/kci-dev.toml.
2) The user-specific configuration file at ~/.config/kci-dev/kci-dev.toml
3) A site-specific configuration file, which is .kci-dev.toml by default, but can be overridden with the --settings option. 

Priority: The configuration files are loaded in the order listed above, with each subsequent file overriding the settings from the previous one.  
If a user-specific file is present, it will override the global configuration.  
The site-specific file, whether default or specified by --settings, takes precedence over both the global and user-specific configuration files.  

```toml
default_instance="local"

[local]
pipeline="https://127.0.0.1"
api="https://127.0.0.1:8001/"
token="example"

[staging]
pipeline="https://staging.kernelci.org:9100/"
api="https://staging.kernelci.org:9000/"
token="example"

[production]
pipeline="https://kernelci-pipeline.westus3.cloudapp.azure.com/"
api="https://kernelci-api.westus3.cloudapp.azure.com/"
token="example"
```

Where `default_instance` is the default instance to use, if not provided in the command line.  
In section `local`, `staging`, `production` you can provide the host for the pipeline, api and also a token for the available instances.  
pipeline is the URL of the KernelCI Pipeline API endpoint, api is the URL of the new KernelCI API endpoint, and token is the API token to use for authentication.  
If you are using KernelCI Pipeline instance, you can get the token from the project maintainers.  
If it is a local instance, you can generate your token using [kernelci-pipeline/tools/jwt_generator.py](https://github.com/kernelci/kernelci-pipeline/blob/main/tools/jwt_generator.py) script.  

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

- [checkout](checkout)

#### testretry

- [testretry](testretry)

#### maestro-results

- [maestro-results](maestro-results)

