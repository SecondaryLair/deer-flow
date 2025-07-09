default:
    @just -l

dev-run-web:
    uv run server.py --reload

dev-run-server:
    cd web && pnpm dev

dev:
    @overmind s

install-git-hooks:
    @mv .git/hooks/pre-commit .git/hooks/pre-commit.bak.$(date +%s) || true
    @cp scripts/pre-commit .git/hooks/pre-commit
    @echo "Pre-commit hooks updated"

langgraph-dev:
	uv run langgraph dev --allow-blocking

lint:
	uv run ruff format
	uv run ruff check --fix

coverage:
	uv run pytest --cov=src tests/ --cov-report=term-missing --cov-report=xml

