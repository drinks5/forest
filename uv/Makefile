HTTPPARSERVERSION = 2.7.1
HTTPPARSERVERSIONSTRING = v$(HTTPPARSERVERSION)
HTTPPARSER = http-parser-$(HTTPPARSERVERSION)

dev-env: $(HTTPPARSER)
	pip install -e .
	pip install tox

test: test-binding test-http-parser

test-binding: dev-env
	tox

test-http-parser: $(HTTPPARSER)
	make -C $(HTTPPARSER) test

$(HTTPPARSER): $(HTTPPARSER).tar.gz
	tar -xzf $(HTTPPARSER).tar.gz

$(HTTPPARSER).tar.gz:
	curl -L https://github.com/joyent/http-parser/archive/$(HTTPPARSERVERSIONSTRING).tar.gz > $(HTTPPARSER).tar.gz

clean:
	python setup.py --quiet clean
	rm -rf .tox build dist $(HTTPPARSER) $(HTTPPARSER).tar.gz *.egg *.egg-info
	find . -name "*.pyc" -delete
	find . -name "*.so" -delete
	find . -path "*__pycache__*" -delete

.PHONY: dev-env test test-binding test-http-parser clean
