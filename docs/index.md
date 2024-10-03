# kci-dev

kci-dev is a cmdline tool for interact with a enabled KernelCI server
Purpose of this tool to provide a easy way to use features of KernelCI Pipeline instance.

## Installation

Using poetry and virtualenv
```sh
virtualenv .venv
source .venv/bin/activate
pip install poetry
poetry install
poetry run kci-dev
```

## Configuration

kci-dev uses a configuration file .kci-dev.toml in the program directory.
```toml
default_instance="local"

[local]
host="https://127.0.0.1"
token="example"

[staging_pipeline]
host="https://staging.kernelci.org:9100/"
token="example"

[staging_api]
host="https://staging.kernelci.org:9000/"
token="example"

[production_pipeline]
host="https://kernelci-pipeline.westus3.cloudapp.azure.com/"
token="example"

[production_api]
host="https://kernelci-api.westus3.cloudapp.azure.com/"
token="example"
```

Where `default_instance` is the default instance to use, if not provided in the command line.
In section `local`, `staging`, `production` you can provide the host and token for the available instances.
host is the URL of the KernelCI Pipeline API endpoint, and token is the API token to use for authentication.
If you are using KernelCI Pipeline instance, you can get the token from the project maintainers.
If it is a local instance, you can generate your token using kernelci-pipeline/tools/jwt_generator.py script.

## Options

### instance
You can provide the instance name to use for the command.

Example:
```sh
kci-dev --instance staging_api
```

### settings

You can provide the configuration file path to use for the command.

Example:
```sh
kci-dev --settings /path/to/.kci-dev.toml
```

## Commands

### testretry

This command will retry the failed tests. In some cases tests may fail due to network issues, hardware problems,
nature of test (flaky), etc. This command will retry the failed tests, and create additional test jobs for the failed tests.
After observing the results, you can decide if test results were reliable, not, or maybe even test need improvement.

Example:
```sh
kci-dev testretry --nodeid <str: testnodeid>
```

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
