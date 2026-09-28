# Step 2: Scoring rules (pure Python)

**Commit:** `Compute a gated, weighted score from per-requirement verdicts`
**Goal:** the code that turns per-requirement verdicts into a score out of 100, built and tested
with hand-made verdicts before any LLM is involved.

---

## Part 1: How everything connects, from `uvicorn` booting to a response

This is the whole backend as it stands after Step 2, in the order things actually happen.

### Phase A: Boot (`uvicorn backend.main:app`, or the Docker `CMD` that runs the same command)

```
uvicorn backend.main:app
   │
   ├─1─ Python imports the module "backend.main"
   │      (possible because backend/__init__.py makes "backend" a package)
   │
   │    main.py runs top to bottom:
   │      from fastapi import FastAPI, HTTPException
   │      from backend import db  ──────────────▶ db.py runs top to bottom:
   │                                                 from backend.config import get_settings ─▶ config.py runs:
   │                                                                                             ROOT_DIR = repo root (or /app)
   │                                                                                             class Settings defined
   │                                                                                             get_settings defined (NOT called yet)
   │                                                 SCHEMA string defined
   │                                                 get_conn, init_db, seed_rfqs, list_rfqs, get_rfq defined
   │      lifespan() defined (not run yet)
   │      app = FastAPI(title="AstroBase", lifespan=lifespan)   ← the app object
   │      @app.get("/api/health")        ┐
   │      @app.get("/api/rfqs")          ├ each decorator registers "path → function" in app's routing table
   │      @app.get("/api/rfqs/{rfq_id}") ┘
   │
   ├─2─ uvicorn takes the attribute "app" from that module (the ":app" part of the command)
   │
   ├─3─ uvicorn runs the app's startup → FastAPI enters lifespan() and runs the code before `yield`:
   │      db.init_db()
   │         └─ get_settings()  ← FIRST call: Settings() reads env vars, then .env, then defaults;
   │                              result cached by @lru_cache, so later calls reuse it
   │         └─ settings.db_file → ROOT_DIR / "data_warehouse/astrobase.db"
   │         └─ mkdir data_warehouse/ (if missing)
   │         └─ get_conn() → sqlite3.connect(...) → executescript(SCHEMA) → commit → close
   │      db.seed_rfqs()
   │         └─ read data_warehouse/seed/rfqs.json → 3 dicts
   │         └─ INSERT OR IGNORE each one → commit → close
   │      yield            ← "Application startup complete"
   │
   └─4─ uvicorn listens on port 8000 and waits for HTTP requests
```

**Not loaded at boot yet:** `schemas.py` and `agents/scoring.py`. Nothing in `main.py` imports them
until Step 3 adds the evaluation route. Python only runs a module when something imports it.

### Phase B: A request, e.g. `GET /api/rfqs/RFQ-002`

```
HTTP request arrives on port 8000
   │
   ├─ uvicorn parses the raw HTTP and hands it to the FastAPI app (via ASGI, the Python web-server interface)
   ├─ FastAPI matches the path against its routing table → get_rfq(rfq_id="RFQ-002")
   │    (the "{rfq_id}" part of the path becomes the function argument)
   ├─ get_rfq is a plain `def`, so FastAPI runs it in a worker thread (sqlite3 is blocking)
   ├─ db.get_rfq("RFQ-002")
   │    └─ get_settings() (cached) → get_conn() → SELECT data FROM rfqs WHERE id = ? → close
   │    └─ json.loads(row["data"]) → dict   (or None if no row)
   ├─ None?  → raise HTTPException(404) → FastAPI sends {"detail": "RFQ RFQ-002 not found"}
   └─ dict?  → FastAPI converts it to JSON → 200 response
```

### Phase C: What Step 3 adds (preview): the evaluation request end to end

```
POST /api/evaluations {rfq_id, vendor_text}
   ├─ FastAPI validates the body against EvaluationRequest (schemas.py)        → 422 if bad
   ├─ db.get_rfq(rfq_id)                                                      → 404 if unknown
   ├─ evaluator.build_criteria(rfq)        RFQ JSON → [Criterion M1, T1..T5, R1, R2, P1..P3]
   ├─ prompts/: fill the system + user templates with criteria and vendor text
   ├─ model.get_chat_model()               the one place ChatOpenAI is built    → 503 if not configured
   ├─ chain.invoke(...)                    ★ THE ONE LLM CALL ★                  → 502 if it fails
   │    └─ returns a validated LLMEvaluation (schemas.py): verdicts + quotes + 3 reasons + 2 gaps
   ├─ scoring.compute_score(criteria, verdicts, vendor_text)   ← THIS STEP's code
   │    └─ ScoreResult: score, raw_score, gate_passed, breakdown, per-line verdicts
   ├─ (Step 4) db.insert_evaluation(...)   saves everything, incl. model + prompt version
   └─ JSON response → the UI shows score, 3 reasons, 2 gaps
```

