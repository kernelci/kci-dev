import os
import shutil
from subprocess import PIPE, run

import git
import pytest


def test_prepare():
    # prepare enviroment
    os.system("cp .kci-dev.toml.example .kci-dev.toml")
    assert os.path.exists(".kci-dev.toml")


def test_kcidev_help():
    command = ["poetry", "run", "kci-dev", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_commit_help():
    command = ["poetry", "run", "kci-dev", "commit", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_patch_help():
    command = ["poetry", "run", "kci-dev", "patch", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_results_help():
    command = ["poetry", "run", "kci-dev", "maestro-results", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_testretry_help():
    command = ["poetry", "run", "kci-dev", "testretry", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_checkout_help():
    command = ["poetry", "run", "kci-dev", "checkout", "--help"]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_kcidev_results_tests():
    command = [
        "poetry",
        "run",
        "kci-dev",
        "--instance",
        "staging",
        "maestro-results",
        "--nodeid",
        "65a1355ee98651d0fe81e41d",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)


def test_create_repo():
    repo_dir = os.path.join("my-new-repo")
    file_name = os.path.join(repo_dir, "new-file")
    file_name2 = os.path.join(repo_dir, "new-file2")
    r = git.Repo.init(repo_dir)
    open(file_name, "wb").close()
    r.index.add("new-file")
    r.index.commit("initial commit")
    test_branch = r.create_head("test")
    r.head.reference = test_branch
    open(file_name2, "wb").close()
    r.index.add("new-file2")
    r.index.commit("test")


def test_kcidev_commit():
    command = [
        "poetry",
        "run",
        "kci-dev",
        "--instance",
        "staging",
        "commit",
        "--repository",
        "linux-next",
        "--origin",
        "master",
        "--branch",
        "test",
        "--path",
        "my-new-repo",
    ]
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print("returncode: " + str(result.returncode))
    print("#### stdout ####")
    print(result.stdout)
    print("#### stderr ####")
    print(result.stderr)
    assert result.returncode == 0


def test_main():
    from kcidev.subcommands.commit import api_connection

    print(api_connection("test"))

    pass


def test_clean():
    # clean enviroment
    shutil.rmtree("my-new-repo/")

    if os.path.isfile(".kci-dev.toml"):
        os.remove(".kci-dev.toml")
    else:
        print("File does not exist")
