+++
title = 'results'
date = 2024-12-10T07:07:07+01:00
description = 'Fetch results from the KernelCI ecosystem.'
+++

`kci-dev` pulls from our Dashboard API. As of now, it is an EXPERIMENTAL tooling under development with close collaboration from Linux kernel maintainers.

> KNOWN ISSUE: The Dashboard endpoint we are using returns a file of a few megabytes in size, so download may take
a few seconds, slowing down your usage of `kci-dev results`. We are working on [it](https://github.com/kernelci/dashboard/issues/661).

## Base parameters

### --origin

Set the KCIDB origin desired. 'maestro' is the default.

### --giturl

The url of the tree to fetch results

### --branch

The branch to get results for

### --commit

The tip of tree commit being tested. It needs to be the full commit hash.

Unfortunately the Dashboard API doesn't support git tags as parameters yet.

### --latest

Return results for the latest commit for the tree.

### --status

Filter results by the status: "all", "pass", "fail" or "inconclusive"

## Results actions

### --action=trees

List all available trees for a given origin.

Example:

```sh
kci-dev results --action=trees
```

### --action=summary

Shows a numeric summary of the build, boot and test results.
If `--action` is omitted, it will show the summary by default.

Example:

```sh
kci-dev results --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --commit  d1486dca38afd08ca279ae94eb3a397f10737824 --action=summary
```

### --action=builds

List builds.

Example:

```sh
kci-dev results --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --commit  d1486dca38afd08ca279ae94eb3a397f10737824 --action builds
```

## Downloading logs

`--download-logs` Download failed logs when used with `--action=failed-*` commands.

Example:
```sh
kci-dev results --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --commit  d1486dca38afd08ca279ae94eb3a397f10737824 --action failed-builds --download-logs
```