### Who imports whom (no cycles)
```
config.py  ◀── db.py  ◀── main.py
                 ◀──────── seed.py
schemas.py ◀── agents/scoring.py        (Step 3: evaluator imports scoring, schemas, model, prompts;
                                         main imports evaluator)
```

---

## Part 2: This step's files

### `backend/schemas.py`: the data shapes
Pydantic models are classes that **validate** data: creating one with a wrong type or a missing
field raises an error. Two groups:

| Model | Used by | Meaning |
|---|---|---|
| `Criterion(id, tier, text)` | scoring, evaluator | One RFQ line, e.g. `T2 / technical / "Surface finish Ra 1.6"` |
| `ScoredCriterion` | scoring output | A `Criterion` **plus** final `verdict`, `evidence`, `rationale`, `downgraded` |
| `TierScore(points, max)` | scoring output | e.g. technical `36.0 / 40.0` |
| `ScoreResult` | scoring output | `score`, `raw_score`, `gate_passed`, `breakdown`, `criteria` |
| `CriterionVerdict` | LLM output | The model's judgement on one line |
| `Finding` | LLM output | One reason or gap, tied to a criterion id |
| `LLMEvaluation` | LLM output | The full JSON the model must return (Step 3) |

- `Tier` and `Verdict` are `Literal[...]` types: only those exact strings are allowed. In Step 3
  this becomes an `enum` in the JSON schema sent to OpenAI, so the model can't invent a verdict like `"mostly_met"`.
- The `Field(description=...)` texts on the LLM models are **sent to the model** as part of the
  schema. They're instructions ("copy the exact sentence…"), which is why they read that way.
- No field in the LLM models has a default value. OpenAI's strict structured output requires every
  field to be required.
- `ScoredCriterion(Criterion)` **inherits** `id, tier, text` and adds the verdict fields.

### `backend/agents/scoring.py`: the maths (read top to bottom)

**The four constants** are the scoring policy. Changing them *is* changing the policy:
```python
TIER_WEIGHTS   = {"technical": 40, "required": 35, "preferred": 25}   # sums to 100
VERDICT_POINTS = {"met": 1.0, "partial": 0.5, "not_met": 0.0, "not_evidenced": 0.0}
GATE_CAP       = 30
NEEDS_EVIDENCE = {"met", "partial"}
```
- Mandatory isn't in `TIER_WEIGHTS` on purpose. It earns no points; it's only a pass/fail gate.
- `not_applicable` isn't in `VERDICT_POINTS` on purpose. Those lines are skipped, not scored as 0.

**`compute_score(criteria, verdicts, vendor_text)`**: the entry point, 4 lines of logic:
1. `apply_verdicts(...)` → clean list of `ScoredCriterion`
2. `score_tiers(...)` → points per tier
3. `raw_score = round(sum of tier points)`
4. `gate_passed = every mandatory line is "met"`; if not, `score = min(raw_score, GATE_CAP)`

**`apply_verdicts(...)`**: pairs each RFQ line with the model's verdict and fixes what we can't trust:
- `by_id = {v.criterion_id: v ...}`: a lookup table. We loop over **our** criteria and look each one
  up, so an id the model invented (e.g. `"X9"`) is simply never used.
- **Missing verdict** → `not_evidenced`, `downgraded=True`. Silence is never a pass.
- **Quote check:** if the verdict is `met`/`partial` and `quote_found(...)` is False →
  `not_evidenced`, `downgraded=True`.
- **Mandatory + not_applicable** → `not_met`. Otherwise the model could dodge the gate by calling
  AS9100D "not applicable".

**`score_tiers(scored)`**: for each tier:
1. Collect points of the lines that apply (skip `not_applicable`).
2. `average = sum / count`.
3. `active_weight` = sum of weights of tiers that still have lines. Normally 100; 75 if preferred dropped out.
4. `tier_max = 100 × weight / active_weight`. With all tiers present, that's just the weight (40/35/25).
   With preferred gone: technical 53.3, required 46.7. The total stays out of 100.
