### testretry

This command will retry the failed tests. In some cases tests may fail due to network issues, hardware problems,
nature of test (flaky), etc. This command will retry the failed tests, and create additional test jobs for the failed tests.
After observing the results, you can decide if test results were reliable, not, or maybe even test need improvement.

Example:
```sh
kci-dev testretry --nodeid <str: testnodeid>
```

testnodeid is the node id of the test job, which you can get from the KernelCI dashboard. Usually it is hexadecimal string.
