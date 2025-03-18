import gzip
import os
import re

import requests
from libs.common import kci_err

INVALID_FILE_CHARS = re.compile(r'[\\/:"*?<>|]+')


def to_valid_filename(filename):
    return INVALID_FILE_CHARS.sub("", filename)


def download_logs_to_file(log_url, log_file):
    try:
        log_gz = requests.get(log_url)
        log = gzip.decompress(log_gz.content)
        log_file = to_valid_filename(log_file)
        with open(log_file, mode="wb") as file:
            file.write(log)
        log_path = "file://" + os.path.join(os.getcwd(), log_file)
        return log_path
    except:
        kci_err(f"Failed to fetch log {log_url}.")
