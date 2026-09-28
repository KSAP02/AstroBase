"""FastAPI app: wiring only (startup + routes). Logic lives in db.py and agents/."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from backend import db
from backend.agents.evaluator import LLMCallError, evaluate_vendor
from backend.model import LLMConfigError
from backend.schemas import EvaluationOut, EvaluationRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts: make sure tables exist and the RFQs are loaded.
    db.init_db()
    db.seed_rfqs()
    yield  # the app serves requests here; nothing to clean up on shutdown


app = FastAPI(title="AstroBase", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/rfqs")
def list_rfqs() -> list[dict]:
    return db.list_rfqs()


@app.get("/api/rfqs/{rfq_id}")
def get_rfq(rfq_id: str) -> dict:
    rfq = db.get_rfq(rfq_id)
    if rfq is None:
        raise HTTPException(status_code=404, detail=f"RFQ {rfq_id} not found")
    return rfq


@app.post("/api/evaluations")
def create_evaluation(req: EvaluationRequest) -> EvaluationOut:
    # FastAPI has already validated the body against EvaluationRequest (422 if invalid).
    rfq = db.get_rfq(req.rfq_id)
    if rfq is None:
        raise HTTPException(status_code=404, detail=f"RFQ {req.rfq_id} not found")

    # Translate failures into clear HTTP errors instead of a 500 with a traceback.
    try:
        evaluation, raw = evaluate_vendor(rfq, req.vendor_text)
    except LLMConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LLMCallError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Persist everything (incl. raw model output, model id, prompt version) for history and auditing.
    eval_id, created_at = db.insert_evaluation(evaluation.model_dump(), req.vendor_text, raw)
    return evaluation.model_copy(update={"id": eval_id, "created_at": created_at})


@app.get("/api/evaluations")
def list_evaluations(limit: int = Query(20, ge=1, le=100)) -> list[EvaluationOut]:
    return db.list_evaluations(limit)
