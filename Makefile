.PHONY: clean-pyc clean-build docs clean

develop:clean-pyc install tmp_test

tmp_test:
	python test.py

install:
	python setup.py install

uninstall:

test:
	python tests/test.py

clean: clean-pyc

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '*.c' -exec rm -f {} +
	find . -name '*.so' -exec rm -f {} +
	rm -rf build
	rm -rf dist 
	rm -rf *.egg-info
	rm -rf ~/.pyxbld

	pip uninstall -y forest || echo "pip uninstall failed"
