# AstroBase — Build Plan (end to end)

The design document: what we're building, why it's shaped this way, and how every piece fits.
The ordered, time-boxed checklist lives in [`STEP_BY_STEP.md`](STEP_BY_STEP.md).
The original brief is `candidate-pack/SPEC.md` (moves to `MD_files/SPEC.md` in Step 0).

**Decided stack:** Python + FastAPI · minimal TypeScript frontend (Vite, no framework) · SQLite in
`data_warehouse/` · OpenAI via LangChain · prompts in `backend/prompts/` · mandatory-gate failure
caps the score at 30 · **Docker Compose** runs both servers locally (`docker compose up --build`).

---

## 0. The project in plain words

### What problem is this?

An aerospace company needs to buy something: 250 machined aluminium brackets, a coating service,
or titanium sheet. It writes down what it needs in a **Request for Quotation (RFQ)**. Suppliers
send back a **vendor profile**, a page describing who they are, what machines they own and which
certificates they hold.

A buyer then has to read each profile and ask one question: **"Can this supplier actually do this
job, and how sure am I?"** Our app does that first read automatically and gives a score out of 100,
3 reasons for the score and 2 gaps.

### What does an RFQ contain?

Each RFQ sorts its needs by how much they matter:

| Tier | Meaning | Example (RFQ-001) |
|---|---|---|
| **Mandatory** | Must have, or you're out, no matter what else you offer | AS9100D certification (the aerospace quality certificate) |
| **Technical** | The part has to come out right | ±0.02 mm tolerance, Ra 1.6 surface finish, 5-axis machines |
| **Quantity / delivery** | Can they make enough, fast enough? | 250 units in 6 weeks |
| **Required** | Expected; missing one is a serious problem | AS9102 first-article inspection report, material traceability |
| **Preferred** | Nice to have; breaks ties | In-house measuring machine (CMM), past aerospace work |

### What exactly is the LLM judging?

**Not** "give this vendor a score." Asked that way, an LLM reads a confident, well-written profile
and says "85/100, looks great", even if the vendor lacks the one certificate that disqualifies them.
That number means nothing: you can't check it, explain it or reproduce it.

Instead we ask the LLM a set of **small, checkable questions**, one per RFQ line:

> "RFQ line T1 says *Tolerance ±0.02 mm*. Does the vendor profile show they can do that?
> Answer `met`, `partial`, `not_met`, `not_evidenced` or `not_applicable`, **quote the exact sentence
> from the profile** that proves it, and give a one-line reason."

The LLM is good at this part: reading messy human text and matching it to a requirement,
understanding that "+/-0.01 mm" beats "±0.02 mm" and that "Ra 0.8" is a finer finish than "Ra 1.6".

**Plain Python then turns those answers into the number**, using fixed weights and a fixed rule for
mandatory items. So the score is **explainable** (every point traces back to a verdict and a quote),
**stable** (same verdicts, same score) and **easy to change** ("make preferred items worth less"
is one line of code, not a prompt rewrite).

The split in one line: **the LLM reads and judges; code does the maths and enforces the rules.**

### The five verdicts

| Verdict | Meaning | Points |
|---|---|---|
| `met` | The profile states a specific fact that satisfies the line, and we have the quote | 1.0 |
| `partial` | Close but not fully (e.g. CMM exists but is outsourced) | 0.5 |
| `not_met` | The profile shows they **can't** (e.g. "No 5-axis capability") | 0 |
| `not_evidenced` | The profile doesn't say, or only says it in vague marketing language | 0 |
| `not_applicable` | The line doesn't apply to this vendor (e.g. "NADCAP subcontractors for outsourced steps" when nothing is outsourced) | left out of the maths |

`not_met` and `not_evidenced` both score 0, but we keep them apart because a buyer cares about the
difference: "they told us they can't" vs "they didn't tell us".

### How do we know the score means something? (evaluation)

The three sample vendors were written as tests. Each one catches a different way a naive scorer fails:

