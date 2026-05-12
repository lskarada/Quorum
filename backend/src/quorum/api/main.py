"""FastAPI app entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from quorum.api.routes import router

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