5. `points = tier_max × average`, rounded to 1 decimal.

**`quote_found(evidence, vendor_norm)`**: split the quote on `...` (models sometimes join fragments),
normalise each fragment, and require **every** fragment to be a substring of the normalised vendor text.
An empty quote → False.

**`normalise(text)`**: lowercase; `±` → `+/-`; en/em dash → `-`; remove quote marks (`" ' “ ” ‘ ’`);
collapse all whitespace (including line breaks) to single spaces; strip `. , ; :` from the ends.
This is why a quote spanning a line break in `vendor-a.txt` ("Routine\nworking tolerance…") still matches.

### `experiments/scoring_sanity.py`: proof it works

| # | Case | Expected | Why it matters |
|---|---|---|---|
| 1 | Everything met | 100 | Maths adds up to 100 |
| 2 | Mandatory not met, rest met | **30** (raw 100) | The gate caps |
| 3 | Invented quote on T1 | 60, T1 downgraded | Anti-hallucination works |
| 4 | Preferred all not_applicable | 53 (tech 53.3/53.3) | Weight redistribution |
| 5 | Model skipped R1, P1 | 40 | Silence ≠ pass |
| 6 | Mandatory marked not_applicable | 30, M1 → not_met | Gate can't be dodged |
| A | **Vendor A × RFQ-001** (real quotes) | raw **84** → **30** | Strong but uncertified |
| B | **Vendor B × RFQ-001** (real quotes) | **30**, gate passed | Certified but can't make the part |
| A′ | Vendor A with a paraphrased T2 quote | raw 76 → 30, T2 downgraded | The exact failure seen in the Step 0 smoke test |

All 9 pass.

**Worked example: vendor A × RFQ-001 by hand**
- Technical: T1 met 1, T2 met 1, T3 met 1, T4 met 1, T5 partial 0.5 (4–5 weeks *from receipt of
  material*, not *from PO*) → average 4.5/5 = 0.9 → 0.9 × 40 = **36.0**
- Required: R1 met, R2 met → 1.0 × 35 = **35.0**
- Preferred: P1 met 1, P2 not_evidenced 0, P3 not_applicable (skipped, nothing outsourced) → 1/2 = 0.5 × 25 = **12.5**
- Raw = 36 + 35 + 12.5 = 83.5 → `round` → **84**
- M1 (AS9100D) is not_met → gate fails → `min(84, 30)` = **30**

