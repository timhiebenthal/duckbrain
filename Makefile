.PHONY: build publish

build:
	rm -rf dist/
	uv build

publish: build
	uv publish --token $$PYPI_TOKEN
