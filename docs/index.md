# kci-dev

kci-dev is a cmdline tool for interact with a enabled KernelCI server
Purpose of this tool to provide a easy way to use features of KernelCI Pipeline instance.

## Installation

### Using PyPI and virtualenv
```sh
virtualenv .venv
source .venv/bin/activate
pip install kci-dev
```

### Using poetry and virtualenv
```sh
virtualenv .venv
source .venv/bin/activate
pip install poetry
poetry install
poetry run kci-dev
```

## Configuration

kci-dev uses a configuration file .kci-dev.toml in the program directory.
```toml
default_instance="local"

[local]
host="https://127.0.0.1"
token="example"

[staging_pipeline]
host="https://staging.kernelci.org:9100/"
token="example"

[staging_api]
host="https://staging.kernelci.org:9000/"
token="example"

[production_pipeline]
host="https://kernelci-pipeline.westus3.cloudapp.azure.com/"
token="example"

[production_api]
host="https://kernelci-api.westus3.cloudapp.azure.com/"
token="example"
```

Where `default_instance` is the default instance to use, if not provided in the command line.
In section `local`, `staging`, `production` you can provide the host and token for the available instances.
host is the URL of the KernelCI Pipeline API endpoint, and token is the API token to use for authentication.
If you are using KernelCI Pipeline instance, you can get the token from the project maintainers.
If it is a local instance, you can generate your token using [kernelci-pipeline/tools/jwt_generator.py](https://github.com/kernelci/kernelci-pipeline/blob/main/tools/jwt_generator.py) script.

## Options

### instance
You can provide the instance name to use for the command.

Example:
```sh
kci-dev --instance staging_api
```

### settings

You can provide the configuration file path to use for the command.

Example:
```sh
kci-dev --settings /path/to/.kci-dev.toml
```

## Commands

### checkout

- [checkout](checkout.md)

### testretry

- [testretry](testretry.md)

### results

- [results](results.md)
