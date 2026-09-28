# AstroBase: Vendor ↔ RFQ Scoring

Scores a vendor profile against a stored RFQ (Request for Quotation). Pick an RFQ, paste or upload
a vendor profile, and get an **alignment score out of 100, three supporting reasons and two gaps**.
Past evaluations are listed below, most recent first.

The AI makes **one LLM call per evaluation** and judges each RFQ requirement separately, quoting the
vendor text as evidence. **The score itself is computed in code** from those judgements, so every
point is traceable. Details: [How scoring works](#how-scoring-works) and [`BUILD_LOG.md`](BUILD_LOG.md).

Stack: Python + FastAPI · SQLite · OpenAI via LangChain · Vite + TypeScript · Docker Compose.

---

## Prerequisites

- **Docker Desktop** (or Docker Engine with Compose v2)
- **An OpenAI API key.** The default model is `gpt-6-luna`; any OpenAI chat model that supports
  Structured Outputs will work.

To run without Docker instead: Python 3.11+ (tested on 3.13) and Node.js LTS (tested on 22).

## Quick start (Docker)

```bash
git clone https://github.com/KSAP02/AstroBase.git
cd AstroBase
cp .env.example .env              # PowerShell: Copy-Item .env.example .env
```

Edit `.env` and set your OpenAI key (no quotes, no inline comments):

```
LLM_API_KEY=sk-...your key...
```

`.env.example` already sets `LLM_MODEL=gpt-6-luna` and `LLM_REASONING_EFFORT=low`; change them only
if you want a different model.

Then:

```bash
docker compose up --build
```

- App: **http://localhost:5173**
- API: http://localhost:8000 (interactive docs at http://localhost:8000/docs)

The three RFQs are loaded into the database automatically on first start. Stop with `Ctrl+C` or
`docker compose down`. Evaluation history is kept in `data_warehouse/astrobase.db` on your machine.

**Port already in use?** Set `BACKEND_PORT=8001` and/or `FRONTEND_PORT=5174` in `.env` and run
`docker compose up --build` again.

## Environment variables

All live in the root `.env` (gitignored). `.env.example` lists every key.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `LLM_API_KEY` | **yes** | – | OpenAI API key. Read only by the backend. |
| `LLM_MODEL` | **yes** | `gpt-6-luna` in `.env.example` | Model id, e.g. `gpt-6-luna` (or `gpt-6-sol` for a stronger, pricier model) |
| `LLM_REASONING_EFFORT` | no | `low` in `.env.example` | `none`, `low`, `medium`, `high`, `xhigh`. `low` is recommended (same results as `medium` in testing, about 2× faster). |
| `LLM_PROVIDER` | no | `openai` | Only `openai` is implemented |
| `LLM_BASE_URL` | no | OpenAI's endpoint | Only for Azure OpenAI, a proxy or an OpenAI-compatible server |
| `DB_PATH` | no | `data_warehouse/astrobase.db` | SQLite file, relative to the repo root |
| `BACKEND_PORT` | no | `8000` | Host port for the API (Docker only) |
| `FRONTEND_PORT` | no | `5173` | Host port for the web app (Docker only) |

## Seed data

- **Automatic:** the API creates the tables and loads `data_warehouse/seed/rfqs.json` every time it
  starts. Existing RFQs are skipped, so this is safe to repeat.
- **Manual command** (does the same):
  - Docker: `docker compose exec backend python -m backend.seed`
  - Without Docker: `python -m backend.seed`
- **Reset everything:** stop the app and delete `data_warehouse/astrobase.db`; the next start recreates
  it with the three RFQs and an empty history.

## Running without Docker

Backend (from the repo root):

```bash
python -m venv .venv
source .venv/bin/activate            # Windows Git Bash: source .venv/Scripts/activate
                                     # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                 # then set LLM_API_KEY
python -m backend.seed               # optional; also runs on startup
uvicorn backend.main:app --reload --port 8000
```

Frontend (second terminal):

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173, proxies /api to http://127.0.0.1:8000
```

If the backend runs on a different port, point the proxy at it first:
`VITE_PROXY_TARGET=http://127.0.0.1:8001 npm run dev` (PowerShell: `$env:VITE_PROXY_TARGET="http://127.0.0.1:8001"; npm run dev`).

## Using the app

1. Choose an RFQ from the dropdown; its requirements are shown underneath.
2. Paste a vendor profile, or click **Upload .txt** (sample profiles are in `data_warehouse/samples/`).
3. Click **Evaluate** (one AI call, usually 10–20 s).
4. Read the score, the 3 reasons and 2 gaps, and expand **Per-requirement breakdown** to see each
   requirement's verdict and the exact quote it's based on. A red banner shows when a mandatory
   requirement isn't met.
5. Past evaluations appear below, newest first. Click a row to reopen it.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check (used by the Docker healthcheck) |
| GET | `/api/rfqs` | RFQ list for the dropdown |
| GET | `/api/rfqs/{id}` | One RFQ in full |
| POST | `/api/evaluations` | `{"rfq_id": "RFQ-001", "vendor_text": "..."}` → score, reasons, gaps, per-requirement verdicts |
| GET | `/api/evaluations?limit=20` | Past evaluations, newest first |

Errors return `{"detail": "..."}`: 422 (empty or too-long text), 404 (unknown RFQ),
503 (LLM not configured, e.g. missing key), 502 (the LLM call failed).

## How scoring works

1. The RFQ is split into labelled requirement lines: mandatory (M), technical including material,
   quantity and delivery (T), required (R), preferred (P).
2. **One LLM call** returns, per line, a verdict (`met`, `partial`, `not_met`, `not_evidenced`,
   `not_applicable`) with a verbatim quote from the vendor profile, plus 3 reasons and 2 gaps.
   Prompts: [`backend/prompts/`](backend/prompts/).
3. **Code** ([`backend/agents/scoring.py`](backend/agents/scoring.py)) then:
   - downgrades any `met`/`partial` whose quote isn't actually in the vendor text,
   - weights tiers technical 40 / required 35 / preferred 25 (`met` = 1, `partial` = 0.5),
   - caps the score at **30** if any mandatory requirement isn't met.

Results for all 9 sample combinations are in [`BUILD_LOG.md`](BUILD_LOG.md#scoring-approach) and
[`experiments/`](experiments/).

## Project layout

```
backend/            FastAPI app
  main.py           routes and startup (wiring only)
  config.py         settings from .env (the only reader)
  db.py             SQLite: rfqs + evaluations tables
  seed.py           python -m backend.seed
  model.py          the only place the LLM client is built
  schemas.py        Pydantic models (API + LLM output)
  prompts/          prompt templates (.md) + PROMPT_VERSION
  agents/
    evaluator.py    RFQ → criteria → one LLM call → score
    scoring.py      pure scoring rules
frontend/           Vite + TypeScript single page
data_warehouse/     seed/ (rfqs.json), samples/ (vendor profiles), astrobase.db (created at runtime)
experiments/        scoring_sanity.py, run_matrix.py and their reports
MD_files/           spec copy, design plan, step-by-step build explainers (build_logs/)
BUILD_LOG.md        decisions, what broke, working with AI
AI_SESSION_TRANSCRIPT.jsonl   the full Claude Code session that built this (one JSON record per line)
```

## Checks

```bash
python experiments/scoring_sanity.py                     # scoring rules with hand-made verdicts (no API calls)
python experiments/run_matrix.py http://localhost:8000   # all 9 vendor × RFQ pairs via the running API (~$0.01)
```
