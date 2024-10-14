## checkout

This command allow to test arbitary commit on the KernelCI Pipeline instance. This might be useful in several cases:
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

The command will keep watching the progress of the test until all jobs are done. You can also stop the watching by pressing `Ctrl+C` or command will stop after all jobs are done(or failed).
