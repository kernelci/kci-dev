import configparser
import os
import subprocess
import urllib

from libs.dashboard import dashboard_fetch_tree_list

from kcidev.libs.common import *


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


def get_latest_commit(origin, giturl, branch):
    trees = dashboard_fetch_tree_list(origin, False)
    for t in trees:
        if t["git_repository_url"] == giturl and t["git_repository_branch"] == branch:
            return t["git_commit_hash"]

    kci_err("Tree and branch not found.")
    raise click.Abort()


def set_giturl_branch_commit(origin, giturl, branch, commit, latest, git_folder):
    if not giturl or not branch or not ((commit != None) ^ latest):
        giturl, branch, commit = get_folder_repository(git_folder, branch)
    if latest:
        commit = get_latest_commit(origin, giturl, branch)
    return giturl, branch, commit
