+++
title = 'watch'
date = 2025-01-30T07:07:07+01:00
description = 'Watch for the results of given node'
+++

This command waits for the results of selected jobs for a particular node id.
At least one `--job-filter` must be supplied; repeat the option to watch multiple
jobs. Watching without a job filter is not supported because jobs can be added to
the node dynamically.

Example:
```sh
kci-dev watch --nodeid 679a91b565fae3351e2fac77 --job-filter "kbuild-gcc-12-x86-chromeos-amd"
```

`--job-filter` and `--test` work in the same manner as in the [checkout](../checkout.md) command.

## --node-id

The Maestro node id to watch for.

## --job-filter

Pass one or more job filters. This option is required:

```sh
kci-dev watch --nodeid 679a91b565fae3351e2fac77 --job-filter "kbuild-gcc-12-x86-chromeos-amd" --job-filter baseline-nfs-arm64-qualcomm --job-filter kbuild-gcc-12-arm64-chromeos-qualcomm
```

### --test

Return code of kci-dev will depend on the test result for the supplied test name:

- `pass` - return code 0 (test passed)
- `fail` - return code 1 (test failed)
- `error` - return code 2 (prior steps failed, such as compilation, test setup, etc, or infrastructure error)
- `critical error` - return code 64 (kci-dev failed to execute command, crashed, etc)

For example:
```sh
kci-dev watch --nodeid 679a91b565fae3351e2fac77 --job-filter baseline-nfs-arm64-qualcomm  --test crit
```

This command can be used for regression bisection, where you can test if the test `crit` pass or fail on the specific commit.
