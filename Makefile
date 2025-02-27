test:
	uv run --no-sync --project . pytest --disable-warnings -random-order-seed=seed -s -r tests/

format-and-lint:
	uv run --no-sync --project . ruff check --select I --fix
	uv run --no-sync --project . ruff format
	uv run --no-sync --project . ruff check --fix
