# kci-dev

<p align="center">
  <a href="https://pypi.org/project/kci-dev"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/kci-dev.svg?maxAge=86400" /></a>
  <a href="https://pypi.org/project/kci-dev"><img alt="Python Versions" src="https://img.shields.io/pypi/pyversions/kci-dev.svg?maxAge=86400" /></a>
  <a href="https://www.bestpractices.dev/projects/9829"><img src="https://www.bestpractices.dev/projects/9829/badge"></a>
</p>

> *Stand alone tool for Linux Kernel developers and maintainers to interact with KernelCI*

## Quickstart

Using [PyPI](https://pypi.org/project/kci-dev/) and virtualenv
```sh
virtualenv .venv
source .venv/bin/activate
pip install kci-dev
```

## Config file

> `kci-dev results` can be used without a config file or KernelCI authorization token.  

For other subcommands (like `kci-dev bisect`) is possible to create a default config file at  
`~/.config/kci-dev/kci-dev.toml` with the following command:  
```sh
kci-dev config
```

## KernelCI authorization tokens

Authorizaton tokens can be requested [here](https://github.com/kernelci/kernelci-core/issues/new?template=kernelci-api-tokens.md)

## Contributing to kci-dev

The kci-dev project welcomes, and depends on, contribution from developers and users in the open source community.  
The [Contributor Guide](https://github.com/kernelci/kci-dev/blob/main/CONTRIBUTING.md) should guide you on how to contribute to kci-dev project.

## Documentation

For latest informations check out the documentation [here](https://kernelci.github.io/kci-dev/)  

## License

[LGPL-2.1](https://github.com/kernelci/kci-dev/blob/main/LICENSE)
