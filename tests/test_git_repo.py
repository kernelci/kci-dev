import subprocess

import pytest

from kcidev.libs.git_repo import get_repository_url, repository_url_cleaner


@pytest.mark.parametrize(
    ("remote", "expected"),
    [
        (
            "https://github.com/kernelci/kci-dev.git",
            "https://github.com/kernelci/kci-dev.git",
        ),
        (
            "ssh://git@github.com/kernelci/kci-dev.git",
            "https://github.com/kernelci/kci-dev.git",
        ),
        (
            "git@github.com:kernelci/kci-dev.git",
            "https://github.com/kernelci/kci-dev.git",
        ),
    ],
)
def test_repository_url_cleaner_normalizes_git_remote_urls(remote, expected):
    assert repository_url_cleaner(remote) == expected


def _create_repository(path, remote):
    path.mkdir()
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    subprocess.run(["git", "remote", "add", "origin", remote], cwd=path, check=True)
    (path / "README").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=path, check=True, capture_output=True
    )


def test_get_repository_url_from_nested_directory(tmp_path):
    repository = tmp_path / "repository"
    _create_repository(repository, "git@github.com:kernelci/kci-dev.git")
    nested = repository / "one" / "two"
    nested.mkdir(parents=True)

    assert get_repository_url(nested) == "https://github.com/kernelci/kci-dev.git"


def test_get_repository_url_from_linked_worktree(tmp_path):
    repository = tmp_path / "repository"
    worktree = tmp_path / "worktree"
    _create_repository(repository, "git@github.com:kernelci/kci-dev.git")
    subprocess.run(
        ["git", "worktree", "add", "-b", "worktree-branch", str(worktree)],
        cwd=repository,
        check=True,
        capture_output=True,
    )

    assert (worktree / ".git").is_file()
    assert get_repository_url(worktree) == "https://github.com/kernelci/kci-dev.git"
