from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.routers import (
    anomalies,
    consent,
    customers,
    dataset,
    distress,
    explain,
    features,
    recommend,
    simulate,
)

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

# Serve the review UI from the API itself so it is same-origin: no CORS
# negotiation, and no file:// sandbox restrictions on fetch.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")


@app.get("/api/v1/health")
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
