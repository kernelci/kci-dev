#!/bin/bash

poetry run black . --extend-exclude="kcidev-src"
poetry run isort . --extend-skip="kcidev-src"
poetry run tox
