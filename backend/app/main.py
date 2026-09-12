from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas import HealthResponse
from app.database.connection import get_db
from app.routers import (
    anomalies,
    auth,
    chat,
    consent,
    customers,
    dataset,
    distress,
    enquiry,
    explain,
    features,
    onboarding,
    recommend,
    simulate,
    support,
    user_input,
)
from app.services.warmup import start_warmup
from app.services.warmup import status as warmup_status

app = FastAPI(title="DhanSaathi API", version=settings.model_version)

# The review frontend is a static file opened directly from disk, so its
# origin is "null". This is a local debugging surface for a prototype; a
# deployment would pin allow_origins to the real frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(dataset.router)
app.include_router(customers.router)
app.include_router(features.router)
app.include_router(simulate.router)
app.include_router(distress.router)
app.include_router(anomalies.router)
app.include_router(recommend.router)
app.include_router(explain.router)
app.include_router(consent.router)
app.include_router(onboarding.router)
app.include_router(enquiry.router)
app.include_router(auth.router)
app.include_router(user_input.router)
app.include_router(chat.router)
app.include_router(support.router)

# Serve the review UI from the API itself so it is same-origin: no CORS
# negotiation, and no file:// sandbox restrictions on fetch. This is the
# backend's own debugging surface; the product frontend lives in ../frontend
# and is a separate app.
REVIEW_UI_DIR = Path(__file__).resolve().parent.parent / "review_ui"
if REVIEW_UI_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=REVIEW_UI_DIR, html=True), name="ui")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Send the root URL somewhere useful.

    Opening localhost:8010 is the first thing anyone does, and a bare 404
    gives no hint that the app lives at /ui and /docs.
    """
    return RedirectResponse(url="/ui/")


@app.on_event("startup")
def _on_startup() -> None:
    if settings.warm_models_on_startup:
        start_warmup()


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "unavailable"

    return {
        "status": "healthy",
        "database": db_status,
        "model_version": settings.model_version,
        "models": warmup_status(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
