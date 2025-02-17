#!/bin/bash

poetry run black . --extend-exclude="kcidev_src"
poetry run isort . --extend-skip-glob="kcidev_src"
poetry run pytest -rP
