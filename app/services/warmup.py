"""Model warm-up (demo readiness).

The Cox survival model and the XGBoost need-match classifier are trained
lazily on first use, which costs 25-45 seconds. That is fine for a batch job
and unacceptable for a live demo: the first person to press a button pays the
entire training cost while watching a spinner.

Warm-up runs in a background thread at startup so the server becomes ready
immediately and the cost is paid before anyone clicks. It is deliberately
fault-tolerant — an unseeded database or a failed fit must not prevent the
API from starting, since /health and the customer endpoints still work
without a trained model.
"""

from __future__ import annotations

import logging
import threading
import time

from app.database.connection import SessionLocal
from app.database.models import Customer

logger = logging.getLogger(__name__)

_state: dict = {"status": "cold", "seconds": None, "error": None}


def status() -> dict:
    return dict(_state)


def _warm() -> None:
    started = time.time()
    _state.update(status="warming", error=None)
    db = SessionLocal()
    try:
        if db.query(Customer).count() == 0:
            _state.update(status="skipped_no_data", seconds=0.0)
            logger.warning("model warm-up skipped: no customers seeded")
            return

        # Imported here rather than at module scope so that importing this
        # module never drags in the ML stack.
        from app.models.need_match import get_or_train_need_model
        from app.models.survival import get_or_train_model

        get_or_train_model(db)
        get_or_train_need_model(db)

        elapsed = round(time.time() - started, 1)
        _state.update(status="warm", seconds=elapsed, error=None)
        logger.info("model warm-up complete in %ss", elapsed)
    except Exception as exc:
        _state.update(
            status="failed",
            seconds=round(time.time() - started, 1),
            error=f"{type(exc).__name__}: {exc}",
        )
        logger.exception("model warm-up failed")
    finally:
        db.close()


def start_warmup() -> None:
    """Kick off warm-up without blocking server startup."""
    thread = threading.Thread(target=_warm, name="model-warmup", daemon=True)
    thread.start()