(`round(83.5)` gives 84 because Python rounds exact halves to the nearest *even* number, "banker's
rounding". `round(82.5)` would give 82. That's worth knowing if the interviewer asks.)

### A finding to discuss: A and B both score 30
Vendor B earns 30 legitimately (0 technical + 26.2 required + 4.2 preferred), and vendor A is
*capped* to 30. The number alone can't tell "excellent but uncertified" from "certified but can't
make the part"; only `gate_passed` and the breakdown can. Options if we want them apart:
lower `GATE_CAP` (e.g. 20 → A below B), or show `raw_score` next to the capped score in the UI.
**Nothing changed yet.** This is a policy decision for you. It's logged in BUILD_LOG as a weakest-part candidate.

---

## Hand-made verdicts (sanity script) vs LLM verdicts (Step 3)

`compute_score()` doesn't know or care where verdicts come from. It receives the same three
arguments either way. What changes is who produces two of them:

| Input | Sanity script (now) | Real app (Step 3) |
|---|---|---|
| `criteria` | Typed by hand (`RFQ_001 = [Criterion(...), ...]`) | `build_criteria(rfq)` from the RFQ JSON in SQLite |
| `verdicts` | Typed by hand (`v("T1", "met", "...")`) | `LLMEvaluation.criteria` from the one LLM call |
| `vendor_text` | Read from `samples/vendor-x.txt` | Whatever the user pasted or uploaded |

What the LLM brings that hand-made verdicts don't:

| LLM behaviour | What handles it |
|---|---|
| Paraphrases the evidence instead of copying it | `quote_found` → downgraded to `not_evidenced` (seen in the Step 0 smoke test) |
| Invents a quote | Same quote check |
| Skips a criterion id | `by_id.get()` → `None` → `not_evidenced` |
| Returns an id we never sent (`"X9"`) | Ignored: we loop over *our* criteria, not the model's list |
| Returns a verdict outside the 5 allowed | Impossible: `Literal` → JSON-schema `enum` → structured output rejects it |
| Marks a mandatory line `not_applicable` | Forced to `not_met` |
| Gives a **wrong verdict with a real quote** (e.g. "Ra 3.2" quoted, verdict `met`) | **Code can't catch this.** Only the prompt rubric and reading the 9-run table can |
| Calls a vague sentence `met` ("Space-grade heritage.") | **Code can't catch this either** (the quote is real). Prompt's specificity rule |
| Slightly different verdicts run to run (no temperature 0 on GPT-6) | Per-line judgements limit the swing: one line flipping `met` → `partial` moves the score by a few points, not 40 |
| Also writes 3 reasons + 2 gaps | Not scored. Displayed, trimmed/padded to exactly 3/2 in Step 3 |
| Costs money and time, can fail | ~$0.001 and a few seconds per call; failures → 502 with a clear message, no hidden retries |

The sanity script tests **the maths given verdicts**. Step 3's 9-run table tests **whether the LLM's
verdicts are right**. The two together justify the number.

---

## Drills (try one, then rerun `python experiments/scoring_sanity.py`)
- **A.** Change the gate from "cap at 30" to "score = 0". Which asserts break, and what would you update?
- **B.** Make `partial` worth 0.6. What does vendor A's raw score become? (Answer: T5 → 0.6 → technical 36.8 → raw 84.3 → 84.)
- **C.** Weights 50 / 30 / 20. Recompute vendor B by hand first, then check.

---

## Check questions

1. Vendor B passes the gate but has `not_met` on 5-axis, tolerance and finish. Walk through its score.
2. Why is `not_applicable` removed from the average instead of counting as 0?
3. What happens if the LLM forgets to return a verdict for `R2`?
4. The LLM says `T1 met` with evidence "tolerance of ±0.01mm". The profile says "+/-0.01 mm". Does it pass the quote check?
5. Why does scoring live in its own file with no database or LLM calls?
6. At boot, is `scoring.py` loaded? Why or why not?

### Answers

**1.** Technical: T1–T5 all `not_met` → average 0 → **0/40**. Required: R1 `partial` (0.5, CMM
outsourced but AS9102 reports done in-house), R2 `met` (1.0) → 0.75 × 35 = **26.25**. Preferred: P1
`not_met` 0, P2 `partial` 0.5 (ground support equipment, not flight structures), P3 `not_evidenced`
0 → 0.5/3 = 0.167 × 25 = **4.17**. Raw = 30.4 → **30**. M1 AS9100D is `met` (quote "AS9100D
certified (valid to August 2027)." is in the text) → gate passes → final **30**.

**2.** Because it would punish a vendor for something that doesn't apply to them. RFQ-001's P3 asks
for NADCAP-accredited subcontractors *for any outsourced process steps*. Vendor A outsources
nothing, so counting it as 0 would cost A points for being *more* self-sufficient. Skipping it
means A's preferred score is the average of the lines that actually apply.

**3.** `by_id.get("R2")` returns `None`, so `apply_verdicts` adds R2 as `not_evidenced` with
`downgraded=True` and rationale "No verdict returned by the model." It scores 0. Silence is never
a pass (sanity case 5).

**4.** Normalising gives `"tolerance of +/-0.01mm"` vs `"... tolerance +/-0.01 mm ..."`. `±` → `+/-`
matches, but **"of"** and the missing space in **"0.01mm"** mean it isn't a substring → **fails** →
downgraded to `not_evidenced`. That's the intended strictness: the model must copy, not rephrase.
The prompt in Step 3 will say so explicitly. (The cost: an honest model that rephrases slightly
loses the point. That's a trade-off we chose.)

**5.** Pure functions (same input → same output, no side effects) are easy to test with hand-made
data (we did, for free, before writing any LLM code), easy to explain, and easy to change live. The
interview's "change the weights" or "change the cap" is a one-line edit here with an instant check.
It also keeps the LLM's job narrow: it judges, and code decides the number.

**6.** No. Python runs a module only when something imports it. At boot `main.py` imports only `db`
(which imports `config`). `scoring.py` and `schemas.py` are loaded once Step 3's evaluator is
imported by `main.py`. Until then they're only used by `experiments/scoring_sanity.py`.
