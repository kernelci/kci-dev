# kci-dev

<p align="center">
  <a href="https://pypi.org/project/kci-dev"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/kci-dev.svg?maxAge=86400" /></a>
  <a href="https://pypi.org/project/kci-dev"><img alt="Python Versions" src="https://img.shields.io/pypi/pyversions/kci-dev.svg?maxAge=86400" /></a>
</p>

> *cmdline tool for interact with KernelCI*

kci-dev is a cmdline tool for interact with a enabled KernelCI server

## Quickstart

Using poetry and virtualenv
```sh
virtualenv .venv
source .venv/bin/activate
pip install poetry
poetry install
poetry run kci-dev
```

## Contributing to kci-dev

The kci-dev project welcomes, and depends on, contribution from developers and users in the open source community.

## Contributing guide

Run the following checks before sending a PR
```sh
poetry run black --check --verbose .
poetry run isort . --check --diff
poetry run pytest -rP
```

## License

[LGPL-2.1](https://github.com/kernelci/kci-dev/blob/main/LICENSE)
