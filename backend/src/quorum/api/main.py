"""FastAPI app entry point."""
from __future__ import annotations

import pathlib

from dotenv import load_dotenv

# Load .env from repo root if present so OPENROUTER_API_KEY etc. are picked up.
# Mirrors quorum/eval/cli.py. Done before quorum imports because module-level
# init (e.g. the LLM client) reads the env — without this, `make dev` boots but
# 500s on the first deliberation with "OPENROUTER_API_KEY not set".
_REPO_ROOT_ENV = pathlib.Path(__file__).resolve().parents[4] / ".env"
if _REPO_ROOT_ENV.exists():
    load_dotenv(_REPO_ROOT_ENV)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from quorum.api.routes import router  # noqa: E402

app = FastAPI(
    title="Quorum API",
    description="Multi-agent diagnostic deliberation, callable over HTTP.",
    version="0.1.0",
)

# Permissive CORS for local dev. Lock down for production.
# 3000 = pinned Vite port (see frontend/vite.config.ts).
# 5173 = Vite default, kept as fallback for `pnpm vite` invocations.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
