default:
    @just -l

dev-run-web:
    cd web && pnpm dev

dev-run-server:
    uv run server.py --reload

dev:
    @overmind s

install-git-hooks:
    @mv .git/hooks/pre-commit .git/hooks/pre-commit.bak.$(date +%s) || true
    @cp scripts/pre-commit .git/hooks/pre-commit
    @echo "Pre-commit hooks updated"

langgraph-dev:
	uv run langgraph dev --allow-blocking

lint:
	uv run ruff check --fix

format:
	uv run ruff format

lint-format: lint format
    @echo "Done"

test:
    uv run pytest

coverage:
	uv run pytest --cov=src tests/ --cov-report=term-missing --cov-report=xml

