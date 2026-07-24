+++
title = 'patchset'
date = 2026-07-24T00:00:00+01:00
description = 'Command for testing patches on top of an existing checkout.'
+++

This command tests one or more patches on top of an existing checkout on the
KernelCI Pipeline instance.
It is useful to verify a patch or a patch series before sending it to a
mailing list, or to check whether a fix repairs a failing test.

The patches are applied on top of a checkout node created with the
[checkout](../checkout) command, in the order given.
Patches can be local files, uploaded inline, or URLs from an allowed domain
such as patchwork.kernel.org.

First trigger a checkout of the tree/branch/commit the patches are based on:
```sh
kci-dev checkout --giturl https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git --branch master --tipoftree
```

The command prints a `checkout_nodeid`, which identifies the checkout to
apply the patches on.

Then test local patch files, for example the output of `git format-patch`:
```sh
kci-dev patchset --nodeid <checkout_nodeid> --patch 0001-fix.patch --patch 0002-fix.patch --job-filter "kbuild-gcc-12-x86"
```

Or test a patch series from patchwork:
```sh
kci-dev patchset --nodeid <checkout_nodeid> --patchurl https://patchwork.kernel.org/series/123456/mbox/ --job-filter "kbuild-gcc-12-x86"
```

Where:
- `nodeid` is the id of the checkout node to apply the patches on.
- `patch` is a local patch file to upload. Can be used multiple times.
- `patchurl` is a patch URL from an allowed domain. Can be used multiple
  times. `--patch` and `--patchurl` cannot be combined in one request.
- `job-filter` is the job filter to use for the test (optional parameter)
- `platform-filter` is the platform filter to use for the test (optional
  parameter)

Patch files must be text-only unified diffs. The pipeline rejects binary
patches, and at most 32 patches of up to 10 MiB each can be uploaded per
request.

### --watch, -w

As with the checkout command, you can use the `--watch` option to watch the
progress of the test on the patched tree, and `--test` to wait for a
particular test result and set the exit code accordingly.
See the [checkout](../checkout) documentation for details.

```sh
kci-dev patchset --nodeid <checkout_nodeid> --patch fix.patch --job-filter baseline-nfs-arm64-qualcomm --watch --test baseline.login
```
