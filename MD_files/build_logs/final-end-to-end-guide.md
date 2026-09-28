# AstroBase: the complete end-to-end guide

One document to understand the whole project: the problem, the data, how evaluation works (by hand and
with the LLM), how the LLM system is designed and where its prompts live, and exactly how the app
starts and how every piece connects. The per-step files (`step-0` … `step-6`) go deeper on each part;
the interview Q&A is in [`interview-qa.md`](interview-qa.md).

---

## 1. The problem statement

### In plain words
An aerospace company wants to buy something (machined brackets, a coating service, titanium sheet)
and writes down exactly what it needs in an **RFQ** (Request for Quotation). Suppliers answer with a
**vendor profile**: who they are, their machines, certificates, customers and lead times.

A buyer then has to answer: **"Can this supplier actually do this job, and how sure am I?"**

**AstroBase does that first read.** You pick an RFQ, give it a vendor profile, and it returns:
- an **alignment score out of 100**,
- **three supporting reasons**,
- **two gaps**,
- and keeps a list of **past evaluations, most recent first**.

### What the SPEC requires (`MD_files/SPEC.md`)
| Requirement | Where it's met |
|---|---|
| RFQs stored in a database, seeded with the three provided | SQLite `rfqs` table, seeded on startup / `python -m backend.seed` |
| Pick an RFQ from a dropdown | Frontend `<select>` ← `GET /api/rfqs` |
| Upload or paste a vendor profile | Textarea + `.txt` upload (read in the browser) |
| Backend invokes an AI agent, **one LLM call per evaluation** | `evaluator.evaluate_vendor()` → one `chain.invoke()` |
| Score /100, 3 reasons, 2 gaps | `scoring.compute_score()` + `pick_reasons()` / `pick_gaps()` |
| Past evaluations, newest first | SQLite `evaluations` table ← `GET /api/evaluations` |
| Secrets in env vars; seed via command or first run; README; BUILD_LOG; ≥ 5 commits | `.env` (gitignored), both seeding paths, README, BUILD_LOG, 8 commits |
| Single page, no auth, no deployment; no RAG, no multi-agent, no tests/CI | Respected |

### What's *really* being tested
The BUILD_LOG asks: **"What did you do to make that number mean something?"** The three sample
vendors are written as traps for a naive "rate this vendor out of 100" prompt:

| Vendor | What they're like | A naive LLM would… |
|---|---|---|
| **A: Sundar Precision** | Excellent machinist, beats every RFQ-001 spec, **but no AS9100D** (only ISO 9001 + IATF 16949, the automotive standard) | give ~85 |
| **B: Arcline Aerospace** | **Has AS9100D**, but no 5-axis, ±0.05 mm, Ra 3.2, 9–11 weeks, max order 120 | be impressed by the name and certificate |
| **C: Vector Industrial** | Pure marketing: "tightest tolerances", "aerospace standards", "accredited partners"; **names no certificate, machine, number or customer** | say it matches all three RFQs |

Our answer: **the LLM judges each requirement separately and must quote its evidence; code computes the number and enforces the rules.**

---

## 2. The data: what exists, where, and how it flows

### 2.1 The RFQs: `data_warehouse/seed/rfqs.json`
Three RFQs, each shaped like this (RFQ-001 shown):
```json
{
  "id": "RFQ-001",
  "title": "Precision CNC Machining, Aluminium Structural Brackets",
  "category": "Machining",
  "quantity": "250 units",
  "material": "7075-T6 aluminium, supplied free-issue",
  "delivery": "6 weeks from PO",
  "technical": ["Tolerance +/-0.02 mm on critical features", "Surface finish Ra 1.6", "5-axis machining capability"],
  "mandatory": ["AS9100D certification"],
  "required":  ["CMM inspection with first-article inspection report per AS9102", "Material traceability to mill test certificate"],
  "preferred": ["In-house CMM", "Prior aerospace structural work", "NADCAP-accredited subcontractors for any outsourced process steps"]
}
```
| RFQ | Buying | Mandatory |
|---|---|---|
| RFQ-001 | CNC machining, 250 × 7075-T6 aluminium brackets, 6 weeks | AS9100D |
| RFQ-002 | Chromate conversion coating, MIL-DTL-5541 Type II Class 1A, 10 working days | NADCAP for Chemical Processing |
| RFQ-003 | Ti-6Al-4V titanium sheet, AMS 4911, ~2 t/year rate contract | Mill test certs traceable to heat lot |

