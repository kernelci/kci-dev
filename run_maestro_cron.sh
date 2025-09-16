#!/bin/bash

timestamp=$(date +"%Y_%m_%d-%H_%M_%S")
log_file="/var/log/cron-$timestamp.log"
cd /home/kernelci
poetry run kci-dev --settings kci-dev.toml maestro validate boots >> "$log_file" 2>&1
# python upload_log.py