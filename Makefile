.PHONY: all build

all: .venv/.make_success

ifeq ($(OS), Windows_NT)
activate=.venv/Scripts/activate
PYTHON27?=C:/Python27/python.exe
else
activate=.venv/bin/activate
PYTHON27?=python2.7
endif

.venv/.make_success: requirements.txt dev-requirements.txt .venv
	. $(activate) &&\
		python -m pip install -U pip &&\
		pip install -r requirements.txt -r dev-requirements.txt
	echo > .venv/.make_success

.venv:
	virtualenv .venv --python=$(PYTHON27)

build: .venv/.make_success
	rm -rf build
	. $(activate) && python setup.py sdist bdist_wheel
