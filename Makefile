.PHONY: install dev eval mcp test lint clean

install:
	uv sync --all-packages
	cd frontend && pnpm install

dev:
	@echo "Starting API on :8000 and frontend on :3000"
	@(cd backend && uv run python scripts/serve_api.py) & \
	(cd frontend && pnpm dev) & \
	wait

eval:
	cd backend && uv run quorum-eval run --corpus medqa --panel dev_cheap --n 3

mcp:
	cd backend && uv run python -m quorum.mcp_server.server

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check src tests
	cd frontend && pnpm lint

clean:
	rm -rf backend/.venv frontend/node_modules frontend/.next frontend/dist
