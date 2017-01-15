.PHONY: clean-pyc clean-build docs clean

develop:clean-pyc install test

install:
	python setup.py install

test:
	python tests/test.py

clean: clean-pyc clean-test

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '*.c' -exec rm -f {} +
