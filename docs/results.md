+++
title = 'results'
date = 2024-12-10T07:07:07+01:00
description = 'Fetch results from the KernelCI ecosystem.'
+++

`kci-dev` pulls from our Dashboard API. As of now, it is an EXPERIMENTAL tooling under development with close collaboration from Linux kernel maintainers.

> KNOWN ISSUE: The Dashboard endpoint we are using returns a file of a few megabytes in size, so download may take
a few seconds, slowing down your usage of `kci-dev results`. We are working on [it](https://github.com/kernelci/dashboard/issues/661).


## Commands

### trees

```sh
kci-dev results trees
```

### summary

Shows a numeric summary of the build, boot and test results.

Example:

```sh
kci-dev results summary --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --commit  d1486dca38afd08ca279ae94eb3a397f10737824
```

### builds

List builds results.

Example:

```sh
kci-dev results builds --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --commit  d1486dca38afd08ca279ae94eb3a397f10737824
```

### <a id="result-boots"></a>boots

List boot results.

Example:

```sh
kci-dev results boots --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --latest
```

### tests

List test results.

Example:

```sh
kci-dev results tests --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --commit  d1486dca38afd08ca279ae94eb3a397f10737824
```

### test

Obtains a single test result.

Example:

```sh
kci-dev results test --id 'maestro:67d3e293f378f0c5986d3309' --download-logs --json
```

### build

Displays all the information from a single build.

Example:

```sh
kci-dev results build --id 'maestro:67d409f9f378f0c5986dc7df' --download-logs --json
```

### hardware

Displays hardware related information

#### list

List all available hardware for the given origin (Maestro by default), for the last 7 days

Example:

```sh
kci-dev results hardware list --origin maestro --json
```

#### summary

Gives a summary on the builds, boots and tests run of the hardware with `name` for the last seven days

Example:

```sh
kci-dev results hardware summary --name mediatek,mt8195 --origin maestro --json
```

#### boots

List boot results for a hardware with `name` list for the last seven days.
It supports the same options as [results boots](#result-boots).

Example:

```sh
kci-dev results hardware boots --name mediatek,mt8195 --origin maestro --json
```

## Common parameters

### --origin

Set the KCIDB origin desired. 'maestro' is the default.

### --giturl

The url of the tree to fetch results

### --branch

The branch to get results for

### --git-folder

Path of the local git repository

### --commit

The tip of tree commit being tested. It needs to be the full commit hash.

Unfortunately the Dashboard API doesn't support git tags as parameters yet.

### --latest

Return results for the latest commit for the tree.

Example:
```sh
kci-dev results builds --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master  --latest
```

### --status

Filter results by the status: "all", "pass", "fail" or "inconclusive".
(available for subcommands `build`, `boots` and `tests`)

Example:
```sh
kci-dev results builds --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master  --latest --status=fail
```

## --download-logs

Automatically download logs for results listed.
(available for subcommands `build`, `boots` and `tests`)

Example:
```sh
kci-dev results builds --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --commit  d1486dca38afd08ca279ae94eb3a397f10737824 --download-logs
```

## --filter

Pass a YAML filter file to customize results. Only supports hardware and test name filtering at the moment.
See filter yaml example below:
(available for subcommands `boots` and `tests`)

```yaml
hardware:
  - radxa,rock2-square
  - fsl,imx6q
  - dell-latitude-3445-7520c-skyrim
test:
  - kselftest.dt
  - kselftest.iommu
```

Example:
```sh
kci-dev results boots --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --latest --filter=filter.yaml
```

## --arch

Filters results by arch.

Example:
```sh
kci-dev results summary --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master  --latest --arch arm64
```

## --count

Displays the number of results.

Example:

```sh
kci-dev results summary --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master  --latest --count
```

## --json

Displays results in a json format. It also affects flags like  `--count`.

Example:

```sh
kci-dev results summary --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master  --latest --json
```

### without arguments

If used without arguments, `kci-dev results` subcommands will get KernelCI status
of local checked out git repository for commands that require a giturl and branch.
In the following example, kci-dev is used on a local linux repository folder.
This command work with every linux repository supported by KernelCI

```sh
linux git:(master)$ kci-dev results summary
git folder: None
tree: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
branch: master
commit: fbfd64d25c7af3b8695201ebc85efe90be28c5a3
pass/fail/inconclusive
builds: 46/0/0
boots:  580/48/8
tests:  7858/6903/654
```

### --git-folder=\<local repository path\>

Get results automatically from a folder with a local linux repository.

```sh
kci-dev git:(master)$ kci-dev results summary --git-folder ../linux
git folder: ../linux
tree: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
branch: master
commit: fbfd64d25c7af3b8695201ebc85efe90be28c5a3
pass/fail/inconclusive
builds: 46/0/0
boots:  580/48/8
tests:  7858/6903/654
```

## --branch

In the case of the script not been able to get the current branch information,  
like in the case of a detached HEAD, it is possible to specify a branch.  
Like in the following case:  

```sh
linux-cip git:(6077b17f20b1) kci-dev results summary --branch linux-5.10.y-cip
git folder: None
tree: https://git.kernel.org/pub/scm/linux/kernel/git/cip/linux-cip.git
branch: linux-5.10.y-cip
commit: 6077b17f20b1bcfeccaa23bc05573b938c47679d
pass/fail/inconclusive
builds: 21/0/0
boots:  440/36/18
tests:  1190/184/100
```
