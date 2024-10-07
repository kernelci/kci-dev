### checkout

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

You can also set instead of --commit option --tipoftree which will retrieve the latest commit of the tree.
