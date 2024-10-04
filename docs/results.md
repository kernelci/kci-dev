### results

This command will show the test result by node id.

Example:
```sh
kci-dev results --nodeid <str: testnodeid>
```

This command will show the results of tests by page nodes limit and page offset.

Example:
```sh
kci-dev results --nodes --limit <int: page nodes limit> --offset <int: page nodes offset>
```

Result sample:
```yaml
{'artifacts': None,
 'created': '2024-10-04T00:49:15.691000',
 'data': {'arch': 'x86_64',
          'compiler': 'gcc-12',
          'config_full': 'x86_64_defconfig+lab-setup+x86-board',
          'defconfig': 'x86_64_defconfig',
          'device': None,
          'error_code': None,
          'error_msg': None,
          'job_context': None,
          'job_id': None,
          'kernel_revision': {'branch': 'staging-mainline',
                              'commit': '232edaea0fd9b4b7feb7b43508834bba7e820584',
                              'commit_message': 'staging-mainline-20241004.0',
                              'commit_tags': ['staging-mainline-20241004.0'],
                              'describe': 'staging-mainline-20241004.0',
                              'patchset': None,
                              'tip_of_branch': False,
                              'tree': 'kernelci',
                              'url': 'https://github.com/kernelci/linux.git',
                              'version': {'extra': '-rc1-115-g232edaea0fd9b',
                                          'name': None,
                                          'patchlevel': 12,
                                          'sublevel': None,
                                          'version': 6}},
          'kernel_type': 'bzimage',
          'platform': 'hp-14b-na0052xx-zork',
          'regression': None,
          'runtime': 'lava-collabora',
          'test_revision': None,
          'test_source': None},
 'debug': None,
 'group': 'kselftest-exec',
 'holdoff': None,
 'id': '66ff3b8c0abcc4c8343d1c71',
 'jobfilter': None,
 'kind': 'test',
 'name': 'exec_execveat_Check_success_of_execveat_20_4096',
 'owner': 'staging.kernelci.org',
 'parent': '66ff3b8b0abcc4c8343d1b8a',
 'path': ['checkout',
          'kbuild-gcc-12-x86',
          'kselftest-exec',
          'kselftest-exec',
          'exec_execveat_Check_success_of_execveat_20_4096'],
 'result': 'pass',
 'state': 'done',
 'submitter': 'service:pipeline',
 'timeout': '2024-10-04T06:49:15.691000',
 'treeid': 'a44035dadc31327a5c30db4013b0e7e90acbb6a8fc45f94a6d91671e76cdfd8a',
 'updated': '2024-10-04T00:49:15.691000',
 'user_groups': []}
```

testnodeid is the node id of the test job, which you can get from the KernelCI dashboard. Usually it is hexadecimal string.
