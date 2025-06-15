import gzip
import logging
import os
import re

import requests

from kcidev.libs.common import kci_err

INVALID_FILE_CHARS = re.compile(r'[\\/:"*?<>|]+')


def to_valid_filename(filename):
    cleaned = INVALID_FILE_CHARS.sub("", filename)
    if cleaned != filename:
        logging.debug(f"Cleaned filename: '{filename}' -> '{cleaned}'")
    return cleaned


def download_logs_to_file(log_url, log_file):
    logging.info(f"Downloading log from: {log_url}")
    logging.debug(f"Target file: {log_file}")
    try:
        # Download compressed log
        logging.debug("Fetching compressed log file")
        response = requests.get(log_url)
        response.raise_for_status()

        # Decompress log
        logging.debug(f"Downloaded {len(response.content)} bytes, decompressing")
        log = gzip.decompress(response.content)
        logging.debug(f"Decompressed to {len(log)} bytes")

        # Save to file
        log_file = to_valid_filename(log_file)
        logging.debug(f"Writing log to: {log_file}")
        with open(log_file, mode="wb") as file:
            file.write(log)

        log_path = "file://" + os.path.join(os.getcwd(), log_file)
        logging.info(f"Log saved successfully: {log_path}")
        return log_path
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download log from {log_url}: {e}")
        kci_err(f"Failed to fetch log {log_url}.")
    except gzip.BadGzipFile as e:
        logging.error(f"Failed to decompress log from {log_url}: {e}")
        kci_err(f"Failed to decompress log {log_url}.")
    except OSError as e:
        logging.error(f"Failed to write log file {log_file}: {e}")
        kci_err(f"Failed to write log file {log_file}.")
    except Exception as e:
        logging.error(f"Unexpected error downloading log from {log_url}: {e}")
        kci_err(f"Failed to fetch log {log_url}.")
