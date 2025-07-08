default:
    @just -l

dev-run-web:
    uv run server.py --reload

dev-run-server:
    cd web && pnpm dev

dev:
    @overmind s
