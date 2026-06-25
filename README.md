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

## Shell Completions

kci-dev supports tab completion for bash, zsh, and fish shells. To enable completions:

### Bash
```bash
# Add to ~/.bashrc
source /path/to/kci-dev/completions/kci-dev-completion.bash
```

### Zsh
```bash
# Add to ~/.zshrc (make sure compinit is enabled)
fpath=(/path/to/kci-dev/completions $fpath)
autoload -U compinit && compinit
```

### Fish
```bash
# Copy to fish completions directory
cp /path/to/kci-dev/completions/kci-dev.fish ~/.config/fish/completions/
```

After adding the appropriate lines, restart your shell or source your configuration file.

## KernelCI authorization tokens

Authorizaton tokens can be requested [here](https://github.com/kernelci/kernelci-core/issues/new?template=kernelci-api-tokens.md)

## Contributing to kci-dev

The kci-dev project welcomes, and depends on, contribution from developers and users in the open source community.  
The [Contributor Guide](https://github.com/kernelci/kci-dev/blob/main/CONTRIBUTING.md) should guide you on how to contribute to kci-dev project.

## Documentation

For latest informations check out the documentation [here](https://kernelci.github.io/kci-dev/)  

## Using kci-dev as a Python library

Python applications can import `kci-dev` directly instead of shelling out to the
`kci-dev` command. This is useful for services such as mail clients, patchwork
integrations, or websites that want to test kernel email patches and then submit
or inspect KernelCI data.

### Create a client

```python
from kcidev import KernelCIClient

client = KernelCIClient(
    kcidb_rest_url="https://kcidb.kernelci.org/submit",
    kcidb_token="<token>",
)
```

The client also accepts the same config dictionary layout used by the CLI:

```python
from kcidev import KernelCIClient
from kcidev.libs.common import load_toml

cfg = load_toml(".kci-dev.toml", "submit")
client = KernelCIClient(cfg=cfg, instance="staging")
```

If explicit credentials are not provided, KCIDB submission can also use the
`KCIDB_REST` environment variable supported by the CLI.

### Build and submit KCIDB build results

```python
from kcidev import KernelCIClient

client = KernelCIClient(kcidb_rest_url="https://example.test/submit", kcidb_token="secret")

payload = client.build_kcidb_build_submission(
    origin="my-mail-ci",
    giturl="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
    branch="master",
    commit="0123456789abcdef0123456789abcdef01234567",
    tree_name="mainline",
    arch="x86_64",
    config_name="defconfig",
    compiler="gcc-14",
    status="PASS",
    log_url="https://ci.example.test/logs/0123456789abcdef",
    comment="Build triggered from an email patch series",
)

result = client.submit_kcidb(payload)
```

For applications that already have a checked-out git tree, `git_folder` can be
used instead of manually passing `giturl`, `branch`, and `commit`:

```python
payload = client.build_kcidb_build_submission(
    origin="my-mail-ci",
    git_folder="/srv/builds/linux",
    arch="arm64",
    config_name="defconfig",
    status="FAIL",
)
```

Use `client.submit_build(...)` to build and submit the payload in a single call.

### Query KernelCI dashboard data

The library exposes Python methods for common dashboard requests and returns the
JSON-compatible Python objects returned by the API:

```python
summary = client.get_summary(
    origin="maestro",
    giturl="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
    branch="master",
    commit="0123456789abcdef0123456789abcdef01234567",
)

builds = client.get_builds(
    origin="maestro",
    giturl="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
    branch="master",
    commit="0123456789abcdef0123456789abcdef01234567",
    arch="x86_64",
)
```

Additional helper functions remain importable from `kcidev.libs.*` for advanced
use cases, but new applications should prefer `KernelCIClient` for a stable,
Click-free library interface. Library methods raise `kcidev.KciDevError` for
recoverable kci-dev failures instead of aborting the process like the CLI.

## License

[LGPL-2.1](https://github.com/kernelci/kci-dev/blob/main/LICENSE)
