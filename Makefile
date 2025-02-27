test:
	uv run --no-sync --project . pytest --disable-warnings -random-order-seed=seed -s -r tests/

format-and-lint:
	uv run --no-sync --project . ruff check --select I --fix
	uv run --no-sync --project . ruff format
	uv run --no-sync --project . ruff check --fix

publish-test:
	uv build
	@if [ -z "$(PYPI_TEST_TOKEN)" ]; then echo "Error: TEST_PYPI_TOKEN is not set"; exit 1; fi
	uv publish --publish-url https://test.pypi.org/legacy/ --token ${PYPI_TEST_TOKEN}

publish:
	uv build
	@if [ -z "$(TEST_PYPI_TOKEN)" ]; then echo "Error: TEST_PYPI_TOKEN is not set"; exit 1; fi
	uv publish --token ${PYPI_TOKEN}
