from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.routers import (
    anomalies,
    customers,
    dataset,
    distress,
    features,
    recommend,
    simulate,
)

app = FastAPI(title="DhanSaathi API", version=settings.model_version)
app.include_router(dataset.router)
app.include_router(customers.router)
app.include_router(features.router)
app.include_router(simulate.router)
app.include_router(distress.router)
app.include_router(anomalies.router)
app.include_router(recommend.router)


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