| Vendor | What they're like | A naive LLM would… | What our design does |
|---|---|---|---|
| **A: Sundar Precision** | Excellent machinist: beats every RFQ-001 spec. **But has no AS9100D** (only automotive/ISO certificates) | Give ~85 because the technical part is impressive | Mandatory line fails → score **capped at 30**. Reasons still praise the technical strengths; gap #1 is "no AS9100D". |
| **B: Arcline Aerospace** | **Has AS9100D**, but no 5-axis, ±0.05 mm, Ra 3.2, lead time 9–11 weeks, never made more than 120 pieces | Get fooled by the aerospace name and certificate | Passes the gate, but technical lines come back `not_met` → **low-mid** score. |
| **C: Vector Industrial** | Pure marketing: "tightest tolerances", "aerospace standards", "accredited partners". **Names no certificate, machine, number or customer** | Say it matches all three RFQs, because it *claims* to do everything | Vague claims → `not_evidenced` → **low against all three RFQs**. |

Plus a cross-check: A and B are machine shops. Against RFQ-002 (coating) or RFQ-003 (titanium
supply) they should score **near zero**.

**How we evaluate it:** run all 9 combinations (3 vendors × 3 RFQs) and check the results match this
expected pattern (patterns, not exact numbers):

| | RFQ-001 machining | RFQ-002 coating | RFQ-003 titanium |
|---|---|---|---|
| **A** | ≤ 30 (gate fails, strong otherwise) | near 0 | near 0 |
| **B** | low-mid (gate passes, specs fail) | near 0 | near 0 |
| **C** | low | low | low |

For each run we also **read the per-line verdicts**, not just the number. A correct-looking score
built on a wrong verdict (e.g. "Ra 3.2 meets Ra 1.6") is still a bug. The 9-run table and any
wrong verdicts we find go into `BUILD_LOG.md` as evidence.

### Safeguards against the LLM getting it wrong

1. **Quote check (code).** Every `met`/`partial` must include a quote that really appears in the
   vendor text. If it doesn't (the LLM made it up), code downgrades it to `not_evidenced`.
2. **Specificity rule (prompt).** The quote check alone can't catch vendor C, because C's vague
   sentences *are* in the text. So the prompt says: `met` needs a specific fact, and phrases like
   "aligned with international aerospace standards" count as `not_evidenced`.
3. **Exact-certificate rule (prompt).** ISO 9001 / IATF 16949 ≠ AS9100D; "accredited partners" ≠ NADCAP.
4. **Direction rule (prompt).** Smaller tolerance and **lower Ra are better**. LLMs often get this backwards.
5. **Lead-time basis (prompt).** "4–5 weeks from receipt of material" isn't the same as "6 weeks from PO".
6. **Structured output.** The answer comes back as validated JSON with the same shape every time.
   (GPT-6 models are reasoning models and reject `temperature=0`; only the default is allowed. So
   run-to-run stability comes from the design instead: small per-line judgements plus a score computed in code.)
7. **Every run saves** the raw LLM output, the model name and the prompt version, so any score can be audited later.

---

## 1. Architecture

```
Browser (Vite + vanilla TS)
   │  fetch /api/*  (Vite dev-server proxy → no CORS setup needed)
   ▼
FastAPI  backend/main.py  (routes + error translation only)
   ├── db.py ──────────────▶ data_warehouse/astrobase.db  (sqlite3, no ORM)
   └── agents/evaluator.py
          ├── build_criteria(rfq)        RFQ JSON → flat list of ids (M1, T1, R1, P1…)
          ├── prompts/                   system + user templates, PROMPT_VERSION
          ├── model.py                   the ONLY place ChatOpenAI is constructed
          │     └── one structured LLM call  ──▶ OpenAI
          └── agents/scoring.py          pure Python: quote check, weights, gate → score
```

One request = one LLM call. No agent loop, no retries, no second "judge" call.

**At runtime (Docker Compose, §8):**
```
host :5173 ──▶ [frontend container]  Vite dev server ──proxy /api──▶ http://backend:8000
host :8000 ──▶ [backend container]   uvicorn backend.main:app
                                       └── ./data_warehouse mounted at /app/data_warehouse (DB survives restarts)
```

## 2. Final layout

