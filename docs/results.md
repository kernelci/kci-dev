+++
title = 'results'
date = 2024-01-14T07:07:07+01:00
description = 'Command for show test results.'
+++

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

testnodeid is the node id of the test job, which you can get from the KernelCI dashboard.  
Usually it is hexadecimal string.  

Additionally, for --nodes you can provide optional parameters --filter to filter the results by the given key and value.  
For example:
```sh
./kci-dev.py results --nodes --filter treeid=e25266f77837de335edba3c1b8d2a04edc2bfb195b77c44711d81ebea4494140 --filter kind=test
```
This command will show the nodes of tests in particular tree checkout.  
But as you might see, there is a lot of fields you might be not interested in.  

For this we have additional option --field, that will restrict output only to specified fields.  
For example:
```sh
./kci-dev.py results --nodes --filter treeid=e25266f77837de335edba3c1b8d2a04edc2bfb195b77c44711d81ebea4494140 --filter kind=test --field name --field result
```
Example:

```json
{'name': 'kver', 'result': 'pass'}
{'name': 'config', 'result': 'pass'}
{'name': 'build', 'result': 'pass'}
{'name': 'example_init_test', 'result': 'pass'}
{'name': 'time64_to_tm_test_date_range', 'result': 'pass'}
{'name': 'test_one_cpu', 'result': 'skip'}
{'name': 'test_many_cpus', 'result': 'skip'}
{'name': 'test_one_task_on_all_cpus', 'result': 'skip'}
{'name': 'test_two_tasks_on_all_cpus', 'result': 'skip'}
{'name': 'test_one_task_on_one_cpu', 'result': 'skip'}
{'name': 'test_one_task_mixed', 'result': 'skip'}
{'name': 'test_two_tasks_on_one_cpu', 'result': 'skip'}
{'name': 'test_two_tasks_on_one_all_cpus', 'result': 'skip'}
{'name': 'test_task_on_all_and_one_cpu', 'result': 'skip'}
{'name': 'resource_test_union', 'result': 'pass'}
{'name': 'resource_test_intersection', 'result': 'pass'}
....
```