The `RFQ-00x.md` files are the same content for humans. They differ slightly from the JSON (RFQ-002's
`.md` has no Technical section), so **`rfqs.json` is the source of truth**.

### 2.2 The vendor profiles: `data_warehouse/samples/vendor-{a,b,c}.txt`
Plain text, used as **test inputs**. You paste or upload them in the UI. They are **not** stored as seed data.

### 2.3 The database: `data_warehouse/astrobase.db` (SQLite, created at runtime, gitignored)
```sql
rfqs        (id TEXT PK, title, category, data TEXT)          -- data = the full RFQ JSON
evaluations (id INTEGER PK AUTOINCREMENT, rfq_id → rfqs.id, vendor_name, vendor_text,
             score, gate_passed (0/1), result TEXT, model, prompt_version, created_at TEXT)
```
- **`rfqs`** is **input for the backend**. The evaluator loads the RFQ from here, not from the JSON file. It's
  stored as one JSON blob because we never query *inside* an RFQ; `id`, `title` and `category` are
  real columns for the dropdown.
- **`evaluations`** is the history list **and an audit trail**. `result` holds
  `{"evaluation": <the API response>, "raw": {"content": <model's JSON>, "usage": <tokens>}}`, so any past
  score can be explained later, including under which `model` and `prompt_version`.

### 2.4 How the data moves
```
rfqs.json ──(startup seed, INSERT OR IGNORE)──▶ rfqs table ──get_rfq()──▶ build_criteria() ──▶ criteria lines
vendor text (paste/upload) ─────────────────────────────────────────────────────────────┐
criteria lines + vendor text ──▶ prompt ──▶ ONE LLM call ──▶ verdicts + quotes ──▶ compute_score() ──▶ result
result + raw model output ──▶ evaluations table ──list_evaluations()──▶ history list in the UI
```

### 2.5 From RFQ JSON to "criteria" (`evaluator.build_criteria`)
The RFQ is flattened into labelled lines the LLM judges one by one. Material, quantity and delivery
become **technical** lines. RFQ-001 becomes:

| Id | Tier | Requirement |
|---|---|---|
| M1 | mandatory | AS9100D certification |
| T1 | technical | Tolerance +/-0.02 mm on critical features |
| T2 | technical | Surface finish Ra 1.6 |
| T3 | technical | 5-axis machining capability |
| T4 | technical | Material: 7075-T6 aluminium, supplied free-issue |
| T5 | technical | Quantity: 250 units |
| T6 | technical | Delivery: 6 weeks from PO |
| R1 | required | CMM inspection with first-article inspection report per AS9102 |
| R2 | required | Material traceability to mill test certificate |
| P1 | preferred | In-house CMM |
| P2 | preferred | Prior aerospace structural work |
| P3 | preferred | NADCAP-accredited subcontractors for any outsourced process steps |

**Dedupe:** tiers are walked in priority order (mandatory → technical → required → preferred), and a line
whose normalised text contains, or is contained in, one already kept is dropped. That catches RFQ-002's
"Ability to handle parts up to 600 mm" (preferred) duplicating "Parts up to 600 mm" (technical). It
doesn't catch RFQ-003's differently worded cut-to-size pair, which is known and documented.

---

## 3. How the evaluation works

### 3.1 The principle
> **The LLM reads and judges; code does the maths and enforces the rules.**

The LLM never outputs the score. It outputs one **verdict per requirement line**, each with a
**verbatim quote** from the vendor profile:

| Verdict | Meaning | Points |
|---|---|---|
| `met` | A specific fact in the profile satisfies the line | 1.0 |
| `partial` | Specific fact, but falls short (e.g. CMM exists but is outsourced) | 0.5 |
| `not_met` | The profile shows they **can't** (e.g. "No 5-axis capability") | 0 |
| `not_evidenced` | Not addressed, or only vague marketing | 0 |
| `not_applicable` | The line's precondition doesn't exist for this vendor | left out of the average |

Why: a single "rate out of 100" number can't be checked, explained or reproduced. Per-line verdicts
with quotes can be checked (by code and by a human), and the number built from them is traceable to every point.

