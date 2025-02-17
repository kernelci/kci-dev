#!/bin/bash

poetry run black . --extend-exclude="kcidev-src"
poetry run isort . --extend-skip="kcidev-src"
poetry run pytest -rP --ignore="kcidev-src"
