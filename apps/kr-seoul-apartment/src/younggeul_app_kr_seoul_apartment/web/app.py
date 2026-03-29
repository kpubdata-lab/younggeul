from __future__ import annotations

from fastapi import FastAPI

from .routes.baseline import router as baseline_router
from .routes.health import router as health_router
from .routes.simulate import router as simulate_router
from .routes.snapshot import router as snapshot_router


def create_app() -> FastAPI:
    app = FastAPI(title="영끌 시뮬레이터", version="0.2.0")
    app.include_router(health_router)
    app.include_router(simulate_router)
    app.include_router(snapshot_router)
    app.include_router(baseline_router)
    return app