### 3.2 The scoring rules: `backend/agents/scoring.py` (pure Python, no I/O)
```python
TIER_WEIGHTS   = {"technical": 40, "required": 35, "preferred": 25}
VERDICT_POINTS = {"met": 1.0, "partial": 0.5, "not_met": 0.0, "not_evidenced": 0.0}
GATE_CAP       = 30
NEEDS_EVIDENCE = {"met", "partial"}
```
`compute_score(criteria, verdicts, vendor_text)` does four things:
1. **`apply_verdicts`**: pairs each of *our* criteria with the model's verdict, then corrects it:
   - no verdict for this id → `not_evidenced` (silence is never a pass)
   - `met`/`partial` whose quote **isn't in the vendor text** → `not_evidenced` (`quote_found` + `normalise`
     compare after lowercasing, `±` → `+/-`, removing quote marks, collapsing whitespace)
   - mandatory marked `not_applicable` → `not_met` (the gate can't be dodged)
2. **`score_tiers`**: per tier, weight × average points over the applicable lines. If a tier has none,
   its weight is shared out proportionally so the total stays out of 100.
3. **Raw score** = sum of tier points, rounded.
4. **Gate:** any mandatory line not `met` → `score = min(raw, 30)`.

**Worked example (hand-made verdicts, vendor A × RFQ-001):** technical 0.9 × 40 = 36, required 1.0 × 35 = 35,
preferred 0.5 × 25 = 12.5 → raw **84** → AS9100D not met → **30**.

### 3.3 Evaluation by hand: `experiments/scoring_sanity.py`
Tests the **rules** with verdicts written by hand (no LLM, no cost, known correct answers):
- 6 synthetic cases, each isolating one rule (everything met = 100; gate caps to 30; invented quote downgraded;
  preferred all N/A → weight redistributed; skipped lines → not_evidenced; mandatory N/A → not_met).
- 3 real cases with exact quotes from the sample files: A × RFQ-001 (84 → 30), B × RFQ-001 (30, gate ✓), and A
  with a paraphrased quote (downgraded, 84 → 76).

Run: `python experiments/scoring_sanity.py` → "All scoring checks passed."

### 3.4 Evaluation by the LLM: `backend/agents/evaluator.py`
The same `compute_score()` runs, but the verdicts now come from `gpt-6-luna`:

| | By hand | By LLM |
|---|---|---|
| Criteria | typed by hand | `build_criteria(rfq)` from the DB |
| Verdicts | typed carefully | one structured LLM call |
| Vendor text | sample file | whatever the user pastes/uploads |

What the LLM adds, and what handles it:

| LLM behaviour | Caught by |
|---|---|
| Paraphrased or invented quote | **code** (`quote_found` → downgrade) |
| Skipped line / invented id / invented verdict | **code** / **schema** (`Literal` → JSON-schema enum) |
| Mandatory marked N/A | **code** |
| Wrong judgement with a *real* quote (e.g. "9 to 11 weeks" → partial) | **prompt rules** + a human reading the verdicts |
| Vague claim counted as met/partial ("multi-axis") | **prompt rules** (v2) |
| Slight variation run to run (no temperature 0) | **design**: per-line scoring limits the swing to a few points |

Reasons and gaps come from the LLM too, then code makes them consistent:
- `pick_reasons`: drops reasons about unknown ids or lines the code downgraded, keeps 3, and pads from met/partial lines if short.
- `pick_gaps`: forces a failed mandatory line to be gap #1, keeps 2, and pads from not_met/not_evidenced lines if short.

### 3.5 The evidence: all 9 combinations with the real model (`experiments/matrix_v2_low.md`)
| Vendor | RFQ-001 machining | RFQ-002 coating | RFQ-003 titanium |
|---|---|---|---|
| **A** strong, no AS9100D | **30** (raw 77, gate ✗) | 0 | 12 |
| **B** AS9100D, can't make the part | **38** (gate ✓) | 0 | 12 |
| **C** marketing only | **0** | **0** | **0** |

A is capped but its raw 77 shows the strength; B earns only what it evidences; C's claims earn nothing;
machine shops score near zero on coating and titanium. The first prompt version gave C 7–11, which is
how v2 was born (see 4.4).

---

## 4. The LLM system design

### 4.1 Overview
```
.env (LLM_MODEL, LLM_API_KEY, LLM_REASONING_EFFORT, LLM_BASE_URL)
   │ read only by
config.py ──get_settings()──▶ model.py ──get_chat_model()──▶ ChatOpenAI(...)
                                                               │
prompts/evaluator_system.md ─┐                                 │  .with_structured_output(LLMEvaluation)
prompts/evaluator_user.md ───┴─▶ ChatPromptTemplate ──── | ────┘
                                         chain = prompt | llm
                                         chain.invoke({...})   ★ one call ★
                                                 │
                            {"parsed": LLMEvaluation, "raw": AIMessage, "parsing_error": ...}
```

### 4.2 The model and the seam: `backend/model.py`
- **The only file that constructs an LLM client** (CLAUDE.md rule: model/provider choice is config, not code).
- Checks config first and raises `LLMConfigError` with an exact fix ("LLM_API_KEY is empty; set it in .env") → API 503.
- Imports `langchain_openai` inside the function → a missing package becomes a clear message, not a startup crash.
- `ChatOpenAI(model, api_key, base_url or None, reasoning_effort or None, max_retries=0, timeout=120)`:
  - **Model `gpt-6-luna`**: chosen after listing the models the key can access, checking the pricing page
    ($0.10 / $0.50 per 1M tokens) and running a trap question on Luna and Sol. About **$0.001 per evaluation**.
  - **No `temperature`**: GPT-6 models are reasoning models and reject `temperature=0` with a 400.
  - **`reasoning_effort=low`**: the dial for reasoning models (`none | low | medium | high | xhigh`). `low` gave the
    same 9-run pattern as `medium` at about half the latency (10–14 s).
  - **`max_retries=0`**: the SDK's default is 2 silent retries, which could turn one evaluation into 3 calls.
  - **`timeout=120`**: a stuck call can't hang the API.

### 4.3 The prompts: `backend/prompts/`
| File | Role |
|---|---|
| `evaluator_system.md` | The **rubric**: verdict definitions, evidence rules, judgement rules, reasons/gaps rules |
| `evaluator_user.md` | The **template**: `{rfq_id}`, `{rfq_title}`, `{criteria_block}`, `{vendor_text}` |
| `__init__.py` | `load_prompt(name)` reads the `.md`; `PROMPT_VERSION = "v2"` is stored with every evaluation |

The rubric's judgement rules, and the trap each targets:

| Rule | Targets |
|---|---|
| Specific beats general; marketing claims → `not_evidenced` | Vendor C |
| `partial` needs specific evidence too (**v2**) | Vendor C getting `partial` for "multi-axis" etc. |
| Certificates must match exactly (ISO 9001 / IATF 16949 ≠ AS9100D; "accredited partners" ≠ NADCAP) | Vendor A, vendor C |
| Tighter tolerance meets looser; **lower Ra is finer** (0.8 meets 1.6; 3.2 doesn't) | Vendors A and B |
| Lead time "from receipt of material" ≠ "from PO" → at best partial | Vendor A |
| Different line of business → mostly not_met / not_evidenced | A and B on RFQ-002 and RFQ-003 |
| Evidence copied **character for character**, "..." to join fragments | Paraphrasing (seen in the first smoke test) |
| Exactly 3 reasons, 2 gaps; failed mandatory first; honesty over invented strengths | SPEC output + vendor C |

The user template wraps the vendor text in `<<<VENDOR_PROFILE … VENDOR_PROFILE>>>` markers so the model
can tell our instructions from the vendor's words. The `{…}` placeholders are LangChain template
variables, which is why the rubric contains no curly braces.

### 4.4 Structured output: the LLM's answer is a validated object
`schemas.py` defines exactly what the model must return:
```python
class CriterionVerdict(BaseModel): criterion_id: str; verdict: Literal[5 values]; evidence: str; rationale: str
class Finding(BaseModel):          criterion_id: str; text: str
class LLMEvaluation(BaseModel):    vendor_name: str; criteria: list[CriterionVerdict]; reasons: list[Finding]; gaps: list[Finding]
```
- `.with_structured_output(LLMEvaluation, method="json_schema", strict=True, include_raw=True)` sends this as a
  **JSON schema** in the same single request; OpenAI's strict mode guarantees the reply matches it.
- The `Field(description=...)` texts go into the schema, so they're instructions to the model ("copy the exact sentence…").
- `include_raw=True` returns the validated object **and** the raw message (content + token usage) for the audit trail.

### 4.5 Why this design, and what was deliberately not done
- **One call, no agent loop.** The SPEC says one LLM call per evaluation, and the task is a single judgement over
  one document. Tools, memory, multi-step agents or RAG would add cost and failure points with no benefit here (and RAG/multi-agent are out of scope).
- **LangChain, used thinly:** a prompt template and structured output only. The raw OpenAI SDK would be ~15 lines
  more; LangChain keeps the prompt files and the provider swap tidy.
- **Prompt versioning:** v1 → v2 was driven by *reading* the 9-run verdicts (vendor C earned `partial` from
  marketing phrases). Every stored evaluation records its prompt version.
- **Failure handling:** `LLMConfigError` → 503, any call failure or schema mismatch → `LLMCallError` → 502. No retries,
  no partial results saved.

---

## 5. The exact pipeline: how the app starts and how everything connects

### 5.1 Configuration flow
```
.env  ──(Compose env_file)──▶ backend container env ──▶ config.Settings ──get_settings()──▶ db.py, model.py, evaluator.py
.env  ──(Compose ${...} substitution)──▶ BACKEND_PORT / FRONTEND_PORT host ports
compose `environment:` ──▶ frontend container VITE_PROXY_TARGET=http://backend:8000 ──▶ vite.config.ts proxy
```
The key reaches only the backend container. It's not in any image (`.dockerignore`), not in git (`.gitignore`), and never sent to the browser.

### 5.2 `docker compose up --build`, step by step
1. **Build the backend image** (`backend/Dockerfile`, context = repo root): `python:3.13-slim` → `pip install -r requirements.txt`
   → copy `backend/` and `data_warehouse/seed/`. `.dockerignore` keeps `.env`, the venv and the DB out.
2. **Build the frontend image** (`frontend/Dockerfile`): `node:lts-slim` → `npm install` → copy the frontend source.
3. **Start the backend container:** `.env` injected as environment variables; `./data_warehouse` mounted at
   `/app/data_warehouse`; host port `${BACKEND_PORT:-8000}` → 8000; runs
   `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
4. **Backend boot** (inside that container):
   1. uvicorn imports `backend.main`. `main.py` imports `db` (→ `config`), `agents.evaluator` (→ `scoring`, `schemas`,
      `model`, `prompts`, LangChain core), `model`, `schemas`. Modules are only *defined* at this point.
   2. `app = FastAPI(lifespan=lifespan)`; each `@app.get/post` registers a route.
   3. **Startup (`lifespan`):** `db.init_db()` → first `get_settings()` call (reads env, caches) → create
      `data_warehouse/` and both tables (`CREATE TABLE IF NOT EXISTS`); `db.seed_rfqs()` → read `rfqs.json` →
      `INSERT OR IGNORE` × 3.
   4. uvicorn listens on 8000 → "Application startup complete".
5. **Healthcheck:** every 5 s Compose runs `python -c "urllib.request.urlopen('http://localhost:8000/api/health')"`
   inside the container → `healthy`.
6. **Start the frontend container** only after the backend is `healthy` (`depends_on: condition: service_healthy`):
   runs `vite --host 0.0.0.0` on 5173 with `VITE_PROXY_TARGET=http://backend:8000`.

### 5.3 Opening the page (http://localhost:5173)
1. Vite serves `index.html` → `src/main.ts` (bundled on the fly with `style.css`).
2. `main.ts` runs `Promise.all([loadRfqs(), loadHistory()])`:
   - `getRfqs()` → `GET /api/rfqs` → **Vite proxy** → `backend:8000` → `db.list_rfqs()` → dropdown filled.
   - then `onRfqChange()` → `getRfq(id)` → `GET /api/rfqs/{id}` → `db.get_rfq()` → tier lists rendered.
   - `getEvaluations()` → `GET /api/evaluations?limit=20` → `db.list_evaluations()` → history table.

### 5.4 One click on **Evaluate**, file by file
```
[browser] main.ts evaluateBtn click
   busy=true (button disabled), status "Evaluating…"
   api.evaluate(rfqId, text) → fetch POST /api/evaluations {rfq_id, vendor_text}
        │
[vite :5173] proxy /api → http://backend:8000
        │
[uvicorn] → FastAPI matches POST /api/evaluations → main.create_evaluation(req)
   1. Body validated against schemas.EvaluationRequest (strip, 1..20 000 chars)   → 422 if bad
   2. db.get_rfq(req.rfq_id)                                                      → 404 if unknown
   3. evaluator.evaluate_vendor(rfq, vendor_text)
        a. build_criteria(rfq)                → [M1, T1..T6, R1, R2, P1..P3]
        b. load_prompt("evaluator_system"), load_prompt("evaluator_user") → ChatPromptTemplate
        c. model.get_chat_model()             → ChatOpenAI(gpt-6-luna, effort low, retries 0) → 503 if misconfigured
        d. .with_structured_output(LLMEvaluation, json_schema, strict, include_raw)
        e. chain.invoke({...})                ★ THE ONE OPENAI REQUEST ★ (~10–15 s)       → 502 on failure
        f. parsed LLMEvaluation (or 502 if it doesn't match the schema)
        g. scoring.compute_score(criteria, parsed.criteria, vendor_text)
             apply_verdicts (quote check, missing ids, mandatory N/A) → score_tiers → raw → gate
        h. pick_reasons (3) + pick_gaps (2)
        i. return EvaluationOut (+ raw content/usage)
   4. db.insert_evaluation(evaluation, vendor_text, raw) → (id, created_at)      [SQLite row]
   5. return evaluation + id + created_at → JSON 200
        │
[browser] renderResult(ev): score box, gate banner (with raw score), 3 reasons, 2 gaps,
          tier bars, per-requirement table (verdict, ⚠ if downgraded, quote, rationale)
          loadHistory() → GET /api/evaluations → the new row is on top
          busy=false
```

### 5.5 Module map and import direction (no cycles)
```
config.py ◀── db.py ◀────────────────────────────────┐
config.py ◀── model.py ◀── agents/evaluator.py ◀──── main.py
schemas.py ◀── agents/scoring.py ◀── agents/evaluator.py
prompts/  ◀── agents/evaluator.py
config.py, db.py ◀── seed.py
```
| File | One-line job |
|---|---|
| `backend/main.py` | Wiring: startup + 5 routes + error translation |
| `backend/config.py` | The only `.env` reader; paths resolved from the repo root |
| `backend/db.py` | All SQL: tables, seeding, RFQ reads, evaluation insert/list |
| `backend/seed.py` | `python -m backend.seed` |
| `backend/model.py` | The only place the LLM client is built |
| `backend/schemas.py` | Pydantic shapes: scoring types, LLM output schema, API request/response |
| `backend/prompts/` | Rubric + template + `PROMPT_VERSION` |
| `backend/agents/evaluator.py` | RFQ → criteria → one LLM call → score → 3 reasons / 2 gaps |
| `backend/agents/scoring.py` | Pure scoring rules |
| `frontend/src/api.ts` | Typed fetch helpers, readable errors |
| `frontend/src/main.ts` | DOM wiring and rendering, HTML escaping |
| `frontend/vite.config.ts` | Dev server + `/api` proxy |
| `docker-compose.yml` | Two services, env, volume, ports, healthcheck, startup order |
| `experiments/scoring_sanity.py` | Rules checked with hand-made verdicts |
| `experiments/run_matrix.py` | 9 vendor × RFQ runs through the live API → Markdown report |

---

## 6. Where to change what (live-modification cheat sheet)

| Change | Where | Then |
|---|---|---|
| Tier weights, `partial` value, gate cap | `scoring.py` constants | `python experiments/scoring_sanity.py` (update expected numbers), rebuild |
| Gate = zero instead of cap | `scoring.py`: `GATE_CAP = 0` (or `score = 0 if not gate_passed`) | same |
| Model or reasoning effort | `.env` `LLM_MODEL` / `LLM_REASONING_EFFORT` | `docker compose up -d --force-recreate` (env is read at container start) |
| Another provider | `model.py` (new branch) + `requirements.txt` + `LLM_PROVIDER` | `docker compose up --build` |
| A prompt rule | `prompts/evaluator_system.md` + bump `PROMPT_VERSION` | rebuild, rerun `run_matrix.py` |
| New field in the LLM output (e.g. confidence) | `schemas.py` `CriterionVerdict` + `ScoredCriterion`, pass it through in `scoring.apply_verdicts`, one prompt line, show it in `main.ts` | rebuild |
| 4 reasons instead of 3 | `evaluator.N_REASONS` + prompt + `LLMEvaluation` description | rebuild |
| Filter history by RFQ | `db.list_evaluations(limit, rfq_id)` + `main.list_evaluations` query param + `api.ts` | rebuild |
| Add a 4th RFQ | append to `rfqs.json` | restart (seeding skips existing ids). Editing an existing RFQ needs a DB reset |
| Any backend/frontend code change | – | `docker compose up --build` (no live reload in containers) |

---

## 7. Deep dive: how the model and the checks really work

Answers to the questions worked through after the build, in the order a request actually flows.

### 7.1 How the database is set up and used
- **One SQLite file**, `data_warehouse/astrobase.db`. Its path comes from `config.py` (`db_path`, resolved from the repo root; `/app` in Docker, mapped to your disk by the volume).
- **Two tables** (`db.py`, the `SCHEMA` string):
  - `rfqs(id PK, title, category, data)`: three columns for the dropdown, plus the **whole RFQ as JSON** in `data`.
  - `evaluations(...)`: one row per completed evaluation, with the full response and raw model output in `result`.
- **Initialised automatically at startup** (`main.py` → `lifespan`): `db.init_db()` creates the folder and runs `CREATE TABLE IF NOT EXISTS` for both tables; `db.seed_rfqs()` reads `rfqs.json` and runs `INSERT OR IGNORE` for each RFQ (existing ids are skipped, so it's safe to repeat). The same two calls run by hand with `python -m backend.seed`.
- **`get_conn()`** wraps every DB call: open → `row_factory = sqlite3.Row` (rows act like dicts) → foreign keys on → commit on success → always close.
- After seeding, `rfqs.json` isn't used again: **the `rfqs` table is the source of truth**.

### 7.2 What `yield` does (in `lifespan` and `get_conn`)
`yield` **pauses** a function and hands control back; the function **resumes after `yield`** later. With `@asynccontextmanager` / `@contextmanager`, that becomes "setup → pause → cleanup":
- `lifespan`: before `yield` = startup (tables + seed); **the pause = the server running**; after `yield` = shutdown (nothing needed).
- `get_conn`: before = open the connection; `yield conn` = hand it to the `with` block; after = commit (on success) and **always** close.

### 7.3 Flattening the RFQ into the prompt happens in memory, per request
On every Evaluate click, inside the request:
1. `main.py`: `rfq = db.get_rfq(id)` → the JSON from the `data` column becomes a Python dict.
2. `evaluator.py`: `criteria = build_criteria(rfq)` → a list of `Criterion(id, tier, text)` (M1, T1…T6, R1, R2, P1…P3), deduped.
3. The prompt files are read from `backend/prompts/`; `chain.invoke({...})` fills `{criteria_block}` with one line per criterion (`T1 [technical] Tolerance +/-0.02 mm…`), plus the RFQ id/title and the delimited vendor text, and sends it: **the one LLM call**.
4. The **same in-memory list** is reused by `compute_score`, so scoring covers exactly the lines the model was shown.

| Thing | Stored? |
|---|---|
| The RFQ | ✅ `rfqs.data` |
| The flattened criteria list | ❌ rebuilt on every request (cheap, never stale) |
| The filled-in prompt text | ❌ not saved (can be rebuilt from the RFQ, the saved vendor text, the prompt files and `prompt_version`) |
| Each line's final verdict, quote, rationale | ✅ inside `evaluations.result` |
| The model's raw answer and token usage | ✅ `evaluations.result.raw` |

### 7.4 Who produces what

| Piece | Produced by |
|---|---|
| Requirement lines (M1, T1 …) | **Code**: `build_criteria()` |
| Verdict per line | **The LLM** |
| Evidence quote per line | **The LLM**: copied from the vendor text in the prompt |
| Rationale per line | **The LLM** |
| 3 reasons, 2 gaps (first draft) | **The LLM** |
| "Is the quote really in the profile?" | **Code**: `quote_found()` |
| Final verdicts, score, gate, final reasons/gaps | **Code** |

The UI's per-requirement table is the **LLM's judgement, audited by code**: verdict + quote + rationale from the model, with ⚠ where code overrode it.

### 7.5 How the score is calculated, precisely
- **Each tier's lines are averaged first, then multiplied by that tier's weight**, and the three results are added: `tier points = weight × (sum of points ÷ number of applicable lines)`. It's *not* weight × each line. Averaging keeps each tier worth exactly 40 / 35 / 25 however many lines it has (one RFQ-001 technical line ≈ 40 ÷ 6 = 6.7 points; one required line = 35 ÷ 2 = 17.5).
- **Mandatory lines carry no points**; they only feed the gate.
- **`not_evidenced` counts as 0 and stays in the average**, so it pulls the score down exactly like `not_met` ("not shown" is treated as "can't do"; otherwise a vendor could raise its score by saying less). **Only `not_applicable` is skipped** from the average.

  Vendor A preferred: P1 met, P2 not_evidenced, P3 N/A → (1 + 0) ÷ 2 × 25 = **12.5**. If P2 were skipped it would be 25; if P3 were not_evidenced instead of N/A, 8.3 (this happened in a live run, one reason A's raw was 77 not 84).

### 7.6 The gate cap is a ceiling, not normalisation
```python
score = raw_score if gate_passed else min(raw_score, GATE_CAP)   # GATE_CAP = 30
```
- The raw score is **blind to mandatory requirements** (they have no weight). Without the cap, vendor A would show **84** while being legally unusable for RFQ-001.
- If any mandatory line isn't `met`, the final score **can't exceed 30**. Nothing is rescaled: 84 → 30, but 12 stays 12 and 0 stays 0.
- **`raw_score` is kept for explanation only** (the UI banner: "capped at 30, would have been 77"). It distinguishes "strong but missing a certificate" from "weak across the board". Decisions use `score`.
- **Why 30 and not 0:** with 0, vendor A and vendor C would both show 0. 30 is a policy value (one constant) meaning "clearly unsuitable, but not erased".

### 7.7 `NEEDS_EVIDENCE` and the quote check
`NEEDS_EVIDENCE = {"met", "partial"}`: the verdicts that **earn points**, so they must be proven. Negative verdicts earn nothing and aren't checked.

**How the check works:** it's a Ctrl+F. Code already has the vendor text the user submitted. It normalises both the vendor text and the LLM's quote (lowercase, `±` → `+/-`, remove quote marks, collapse whitespace/line breaks, strip edge punctuation), splits the quote at `...`, and tests each piece with Python's substring operator (`piece in vendor_text`). Not found → `not_evidenced`, `downgraded=True` (⚠).

Run on vendor A's real file (the tolerance sentence is split across two lines in the file):

| LLM's quote | Found? | Result |
|---|---|---|
| `Routine working tolerance +/-0.01 mm on 5-axis work` | ✅ identical after normalising | stays met |
| `“Routine working tolerance ±0.01 mm on 5-axis work.”` | ✅ quotes, `±`, full stop are harmless | stays met |
| `Ra 0.8 is finer than the required Ra 1.6` | ❌ the model's own words | downgraded |
| `tolerance of ±0.01mm` | ❌ reworded | downgraded |
| `three DMG MORI 5-axis machines ... two Zeiss CONTURA CMMs` | ✅ each piece found | stays met |

**Regex's role is small:** it only tidies text inside `normalise` (removing quote marks, squashing whitespace) and splits on `...`. The actual check is a plain substring search, not pattern matching.

### 7.8 Every check code applies to the LLM's answer
1. **Shape (schema, strict structured output):** all fields present, verdict ∈ 5 allowed values; unparseable → 502, nothing saved.
2. **`apply_verdicts`** loops over **our** lines:
   - invented or duplicate ids are ignored;
   - a missing verdict becomes `not_evidenced`;
   - a `met`/`partial` without a real quote becomes `not_evidenced`;
   - a mandatory marked N/A becomes `not_met`.
3. **Reasons and gaps:** reasons about unknown or downgraded lines are dropped; a failed mandatory line is forced to gap #1; both are padded to exactly 3 and 2.

**What code cannot check:** whether a *real* quote justifies the verdict (e.g. "9 to 11 weeks" marked `partial` against "6 weeks from PO"). That relies on the prompt rules and a human reading the table.

### 7.9 Why not ask the LLM whether its quote exists?
- It's the suspect checking its own work: the model that paraphrased already "believes" it quoted correctly.
- LLMs are weak at character-exact matching and tend to say "yes" for near-paraphrases, exactly the case to catch.
- Code answers it with certainty, for free, in microseconds, the same way every time.
- A second call breaks the SPEC's one-call rule; an in-call `quote_exists: true` field would be self-grading.

Where an LLM check *would* add value is **judgement** ("does this real quote justify the verdict?"). That's handled by prompt rules inside the one call, and would be measured **offline** with a labelled evaluation set (the "Next 48 hours" plan), not with a second live call.