```
backend/
  __init__.py
  config.py          Settings (pydantic-settings) + get_settings(); the only .env reader
  db.py              connect, init_db, seed_rfqs, list_rfqs, get_rfq, insert_evaluation, list_evaluations
  seed.py            `python -m backend.seed`, idempotent (also runs automatically on startup)
  model.py           get_chat_model() → ChatOpenAI(model, api_key, base_url, reasoning_effort, max_retries=0); clear error if key/model missing
  schemas.py         Pydantic models: API request/response + LLM output schema
  prompts/
    __init__.py      load_prompt(name) -> str, PROMPT_VERSION = "v1"
    evaluator_system.md
    evaluator_user.md
  agents/
    __init__.py
    evaluator.py     build_criteria, evaluate_vendor
    scoring.py       normalise, check_evidence, compute_score
  main.py            FastAPI app, lifespan (init_db + seed), routes
  Dockerfile         python:3.13-slim image for the API (build context = repo root)
frontend/
  Dockerfile         node:lts-slim image running the Vite dev server
  .dockerignore      node_modules, dist
  package.json, tsconfig.json, vite.config.ts, index.html
  src/main.ts        DOM wiring + rendering
  src/api.ts         typed fetch helpers
  src/style.css
data_warehouse/
  seed/rfqs.json (+ RFQ-00x.md)   moved from candidate-pack/
  samples/vendor-{a,b,c}.txt      moved from candidate-pack/
  astrobase.db                    created at runtime, gitignored
experiments/         9-combination run outputs (evidence for BUILD_LOG)
MD_files/            SPEC.md, BUILD_PLAN.md, STEP_BY_STEP.md
docker-compose.yml   backend + frontend services
.dockerignore        root-level (backend build context): .venv, astrobase_venv, node_modules, .env, *.db, .git
BUILD_LOG.md  README.md  requirements.txt  .env.example  .gitignore
```

