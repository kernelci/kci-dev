+++
title = 'checkout'
date = 2024-01-14T07:07:07+01:00
description = 'This command allow to test arbitary commit on the KernelCI Pipeline instance.'
+++

This command allow to test arbitary commit on the KernelCI Pipeline instance.  
This might be useful in several cases:
- You want to test a specific commit, if it fails or pass test, or introduce any other degradation comparing to the current, or another commit.
- You want to create snapshot of the test results on specific tags (releases, etc).
- Use this command for regression bisection

This command can execute all tests configured for particular tree/branch, or you can provide jobfilter to execute specific tests and builds.

Example:
```sh
kci-dev checkout --giturl https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git --branch master --commit f06021a18fcf8d8a1e79c5e0a8ec4eb2b038e153 --jobfilter "kbuild-gcc-12-x86"
```

Where:
- `giturl` is the URL of the git repository to test.
- `branch` is the branch of the git repository to test.
- `commit` is the commit hash to test.
- `jobfilter` is the job filter to use for the test (optional parameter)
- `platformfilter` is the platform filter (usually it is name of hardware platform for group of devices) to use for the test (optional parameter)

To figure out correct jobfilter and platformfilter, you need to check test json node. For example:
```json
{
  "id": "670f0c27493b6b8188c7667c",
  "kind": "job",
  "name": "tast-mm-misc-arm64-qualcomm",
  "path": [
    "checkout",
    "kbuild-gcc-12-arm64-chromeos-qualcomm",
    "tast-mm-misc-arm64-qualcomm"
  ],
  "group": "tast-mm-misc-arm64-qualcomm",
  "parent": "670f0782493b6b8188c7621c",
  "state": "done",
  "result": "pass",
  "artifacts": {
    "lava_log": "https://kciapistagingstorage1.file.core.windows.net/staging/tast-mm-misc-arm64-qualcomm-670f0c27493b6b8188c7667c/log.txt.gz?sv=2022-11-02&ss=f&srt=sco&sp=r&se=2024-10-17T19:19:12Z&st=2023-10-17T11:19:12Z&spr=https&sig=sLmFlvZHXRrZsSGubsDUIvTiv%2BtzgDq6vALfkrtWnv8%3D",
    "callback_data": "https://kciapistagingstorage1.file.core.windows.net/staging/tast-mm-misc-arm64-qualcomm-670f0c27493b6b8188c7667c/lava_callback.json.gz?sv=2022-11-02&ss=f&srt=sco&sp=r&se=2024-10-17T19:19:12Z&st=2023-10-17T11:19:12Z&spr=https&sig=sLmFlvZHXRrZsSGubsDUIvTiv%2BtzgDq6vALfkrtWnv8%3D"
  },
  "data": {
    "error_code": null,
    "error_msg": null,
    "test_source": null,
    "test_revision": null,
    "platform": "sc7180-trogdor-lazor-limozeen",
    "device": "sc7180-trogdor-lazor-limozeen-cbg-7",
    "runtime": "lava-collabora",
    "job_id": "16081547",
    "job_context": null,
    "regression": null,
    "kernel_revision": {
      "tree": "kernelci",
      "url": "https://github.com/kernelci/linux.git",
      "branch": "staging-mainline",
      "commit": "c862449c840a37bbe797a0b719881449beac75ca",
      "describe": "staging-mainline-20241016.0",
      "version": {
        "version": 6,
        "patchlevel": 12,
        "sublevel": null,
        "extra": "-rc3-45-gc862449c840a3",
        "name": null
      },
      "patchset": null,
      "commit_tags": [
        "staging-mainline-20241016.0"
      ],
      "commit_message": "staging-mainline-20241016.0",
      "tip_of_branch": false
    },
    "arch": "arm64",
    "defconfig": "cros://chromeos-6.6/arm64/chromiumos-qualcomm.flavour.config",
    "config_full": "+lab-setup+arm64-chromebook+CONFIG_MODULE_COMPRESS=n+CONFIG_MODULE_COMPRESS_NONE=y",
    "compiler": "gcc-12",
    "kernel_type": "image"
  },
  "debug": null,
  "jobfilter": null,
  "platform_filter": null,
  "created": "2024-10-16T00:43:19.079000",
  "updated": "2024-10-16T02:22:58.113000",
  "timeout": "2024-10-16T06:43:19.079000",
  "holdoff": null,
  "owner": "staging.kernelci.org",
  "submitter": "service:pipeline",
  "treeid": "f53af2a7273aed52629647124c95e8ddc79a317b93bced2ee36837bde03d88af",
  "user_groups": []
}
```

In this example, the jobfilter is `tast-mm-misc-arm64-qualcomm` for test, if you look into path, you can figure out also build job named and the platformfilter is `kbuild-gcc-12-arm64-chromeos-qualcomm` and in data/platform: `sc7180-trogdor-lazor-limozeen`. So complete command to test this job would be:
```sh
kci-dev checkout --giturl https://github.com/kernelci/linux.git --branch staging-mainline --commit c862449c840a37bbe797a0b719881449beac75ca --jobfilter tast-mm-misc-arm64-qualcomm --jobfilter kbuild-gcc-12-arm64-chromeos-qualcomm --platformfilter sc7180-trogdor-lazor-limozeen
```

