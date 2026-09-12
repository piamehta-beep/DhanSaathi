import uuid

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.synthetic_data.generator import generate_dataset

router = APIRouter(prefix="/api/v1/dataset", tags=["dataset"])


class GenerateRequest(BaseModel):
    n_customers: int = 1000
    seed: int = 42
    clear_existing: bool = True


@router.post("/generate", status_code=202)
def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(
        generate_dataset, n=req.n_customers, seed=req.seed, clear_existing=req.clear_existing
    )
    return {
        "job_id": job_id,
        "status": "started",
        "estimated_customers": req.n_customers,
        "estimated_transactions": req.n_customers * 1500,
    }
