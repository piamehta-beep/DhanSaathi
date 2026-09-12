import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.onboarding import OnboardingSession, advance

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

# In-memory session store. Onboarding sessions are short-lived conversational
# state that is discarded once complete, not customer records — the masked
# result would be written to `customers` on completion in a real flow. Keeping
# them out of the database also means a half-finished KYC attempt leaves no
# persistent trace of the identifiers it collected.
_sessions: dict[str, OnboardingSession] = {}


class StartRequest(BaseModel):
    language: str = "hi"
    customer_name: str | None = None


class MessageRequest(BaseModel):
    message: str


@router.post("/start", status_code=200)
def start(req: StartRequest):
    session_id = str(uuid.uuid4())
    session = OnboardingSession(
        session_id=session_id,
        language=req.language,
        customer_name=req.customer_name,
    )
    _sessions[session_id] = session
    return {
        "session_id": session_id,
        "step": session.step,
        "message": session.prompt(),
        "progress": session.progress,
    }


@router.post("/{session_id}/message")
def message(session_id: str, req: MessageRequest):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail={"error": "session_not_found"})
    return advance(session, req.message)


@router.get("/{session_id}")
def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail={"error": "session_not_found"})
    return {
        "session_id": session.session_id,
        "language": session.language,
        "step": session.step,
        "progress": session.progress,
        "collected": session.collected,
    }
