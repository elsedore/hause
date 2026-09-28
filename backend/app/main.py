"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.api.predictions import router as predictions_router

app = FastAPI(
    title="House Price Prediction API",
    description="API foundation for the house price prediction application.",
    version="0.1.0",
)
app.include_router(predictions_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Return a simple API welcome message."""
    return {"message": "House Price Prediction API", "status": "ok"}


@app.get("/health")
def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "healthy"}
