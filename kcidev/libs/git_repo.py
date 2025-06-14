import configparser
import logging
import os
import subprocess
import urllib

from kcidev.libs.common import *
from kcidev.libs.dashboard import dashboard_fetch_tree_list


def repository_url_cleaner(url):
    # standardize protocol to https
    logging.debug(f"Cleaning repository URL: {url}")
    parsed = urllib.parse.urlsplit(url)
    scheme = "https"

    # remove auth from url
    authority = parsed.hostname
    if parsed.port:
        authority += f":{parsed.port}"

    url_cleaned = urllib.parse.urlunsplit((scheme, authority, *parsed[2:]))
    logging.debug(f"Cleaned URL: {url_cleaned}")
    return url_cleaned


def is_inside_work_tree():
    cmd = ["git", "rev-parse", "--is-inside-work-tree"]
    logging.debug(f"Running command: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    std_out, std_err = process.communicate()
    is_inside_work_tree = std_out.strip()

    if process.returncode != 0:
        logging.debug(f"Not in git work tree: {std_err.strip()}")
        return False

    logging.debug(f"Git work tree check result: {is_inside_work_tree}")
    if is_inside_work_tree:
        return True
    return False


def get_folder_repository(git_folder, branch):
    kci_msg("git folder: " + str(git_folder))
    logging.info(f"Getting repository info from folder: {git_folder}")
    if git_folder:
        current_folder = git_folder
    else:
        current_folder = os.getcwd()

    logging.debug(f"Current folder: {current_folder}")

    previous_folder = os.getcwd()
    if os.path.isdir(current_folder):
        os.chdir(current_folder)
        logging.debug(f"Changed to directory: {current_folder}")
    else:
        os.chdir(previous_folder)
        logging.error(f"Invalid directory: {current_folder}")
        kci_err("Not a folder")
        raise click.Abort()
    dot_git_folder = os.path.join(current_folder, ".git")
    if is_inside_work_tree():
        while not os.path.exists(dot_git_folder):
            current_folder = os.path.join(current_folder, "..")
            dot_git_folder = os.path.join(current_folder, ".git")
            logging.debug(f"Looking for .git in parent: {current_folder}")

    # Check if we are in a git repository
    if os.path.exists(dot_git_folder):
        logging.info(f"Found .git folder at: {dot_git_folder}")
        # Get remote origin url
        git_config_path = os.path.join(dot_git_folder, "config")
        git_config = configparser.ConfigParser(strict=False)
        git_config.read(git_config_path)
        git_url = git_config.get('remote "origin"', "url")
        logging.debug(f"Raw git URL from config: {git_url}")
        # A way of standardize git url for API call
        git_url = repository_url_cleaner(git_url)

        # Get current branch name
        cmd = ["git", "branch", "--show-current"]
        logging.debug(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        branch_name, branch_err = process.communicate()
        branch_name = branch_name.strip()
        if process.returncode != 0:
            logging.error(f"Failed to get branch name: {branch_err}")
        else:
            logging.debug(f"Current branch: {branch_name}")

        if branch:
            logging.info(f"Overriding branch from {branch_name} to {branch}")
            branch_name = branch

        # Get last commit hash
        cmd = ["git", "rev-parse", "HEAD"]
        logging.debug(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        last_commit_hash, commit_err = process.communicate()
        last_commit_hash = last_commit_hash.strip()
        if process.returncode != 0:
            logging.error(f"Failed to get commit hash: {commit_err}")
        else:
            logging.debug(f"Current commit: {last_commit_hash}")

        os.chdir(previous_folder)
        logging.info(
            f"Repository info - URL: {git_url}, Branch: {branch_name}, Commit: {last_commit_hash}"
        )
        kci_msg("tree: " + git_url)
        kci_msg("branch: " + branch_name)
        kci_msg("commit: " + last_commit_hash)
        return git_url, branch_name, last_commit_hash
    else:
        os.chdir(previous_folder)
        logging.error(f"No .git folder found at: {dot_git_folder}")
        kci_err("Not a GIT folder")
        raise click.Abort()


def get_current_branch_name(git_folder):
    """Get the current branch name from a git repository."""
    logging.debug(f"Getting branch name from: {git_folder}")
    if git_folder:
        current_folder = git_folder
    else:
        current_folder = os.getcwd()

    previous_folder = os.getcwd()
    if os.path.isdir(current_folder):
        os.chdir(current_folder)
    else:
        logging.warning(f"Invalid directory for branch check: {current_folder}")
        os.chdir(previous_folder)
        return None

    if is_inside_work_tree():
        cmd = ["git", "branch", "--show-current"]
        logging.debug(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        branch_name, err = process.communicate()
        branch_name = branch_name.strip()
        if process.returncode == 0:
            logging.info(f"Current branch: {branch_name}")
        else:
            logging.error(f"Failed to get branch: {err}")
        os.chdir(previous_folder)
        return branch_name
    else:
        logging.debug("Not in a git work tree")
        os.chdir(previous_folder)
        return None


def get_current_commit_hash(git_folder):
    """Get the current commit hash from a git repository."""
    logging.debug(f"Getting commit hash from: {git_folder}")
    if git_folder:
        current_folder = git_folder
    else:
        current_folder = os.getcwd()

    previous_folder = os.getcwd()
    if os.path.isdir(current_folder):
        os.chdir(current_folder)
    else:
        logging.warning(f"Invalid directory for commit check: {current_folder}")
        os.chdir(previous_folder)
        return None

    if is_inside_work_tree():
        cmd = ["git", "rev-parse", "HEAD"]
        logging.debug(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        commit_hash, err = process.communicate()
        commit_hash = commit_hash.strip()
        if process.returncode == 0:
            logging.info(f"Current commit: {commit_hash}")
        else:
            logging.error(f"Failed to get commit: {err}")
        os.chdir(previous_folder)
        return commit_hash
    else:
        logging.debug("Not in a git work tree")
        os.chdir(previous_folder)
        return None


def get_repository_url(git_folder):
    """Get the repository URL from a git repository."""
    logging.debug(f"Getting repository URL from: {git_folder}")
    if git_folder:
        current_folder = git_folder
    else:
        current_folder = os.getcwd()

    previous_folder = os.getcwd()
    if os.path.isdir(current_folder):
        os.chdir(current_folder)
    else:
        logging.warning(f"Invalid directory for URL check: {current_folder}")
        os.chdir(previous_folder)
        return None

    dot_git_folder = os.path.join(current_folder, ".git")
    if is_inside_work_tree():
        while not os.path.exists(dot_git_folder):
            current_folder = os.path.join(current_folder, "..")
            dot_git_folder = os.path.join(current_folder, ".git")
            logging.debug(f"Looking for .git in parent: {current_folder}")

    if os.path.exists(dot_git_folder):
        git_config_path = os.path.join(dot_git_folder, "config")
        logging.debug(f"Reading git config from: {git_config_path}")
        git_config = configparser.ConfigParser(strict=False)
        git_config.read(git_config_path)
        try:
            git_url = git_config.get('remote "origin"', "url")
            git_url = repository_url_cleaner(git_url)
            logging.info(f"Repository URL: {git_url}")
            os.chdir(previous_folder)
            return git_url
        except Exception as e:
            logging.error(f"Failed to get repository URL: {e}")
            os.chdir(previous_folder)
            return None
    else:
        logging.debug(f"No .git folder found at: {dot_git_folder}")
        os.chdir(previous_folder)
        return None


def get_latest_commit(origin, giturl, branch):
    logging.info(
        f"Fetching latest commit for {giturl} branch {branch} from origin {origin}"
    )
    trees = dashboard_fetch_tree_list(origin, False)
    logging.debug(f"Retrieved {len(trees)} trees from dashboard")

    for t in trees:
        if t["git_repository_url"] == giturl and t["git_repository_branch"] == branch:
            commit = t["git_commit_hash"]
            logging.info(f"Found latest commit: {commit}")
            return commit

    logging.error(f"Tree {giturl} with branch {branch} not found in dashboard")
    kci_err("Tree and branch not found.")
    raise click.Abort()


def set_giturl_branch_commit(origin, giturl, branch, commit, latest, git_folder):
    logging.info("Setting git URL, branch, and commit parameters")
    # Fill in any missing parameters from local git repository
    if not giturl:
        logging.debug(
            "No git URL provided, attempting to determine from local repository"
        )
        giturl = get_repository_url(git_folder)
        if not giturl:
            logging.error("Failed to determine git URL from local repository")
            kci_err("No git URL provided and could not determine from local repository")
            raise click.Abort()

    if not branch:
        logging.debug(
            "No branch provided, attempting to determine from local repository"
        )
        branch = get_current_branch_name(git_folder)
        if not branch:
            logging.error("Failed to determine branch from local repository")
            kci_err("No branch provided and could not determine from local repository")
            raise click.Abort()

    if not commit and not latest:
        logging.debug(
            "No commit provided, attempting to determine from local repository"
        )
        commit = get_current_commit_hash(git_folder)
        if not commit:
            logging.error("Failed to determine commit from local repository")
            kci_err("No commit provided and could not determine from local repository")
            raise click.Abort()

    # Print the final values
    logging.info(
        f"Final parameters - URL: {giturl}, Branch: {branch}, Commit: {commit if commit else 'latest'}"
    )
    kci_msg("git folder: " + str(git_folder))
    kci_msg("tree: " + giturl)
    kci_msg("branch: " + branch)
    if commit:
        kci_msg("commit: " + commit)

    if latest:
        logging.info("Fetching latest commit from dashboard")
        commit = get_latest_commit(origin, giturl, branch)
        kci_msg("commit: " + commit)

    return giturl, branch, commit