Deleted as unused scaffolding: `mcp-server/` (CLAUDE.md: delete what the project doesn't need).

**Import direction (no cycles):**
`config ← db` · `config ← model` · `schemas ← scoring` ·
`prompts, model, schemas, scoring ← evaluator` · `config, db, evaluator, schemas ← main`.

## 3. Data model (SQLite)

```sql
CREATE TABLE IF NOT EXISTS rfqs (
  id        TEXT PRIMARY KEY,
  title     TEXT NOT NULL,
  category  TEXT NOT NULL,
  data      TEXT NOT NULL            -- full RFQ JSON
);

CREATE TABLE IF NOT EXISTS evaluations (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  rfq_id          TEXT NOT NULL REFERENCES rfqs(id),
  vendor_name     TEXT,
  vendor_text     TEXT NOT NULL,
  score           INTEGER NOT NULL,
  gate_passed     INTEGER NOT NULL,  -- 0/1
  result          TEXT NOT NULL,     -- JSON: verdicts, reasons, gaps, breakdown, raw LLM output
  model           TEXT NOT NULL,
  prompt_version  TEXT NOT NULL,
  created_at      TEXT NOT NULL      -- UTC ISO-8601
);
```

- Seeding: `INSERT OR IGNORE` from `data_warehouse/seed/rfqs.json`. `rfqs.json` is the source of
  truth; the `.md` files differ slightly (RFQ-002's `.md` has no Technical section).
- Seeds run on startup (FastAPI lifespan) **and** by hand via `python -m backend.seed`.
  Running either twice is harmless.

## 4. API

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/health` | – | `{"status": "ok"}` (used by the Docker healthcheck) |
| GET | `/api/rfqs` | – | `[{id, title, category}]` for the dropdown |
| GET | `/api/rfqs/{rfq_id}` | – | full RFQ (shown under the dropdown) |
| POST | `/api/evaluations` | `{rfq_id, vendor_text}` | full evaluation (below) |
| GET | `/api/evaluations` | `?limit=20` | past evaluations, all RFQs, newest first |

Evaluation response:
```json
{
  "id": 7, "rfq_id": "RFQ-001", "vendor_name": "Sundar Precision Works Pvt. Ltd.",
  "score": 30, "gate_passed": false, "raw_score": 78,
  "reasons": [{"criterion_id": "T1", "text": "..."}, "... x3"],
  "gaps":    [{"criterion_id": "M1", "text": "..."}, "... x2"],
  "criteria": [{"criterion_id": "M1", "tier": "mandatory", "text": "AS9100D certification",
                "verdict": "not_met", "evidence": "", "rationale": "...", "downgraded": false}],
  "breakdown": {"technical": 36.0, "required": 35.0, "preferred": 7.0},
  "model": "...", "prompt_version": "v1", "created_at": "2026-09-28T10:15:00Z"
}
```

Errors are translated into clear messages, never raw tracebacks:
`404` unknown RFQ · `422` empty or >20 000-char vendor text · `503` LLM not configured
("LLM_API_KEY is empty — set it in .env") · `502` the LLM call failed (message passed through).

**Uploads:** the browser reads the `.txt` file (FileReader) into the textarea, so paste and upload
share one backend path and no multipart endpoint is needed.

## 5. The evaluation pipeline in detail

### 5.1 `build_criteria(rfq) -> list[Criterion]` (evaluator.py)
- Flattens the RFQ into `{id, tier, text}`:
  - `M1..` mandatory
  - `T1..` technical, plus `Quantity: <quantity>` and `Delivery: <delivery>` added as technical lines
  - `R1..` required
  - `P1..` preferred
- **Dedupe:** tier order is mandatory > technical > required > preferred. A lower-tier item whose
  normalised text contains, or is contained in, a higher-tier item is dropped. This catches RFQ-002
  "Parts up to 600 mm" (technical) vs "Ability to handle parts up to 600 mm" (preferred). The RFQ-003
  "Cut-to-size capability" / "Ability to supply cut-to-size" overlap uses different words, so it isn't
  caught. We document it in BUILD_LOG instead.

### 5.2 Prompt (`backend/prompts/`)
- `evaluator_system.md` is the rubric: verdict definitions (§0 table) plus safeguards 2–5 and
  "return exactly 3 reasons and 2 gaps, each tied to a criterion id; if there are no real strengths,
  say so honestly rather than inventing one".
- `evaluator_user.md` is a template with `{rfq_id}`, `{rfq_title}`, `{criteria_block}` (one line per
  `ID [tier] text`) and `{vendor_text}` wrapped in clear delimiters.
- `prompts/__init__.py`: `load_prompt(name)` reads the `.md` file; `PROMPT_VERSION = "v1"` is bumped
  whenever the rubric changes, and every evaluation stores it.

### 5.3 The single LLM call (evaluator.py)
```python
prompt = ChatPromptTemplate.from_messages([("system", system_md), ("human", user_md)])
chain  = prompt | get_chat_model().with_structured_output(LLMEvaluation, method="json_schema", include_raw=True)
out    = chain.invoke({...})   # exactly one OpenAI request
```
LLM output schema (`schemas.py`):
```python
Verdict = Literal["met", "partial", "not_met", "not_evidenced", "not_applicable"]
class CriterionVerdict(BaseModel): criterion_id: str; verdict: Verdict; evidence: str; rationale: str
class Finding(BaseModel):          criterion_id: str; text: str
class LLMEvaluation(BaseModel):
    vendor_name: str
    criteria: list[CriterionVerdict]
    reasons: list[Finding]   # prompt asks for 3
    gaps: list[Finding]      # prompt asks for 2
```

### 5.4 Scoring (`agents/scoring.py`), pure and written by hand
```python
TIER_WEIGHTS = {"technical": 40, "required": 35, "preferred": 25}
VERDICT_POINTS = {"met": 1.0, "partial": 0.5, "not_met": 0.0, "not_evidenced": 0.0}
GATE_CAP = 30
```
1. **Normalise** text: lowercase, `±` → `+/-`, collapse whitespace, strip quotes/punctuation at the ends.
2. **Quote check:** for each `met`/`partial` verdict, the normalised evidence must be a substring of
   the normalised vendor text, otherwise the verdict becomes `not_evidenced` and `downgraded=True`.
   Criterion ids the LLM skipped become `not_evidenced`; ids we never sent are ignored.
3. **Tier score:** `tier_weight × mean(points)` over that tier's applicable criteria
   (`not_applicable` excluded). If a tier has no applicable criteria, its weight is redistributed
   proportionally across the other tiers.
4. **Raw score** = sum of tier scores, rounded to an int from 0 to 100.
5. **Gate:** if every mandatory criterion is `met` (after the quote check), then `gate_passed=True`.
   Otherwise `score = min(raw_score, 30)`. A mandatory item can't be `not_applicable`; that counts as a failure.
6. **Reasons/gaps:** trim to 3/2. If the model returned fewer, pad with deterministic text from the
   strongest `met` criteria (reasons) or the weakest criteria (gaps).

Returns `{score, raw_score, gate_passed, breakdown, criteria}`. It has no I/O, so it's easy to
explain and easy to change live.

### 5.5 Persist
`insert_evaluation(...)` stores the vendor text, score, gate, full result JSON (including the raw LLM
message), `model` and `PROMPT_VERSION`.

## 6. Frontend (minimal, decent)

One page, top to bottom:
1. **Header**: "AstroBase: Vendor ↔ RFQ Scoring".
2. **RFQ picker**: `<select>` filled from `GET /api/rfqs`; below it, the selected RFQ's tiers as small lists.
3. **Vendor profile**: `<textarea>` (monospace, about 14 rows) plus `<input type=file accept=".txt">`,
   which fills the textarea.
4. **Evaluate** button: disabled while the textarea is empty or a request is pending; shows "Evaluating…".
5. **Result card**: large score `NN / 100` (colour: green ≥ 70, amber 40–69, red < 40); red banner
   "Mandatory requirement not met: score capped at 30" when the gate fails; **3 reasons** and
   **2 gaps** as lists; a `<details>` "Per-requirement breakdown" table (id, tier, requirement,
   verdict, evidence quote).
6. **Past evaluations**: newest first. Each row shows time, RFQ id, vendor name, score and a gate
   badge. Clicking a row shows it in the result card. The list refreshes after every evaluation.
7. Errors from the API appear in a red line under the button.

Plain CSS: system font stack, max-width about 900 px, cards with a light border. No UI framework.

## 7. Configuration and dependencies

Root `.env` (gitignored) and `.env.example` (committed, same keys with no values). No inline comments:
```
LLM_PROVIDER=openai
LLM_MODEL=
LLM_API_KEY=
LLM_BASE_URL=
LLM_REASONING_EFFORT=medium
DB_PATH=data_warehouse/astrobase.db
```
- `LLM_MODEL`: **`gpt-6-luna`** (chosen 2026-09-28: $0.10 / $0.50 per 1M tokens, supports Structured
  Outputs, passed the Ra and vague-claim traps). Switch to `gpt-6-sol` by editing `.env` if verdicts are weak.
- `LLM_API_KEY`: your OpenAI key. Following CLAUDE.md §3, it's read only by `config.py` and passed
  to `ChatOpenAI(api_key=...)` in `model.py`.
- `LLM_BASE_URL`: blank = official OpenAI endpoint. Only set it for Azure, a proxy or an OpenAI-compatible local server.
- `LLM_REASONING_EFFORT`: `none | low | medium | high | xhigh` (what `gpt-6-luna` accepts; it rejects
  `minimal`). Blank = model default.

**Verified `model.py` boilerplate** (tested against langchain-openai 1.6.6 + gpt-6-luna):
```python
class LLMConfigError(RuntimeError):
    """The LLM isn't configured; the message says exactly what to fix."""

def get_chat_model():
    s = get_settings()
    if s.llm_provider != "openai":
        raise LLMConfigError(f"LLM_PROVIDER={s.llm_provider!r} is not supported; set LLM_PROVIDER=openai in .env")
    if not s.llm_api_key:
        raise LLMConfigError("LLM_API_KEY is empty; set it in .env")
    if not s.llm_model:
        raise LLMConfigError("LLM_MODEL is empty; set it in .env (e.g. gpt-6-luna)")
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise LLMConfigError("langchain-openai is not installed; run pip install -r requirements.txt") from e
    return ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key,
        base_url=s.llm_base_url or None,
        reasoning_effort=s.llm_reasoning_effort or None,
        max_retries=0,
        timeout=120,
    )
```
Why each argument:
- **No `temperature`:** GPT-6 models are reasoning models and return a 400 error for any value other than the default.
- **`reasoning_effort`** is the dial for reasoning models: how much the model thinks before answering.
  It's the Chat Completions form; LangChain's `reasoning={"effort": ...}` is the Responses-API form,
  which we don't need.
- **`max_retries=0`:** LangChain leaves this as `None`, so the OpenAI SDK's default of **2 automatic
  retries** applies. That could silently turn one evaluation into 3 API requests and break the SPEC's
  "one LLM call per evaluation". With 0, a failure surfaces as a clear 502 and the user can click again.
- **`timeout=120`:** an upper bound so a stuck request can't hang the API forever.
- `model.py` supports `openai` only for now. Any other provider value raises a clear
  "not implemented, set LLM_PROVIDER=openai" error.

`requirements.txt` (unpinned, flat):
```
fastapi
uvicorn[standard]
pydantic
pydantic-settings
langchain-core
langchain-openai
```
(The full `langchain` package isn't needed. `ChatPromptTemplate` is in `langchain-core`,
`ChatOpenAI` in `langchain-openai`.)

`frontend/package.json` dev dependencies: `vite`, `typescript`. Scripts: `dev`, `build`.

`frontend/vite.config.ts` reads the proxy target from an env var, so the same config works both
inside and outside Docker:
```ts
const target = process.env.VITE_PROXY_TARGET ?? "http://localhost:8000";
export default defineConfig({ server: { host: true, port: 5173, proxy: { "/api": target } } });
```

## 8. Docker: local startup with `docker compose up --build`

The primary way to run and test the app locally. The venv + npm path still works for quick debugging.

**`backend/Dockerfile`** (build context = repo root, because `requirements.txt` and
`data_warehouse/seed/` live there):
```dockerfile
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY data_warehouse/seed/ data_warehouse/seed/
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`frontend/Dockerfile`** (build context = `frontend/`):
```dockerfile
FROM node:lts-slim
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```
It runs the Vite dev server rather than nginx on purpose. The `/api` proxy then works the same as
it does locally, with no CORS setup and no second web-server config to explain.

**`docker-compose.yml`:**
```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./data_warehouse:/app/data_warehouse
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 5s
      timeout: 3s
      retries: 10

  frontend:
    build: ./frontend
    environment:
      VITE_PROXY_TARGET: http://backend:8000
    ports:
      - "5173:5173"
    depends_on:
      backend:
        condition: service_healthy
```

Design notes:
- **Secrets:** `env_file: .env` injects the key at runtime. `.env` is in `.dockerignore`, so it's
  never baked into an image. No inline comments in `.env` (Compose would keep them as part of the value).
- **DB persistence:** mounting `./data_warehouse` means `astrobase.db` lives on the host. History
  survives `docker compose down` and the same DB file is shared with the non-Docker run. Seeding still
  happens automatically on backend startup.
- **`DB_PATH=data_warehouse/astrobase.db`** is relative to `WORKDIR /app`, so it resolves the same
  inside and outside the container.
- **Startup order:** the frontend waits for the backend's `/api/health` healthcheck.
- **Two `.dockerignore` files:** root (backend context) excludes `.venv/`, `astrobase_venv/`,
  `node_modules/`, `.env`, `*.db`, `.git/`; `frontend/.dockerignore` excludes `node_modules/`, `dist/`.
- **Reload:** no bind-mounted source and no `--reload`. After a code change, run
  `docker compose up --build` again. Simple and predictable; fine for a 2-hour exercise.

**Run and test:**
```bash
cp .env.example .env            # fill LLM_API_KEY and LLM_MODEL
docker compose up --build       # backend :8000, frontend :5173
curl localhost:8000/api/health  # {"status":"ok"}
open http://localhost:5173
docker compose down             # DB file stays in data_warehouse/
```

## 9. What goes into BUILD_LOG (collect as we go)

- **Scoring approach:** §0 + §5.4, in five bullets.
- **Unclear spec:** duplicate "600 mm" and "cut-to-size" lines; JSON vs `.md` differences; always
  returning exactly 3/2; "AI agent" read as one structured call; history shows all RFQs; upload read
  client-side; `not_applicable` handling; lead-time basis.
- **Evidence:** the 9-combination table from `experiments/`.
- **Weakest part:** the `not_evidenced` vs vague-quote boundary depends on the prompt; cut-to-size
  double counting; the weights are judgement calls; one call means no retry.
- **Next 48 h:** a small labelled test set per RFQ + checks on verdict accuracy; handle semantic
  duplicates; show the reasoning for the gate in the UI.
