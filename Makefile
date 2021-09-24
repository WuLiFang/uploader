.PHONY: default build

default: .venv build

vendor/.make.sentinel: ./scripts/update-vendor.sh
	$<
	touch $@

.venv:
	virtualenv .venv --python 2.7

.venv/.make.sentinel: .venv dev-requirements.txt vendor/.make.sentinel
	. ./scripts/activate-venv.sh &&\
		python -m pip install -U -r dev-requirements.txt
	touch $@

build: .venv/.make.sentinel
	. ./scripts/activate-venv.sh &&\
		python ./setup.py build bdist_wheel
	# https://github.com/pypa/setuptools/issues/1871
	rm -rf build/lib

