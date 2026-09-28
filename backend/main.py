"""FastAPI app: wiring only (startup + routes). Logic lives in db.py and agents/."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from backend import db


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
