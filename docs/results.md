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

List builds.

Example:

```sh
kci-dev results builds --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --commit  d1486dca38afd08ca279ae94eb3a397f10737824
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
(available for subcommand `build`)

Example:
```sh
kci-dev results builds --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master  --latest --status=fail
```

## --download-logs

Automatically download logs for results listed.
(available for subcommand `build`)

Example:
```sh
kci-dev results build --giturl 'https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git' --branch master --commit  d1486dca38afd08ca279ae94eb3a397f10737824 --download-logs
```


### without arguments

If used without arguments, `kci-dev results` subcommands will get KernelCI status
of local checked out git repository for commands that require a giturl and branch.
In the following example, kci-dev is used on a local linux repository folder
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
kci-dev git:(master)$ kci-dev results --git-folder ../linux
git folder: ../linux
tree: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
branch: master
commit: fbfd64d25c7af3b8695201ebc85efe90be28c5a3

pass/fail/inconclusive
builds: 46/0/0
boots:  580/48/8
tests:  7858/6903/654
```