Other options:

### --tipoftree

You can also set instead of --commit option --tipoftree which will retrieve the latest commit of the tree.

### --watch

Additionally, you can use --watch option to watch the progress of the test.

After executing the command, you will see the output similar to the following:
```sh
./kci-dev.py checkout --giturl https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git --branch master --tipoftree --jobfilter baseline-nfs-arm64-qualcomm --jobfilter kbuild-gcc-12-arm64-chromeos-qualcomm --watch
api connect: https://staging.kernelci.org:9100/
Retrieving latest commit on tree: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git branch: master
Commit to checkout: d3d1556696c1a993eec54ac585fe5bf677e07474
OK
Watching for jobs on treeid: ad137d5a009f685d1c9c964897bcc35d552b031c9f542b433908fa1368b95465
Current time: 2024-10-10 14:20:11
Total tree nodes 1 found.
Node 6707b869322a7c560a1a2c69 job checkout State running Result None
Refresh in 30s...Current time: 2024-10-10 14:20:41
Total tree nodes 1 found.
Node 6707b869322a7c560a1a2c69 job checkout State running Result None
Refresh in 30s...Current time: 2024-10-10 14:21:13
Total tree nodes 1 found.
Node 6707b869322a7c560a1a2c69 job checkout State running Result None
Refresh in 30s...Current time: 2024-10-10 14:21:43
Total tree nodes 1 found.
Node 6707b869322a7c560a1a2c69 job checkout State running Result None
Refresh in 30s...Current time: 2024-10-10 14:22:14
Total tree nodes 1 found.
Node 6707b869322a7c560a1a2c69 job checkout State available Result None
Refresh in 30s...Current time: 2024-10-10 14:22:45
Total tree nodes 2 found.
Node 6707b869322a7c560a1a2c69 job checkout State available Result None
Node 6707b8ed322a7c560a1a2dc2 job kbuild-gcc-12-arm64-chromeos-qualcomm State running Result None
...
Refresh in 30s...Current time: 2024-10-10 14:41:22
Total tree nodes 12 found.
Node 6707b869322a7c560a1a2c69 job checkout State closing Result None
Node 6707b8ed322a7c560a1a2dc2 job kbuild-gcc-12-arm64-chromeos-qualcomm State done Result pass
Node 6707bc74322a7c560a1a38f6 job baseline-nfs-arm64-qualcomm State done Result pass
Node 6707bc75322a7c560a1a38f7 job baseline-nfs-arm64-qualcomm State running Result None
Refresh in 30s...Current time: 2024-10-10 14:41:53
Total tree nodes 12 found.
Node 6707b869322a7c560a1a2c69 job checkout State closing Result None
Node 6707b8ed322a7c560a1a2dc2 job kbuild-gcc-12-arm64-chromeos-qualcomm State done Result pass
Node 6707bc74322a7c560a1a38f6 job baseline-nfs-arm64-qualcomm State done Result pass
Node 6707bc75322a7c560a1a38f7 job baseline-nfs-arm64-qualcomm State running Result None
Refresh in 30s...Current time: 2024-10-10 14:42:23
Total tree nodes 12 found.
Node 6707b869322a7c560a1a2c69 job checkout State closing Result None
Node 6707b8ed322a7c560a1a2dc2 job kbuild-gcc-12-arm64-chromeos-qualcomm State done Result pass
Node 6707bc74322a7c560a1a38f6 job baseline-nfs-arm64-qualcomm State done Result pass
Node 6707bc75322a7c560a1a38f7 job baseline-nfs-arm64-qualcomm State running Result None
```

The command will keep watching the progress of the test until all jobs are done.  
You can also stop the watching by pressing `Ctrl+C` or command will stop after all jobs are done(or failed).

### --test

Together with --watch option, you can use --test option to wait for particular test results. Return code of kci-dev will depend on the test result:

- `pass` - return code 0 (test passed)
- `fail` - return code 1 (test failed)
- `error` - return code 2 (prior steps failed, such as compilation, test setup, etc, or infrastructure error)

For example:
```sh
kci-dev.py checkout --giturl https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git --branch master --tipoftree --jobfilter baseline-nfs-arm64-qualcomm --jobfilter kbuild-gcc-12-arm64-chromeos-qualcomm --platformfilter sc7180-trogdor-kingoftown --watch --test crit
```

This command will wait for the test results of the test with the name `crit`.  
It will follow first jobs, such as `checkout`, `kbuild-gcc-12-arm64-chromeos-qualcomm`, `baseline-nfs-arm64-qualcomm` and when they are complete will wait until timeout for the test `crit` to finish.  
If the test `crit` will pass, the command will return 0, if it will fail, the command will return 1, if any of the jobs will fail or timeout, the command will return 2.  

This command can be used for regression bisection, where you can test if the test `crit` pass or fail on the specific commit.
