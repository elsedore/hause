"""FastAPI application entry point."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api.locations import router as locations_router
from backend.app.api.predictions import router as predictions_router

app = FastAPI(
    title="House Price Prediction API",
    description="API foundation for the house price prediction application.",
    version="0.1.0",
)
app.include_router(predictions_router)
app.include_router(locations_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "healthy"}


default_frontend_dist = Path(__file__).resolve().parents[2] / "frontend_dist"
frontend_dist = Path(os.getenv("FRONTEND_DIST", str(default_frontend_dist)))
if os.getenv("SERVE_FRONTEND") == "true" and frontend_dist.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=frontend_dist, html=True),
        name="frontend",
    )
else:

    @app.get("/")
    def read_root() -> dict[str, str]:
        """Return a simple API welcome message during local API development."""
        return {"message": "House Price Prediction API", "status": "ok"}
