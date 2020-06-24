.PHONY: default build

default: .venv build

.venv: pyproject.toml poetry.lock
	poetry install
	touch .venv

build: .venv
	poetry build
