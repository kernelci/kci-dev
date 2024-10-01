#!/bin/bash

poetry run black  .
poetry run isort .
poetry run pytest -rP
