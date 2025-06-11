import configparser
import os
import subprocess
import urllib

from kcidev.libs.common import *
from kcidev.libs.dashboard import dashboard_fetch_tree_list


def repository_url_cleaner(url):
    # standardize protocol to https
    parsed = urllib.parse.urlsplit(url)
    scheme = "https"

    # remove auth from url
    authority = parsed.hostname
    if parsed.port:
        authority += f":{parsed.port}"

    url_cleaned = urllib.parse.urlunsplit((scheme, authority, *parsed[2:]))
    return url_cleaned


def is_inside_work_tree():
    process = subprocess.Popen(
        ["git", "rev-parse", "--is-inside-work-tree"], stdout=subprocess.PIPE, text=True
    )
    std_out, _ = process.communicate()
    is_inside_work_tree = std_out.strip()
    if is_inside_work_tree:
        return True
    return False


def get_folder_repository(git_folder, branch):
    kci_msg("git folder: " + str(git_folder))
    if git_folder:
        current_folder = git_folder
    else:
        current_folder = os.getcwd()

    previous_folder = os.getcwd()
    if os.path.isdir(current_folder):
        os.chdir(current_folder)
    else:
        os.chdir(previous_folder)
        kci_err("Not a folder")
        raise click.Abort()
    dot_git_folder = os.path.join(current_folder, ".git")
    if is_inside_work_tree():
        while not os.path.exists(dot_git_folder):
            current_folder = os.path.join(current_folder, "..")
            dot_git_folder = os.path.join(current_folder, ".git")

    # Check if we are in a git repository
    if os.path.exists(dot_git_folder):
        # Get remote origin url
        git_config_path = os.path.join(dot_git_folder, "config")
        git_config = configparser.ConfigParser(strict=False)
        git_config.read(git_config_path)
        git_url = git_config.get('remote "origin"', "url")
        # A way of standardize git url for API call
        git_url = repository_url_cleaner(git_url)
        # Get current branch name
        process = subprocess.Popen(
            ["git", "branch", "--show-current"], stdout=subprocess.PIPE, text=True
        )
        branch_name, _ = process.communicate()
        branch_name = branch_name.strip()
        if branch:
            branch_name = branch

        # Get last commit hash
        process = subprocess.Popen(
            ["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, text=True
        )
        last_commit_hash, last_commit_hash_error = process.communicate()
        last_commit_hash = last_commit_hash.strip()

        os.chdir(previous_folder)
        kci_msg("tree: " + git_url)
        kci_msg("branch: " + branch_name)
        kci_msg("commit: " + last_commit_hash)
        return git_url, branch_name, last_commit_hash
    else:
        os.chdir(previous_folder)
        kci_err("Not a GIT folder")
        raise click.Abort()


def get_current_branch_name(git_folder):
    """Get the current branch name from a git repository."""
    if git_folder:
        current_folder = git_folder
    else:
        current_folder = os.getcwd()

    previous_folder = os.getcwd()
    if os.path.isdir(current_folder):
        os.chdir(current_folder)
    else:
        os.chdir(previous_folder)
        return None

    if is_inside_work_tree():
        process = subprocess.Popen(
            ["git", "branch", "--show-current"], stdout=subprocess.PIPE, text=True
        )
        branch_name, _ = process.communicate()
        branch_name = branch_name.strip()
        os.chdir(previous_folder)
        return branch_name
    else:
        os.chdir(previous_folder)
        return None


def get_current_commit_hash(git_folder):
    """Get the current commit hash from a git repository."""
    if git_folder:
        current_folder = git_folder
    else:
        current_folder = os.getcwd()

    previous_folder = os.getcwd()
    if os.path.isdir(current_folder):
        os.chdir(current_folder)
    else:
        os.chdir(previous_folder)
        return None

    if is_inside_work_tree():
        process = subprocess.Popen(
            ["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, text=True
        )
        commit_hash, _ = process.communicate()
        commit_hash = commit_hash.strip()
        os.chdir(previous_folder)
        return commit_hash
    else:
        os.chdir(previous_folder)
        return None


def get_repository_url(git_folder):
    """Get the repository URL from a git repository."""
    if git_folder:
        current_folder = git_folder
    else:
        current_folder = os.getcwd()

    previous_folder = os.getcwd()
    if os.path.isdir(current_folder):
        os.chdir(current_folder)
    else:
        os.chdir(previous_folder)
        return None

    dot_git_folder = os.path.join(current_folder, ".git")
    if is_inside_work_tree():
        while not os.path.exists(dot_git_folder):
            current_folder = os.path.join(current_folder, "..")
            dot_git_folder = os.path.join(current_folder, ".git")

    if os.path.exists(dot_git_folder):
        git_config_path = os.path.join(dot_git_folder, "config")
        git_config = configparser.ConfigParser(strict=False)
        git_config.read(git_config_path)
        try:
            git_url = git_config.get('remote "origin"', "url")
            git_url = repository_url_cleaner(git_url)
            os.chdir(previous_folder)
            return git_url
        except:
            os.chdir(previous_folder)
            return None
    else:
        os.chdir(previous_folder)
        return None


def get_latest_commit(origin, giturl, branch):
    trees = dashboard_fetch_tree_list(origin, False)
    for t in trees:
        if t["git_repository_url"] == giturl and t["git_repository_branch"] == branch:
            return t["git_commit_hash"]

    kci_err("Tree and branch not found.")
    raise click.Abort()


def set_giturl_branch_commit(origin, giturl, branch, commit, latest, git_folder):
    # Fill in any missing parameters from local git repository
    if not giturl:
        giturl = get_repository_url(git_folder)
        if not giturl:
            kci_err("No git URL provided and could not determine from local repository")
            raise click.Abort()

    if not branch:
        branch = get_current_branch_name(git_folder)
        if not branch:
            kci_err("No branch provided and could not determine from local repository")
            raise click.Abort()

    if not commit and not latest:
        commit = get_current_commit_hash(git_folder)
        if not commit:
            kci_err("No commit provided and could not determine from local repository")
            raise click.Abort()

    # Print the final values
    kci_msg("git folder: " + str(git_folder))
    kci_msg("tree: " + giturl)
    kci_msg("branch: " + branch)
    if commit:
        kci_msg("commit: " + commit)

    if latest:
        commit = get_latest_commit(origin, giturl, branch)
        kci_msg("commit: " + commit)

    return giturl, branch, commit
