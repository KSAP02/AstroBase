# Step 3: LLM evaluation endpoint

**Commit:** `Evaluate a vendor against an RFQ with one structured LLM call`
**Goal:** `POST /api/evaluations` takes an RFQ id and vendor text, makes **one** LLM call to get
per-requirement verdicts, scores them with Step 2's code, and returns score, 3 reasons and 2 gaps.
(Saving to the DB comes in Step 4.)

---

## The full request path

```
POST /api/evaluations  {"rfq_id": "RFQ-001", "vendor_text": "..."}
 │
 ├─ main.create_evaluation(req: EvaluationRequest)
 │     FastAPI already validated the body: rfq_id is a string, vendor_text stripped, 1..20 000 chars → else 422
 ├─ db.get_rfq("RFQ-001")                                   → None? 404
 │
 ├─ evaluator.evaluate_vendor(rfq, vendor_text)
 │     ├─ build_criteria(rfq)            → [M1, T1..T6, R1, R2, P1..P3]   (dedupe, ids)
 │     ├─ load_prompt("evaluator_system") + load_prompt("evaluator_user")
 │     ├─ ChatPromptTemplate.from_messages([("system", ...), ("human", ...)])
 │     ├─ get_chat_model()               → ChatOpenAI(gpt-6-luna, reasoning_effort=low, max_retries=0)
 │     │                                   → LLMConfigError if key/model missing → main turns it into 503
 │     ├─ .with_structured_output(LLMEvaluation, method="json_schema", strict=True, include_raw=True)
 │     ├─ chain = prompt | llm
 │     ├─ chain.invoke({rfq_id, rfq_title, criteria_block, vendor_text})   ★ THE ONE LLM CALL ★
 │     │                                   → any exception → LLMCallError → main turns it into 502
 │     ├─ out["parsed"] is an LLMEvaluation (validated) — or None → LLMCallError
 │     ├─ compute_score(criteria, parsed.criteria, vendor_text)       ← Step 2, unchanged
 │     ├─ pick_reasons(...) → exactly 3     pick_gaps(...) → exactly 2
 │     └─ return EvaluationOut, raw        (raw = the model's JSON text + token usage, kept for Step 4)
 │
 └─ FastAPI serialises EvaluationOut → JSON 200
```

Import graph (no cycles):
`config ← model ← evaluator`, `prompts ← evaluator`, `schemas ← scoring ← evaluator`, `evaluator + model + schemas + db ← main`.

---

## File by file

### `backend/model.py`: the only place the LLM client is built
- Checks config and raises `LLMConfigError` with a message that says exactly what to fix
  ("LLM_API_KEY is empty; set it in .env").
- Imports `langchain_openai` **inside** the function, so a missing package becomes a clear message instead of a crash at startup.
- `ChatOpenAI(model, api_key, base_url or None, reasoning_effort or None, max_retries=0, timeout=120)`.
  No temperature, since GPT-6 rejects it. `max_retries=0` keeps it to exactly one call (the SDK
  default is 2 silent retries). Changing model or effort means editing `.env`.

### `backend/prompts/`: the instructions, as editable text
- `__init__.py`: `load_prompt(name)` reads `<name>.md`; `PROMPT_VERSION = "v2"` is recorded in every response.
- `evaluator_system.md` is the **rubric**: what each verdict means, evidence rules (copy character
  for character), and judgement rules that each target a known trap:

  | Rule | Trap it targets |
  |---|---|
  | Specific beats general; vague claims → `not_evidenced` | Vendor C's marketing copy |
  | `partial` needs specific evidence too (**added in v2**) | Vendor C earning `partial` from "multi-axis" etc. |
  | Certificates must match exactly (IATF 16949 ≠ AS9100D) | Vendor A |
  | Lower Ra is finer; tighter tolerance meets looser | Vendor A (beats spec), vendor B (fails spec) |
  | Lead time "from receipt of material" ≠ "from PO" | Vendor A |
  | Different line of business → mostly not_met / not_evidenced | A and B on RFQ-002 and RFQ-003 |
  | Exactly 3 reasons / 2 gaps; failed mandatory is gap #1 | SPEC output format |
- `evaluator_user.md` is a template with `{rfq_id}`, `{rfq_title}`, `{criteria_block}` and
  `{vendor_text}`. The vendor text sits between `<<<VENDOR_PROFILE` / `VENDOR_PROFILE>>>` markers so
  the model can tell our instructions from the vendor's text.
  - `{...}` are LangChain template variables, which is why the system prompt contains no curly braces.

### `backend/agents/evaluator.py`
- **`build_criteria(rfq)`**: turns the RFQ JSON into labelled lines. It walks tiers in priority
  order (mandatory → technical → required → preferred), adds `Material:`, `Quantity:` and `Delivery:` as
  technical lines, and **skips a line if its normalised text contains, or is contained in, a line
  already kept**. Results:
  - RFQ-001: 12 lines (M1, T1–T6, R1–R2, P1–P3).
  - RFQ-002: "Ability to handle parts up to 600 mm" (preferred) dropped, since it duplicates T2
    "Parts up to 600 mm". The material line is dropped because it contains T1's coating spec.
  - RFQ-003: "Cut-to-size capability" (T3) and "Ability to supply cut-to-size" (R2) **both kept**,
    because the wording differs. Known, documented.
- **`evaluate_vendor(rfq, vendor_text)`**: builds the prompt, makes the call, validates, scores, and
  assembles `EvaluationOut`. `include_raw=True` returns `{"raw": AIMessage, "parsed": LLMEvaluation | None,
  "parsing_error": ...}`, so we get the validated object **and** the raw text and token usage for auditing.
- **`pick_reasons`**: keeps the model's reasons unless they point at an unknown id or a line whose
  verdict **our code downgraded**, since a "strength" the evidence check rejected shouldn't be shown.
  Then it trims to 3, and pads from met/partial lines (or an honest "No further strengths…") if short.
- **`pick_gaps`**: puts any failed mandatory line first (inserted if the model didn't mention it),
  trims to 2, and pads from not_met / not_evidenced lines if short.

### `backend/schemas.py` (additions)
- `EvaluationRequest`: `vendor_text` uses `StringConstraints(strip_whitespace=True, min_length=1,
  max_length=20_000)`, so blank or huge input → 422 before any LLM cost.
- `EvaluationOut`: what the API returns: score, raw score, gate, breakdown, per-line verdicts, 3 reasons,
  2 gaps, model, prompt version.

### `backend/main.py` (addition)
`POST /api/evaluations`: `get_rfq` → 404, `evaluate_vendor`, `LLMConfigError` → **503**, `LLMCallError` → **502**.
A client always gets a clear `detail` message, never a bare 500.

### `docker-compose.yml` (change)
Host port is now `${BACKEND_PORT:-8000}`, because port 8000 was taken by another project on this
machine. `.env` has `BACKEND_PORT=8001`; Compose reads `.env` for `${...}` substitution.

### `experiments/run_matrix.py`
Sends all 9 vendor × RFQ pairs to the running API **in parallel** and writes a Markdown report
(summary grid + every verdict and quote). Usage: `python experiments/run_matrix.py http://localhost:8001 <name>`.

---

## What happened when we ran it (the evidence)

**First single call** (A × RFQ-001, v1, medium): score 30, raw 77, gate failed; the model itself wrote
"the profile instead lists ISO 9001:2015 and IATF 16949:2016"; 0 downgrades; **29 s**.

**Matrix, three runs:**

| Run | A×001 | A×002 | A×003 | B×001 | B×002 | B×003 | C×001 | C×002 | C×003 |
|---|---|---|---|---|---|---|---|---|---|
| v1, medium | 30 (raw 81) | 11 | 12 | 36 | 5 | 16 | **7** | **11** | **11** |
| v2, medium | 30 (raw 80) | 0 | 12 | 42 | 5 | 12 | **0** | **0** | **0** |
| **v2, low** (final) | 30 (raw 77) | 0 | 12 | 38 | 0 | 12 | 0 | 0 | 0 |

- **v1 → v2:** vendor C's 7–11 points were all `partial` verdicts on marketing phrases ("multi-axis",
  "conversion coating … to international aerospace specifications", "a wide range of forms and
  specifications"). The quote check can't catch this, because those quotes are real. Adding "partial
  needs specific evidence too" to the rubric → C = 0 everywhere.
- **medium → low:** same pattern, **10–14 s instead of 14–30 s**, and low correctly marked B's
  "9 to 11 weeks" as `not_met` where medium had said `partial`. Chose **low**.
- **A × RFQ-003 gate ✓:** vendor A really does track stock "by heat lot" against mill test
  certificates, a literal match for RFQ-003's mandatory line. It still scores 12 because it isn't a
  titanium supplier. Acceptable.
- Reports: `experiments/matrix_v1_medium.md`, `matrix_v2_medium.md`, `matrix_v2_low.md`.

---

## Drills
- **A.** Add a `confidence: low | medium | high` field to each verdict: `CriterionVerdict` in
  `schemas.py` + one line in the prompt. Nothing else changes, because structured output picks up the new field.
- **B.** Switch to `gpt-6-sol` and rerun one combination. (Edit `.env`, then `docker compose up -d --force-recreate`.)
- **C.** Make vendor B's "CMM outsourced" count as `partial` instead of `met` by adding a rule to the rubric; bump `PROMPT_VERSION` to `v3`.

---

## Check questions

1. Where exactly is the single LLM call, and how do you know there's only one?
2. Vendor C quotes "Space-grade heritage." Why doesn't the quote check catch it, and what does?
3. How would you switch to a different OpenAI model? To a different provider?
4. What happens if `LLM_API_KEY` is empty, or OpenAI is down?
5. Why does `pick_reasons` drop a reason whose criterion was downgraded?
6. Why did we bump `PROMPT_VERSION`, and why does it matter?

### Answers

**1.** `chain.invoke(...)` in `evaluator.evaluate_vendor()`, marked ★. It's called once per request,
there's no loop around it, and `model.py` sets `max_retries=0`, so the OpenAI SDK can't silently
repeat it. LangChain's structured output uses the model's native JSON-schema mode inside that same
request; it doesn't make a second "fix the JSON" call.

**2.** The quote check only asks "is this text really in the profile?". "Space-grade heritage." is,
so it passes. What stops it is the **prompt**: the rules "specific beats general" and (since v2)
"partial needs specific evidence too" make the model return `not_evidenced`, which needs no quote and
scores 0. Evidence: vendor C went from 7–11 (v1) to 0 (v2).

**3.** Another OpenAI model: change `LLM_MODEL` in `.env` and recreate the container. No code
changes. Another provider: add a branch in `model.py` only (e.g. `if s.llm_provider == "anthropic":`
build `ChatAnthropic(...)`), add its package to `requirements.txt`, and set `LLM_PROVIDER`. Nothing else
calls a provider SDK, so nothing else changes. An OpenAI-compatible server (Azure, a proxy, Ollama)
needs only `LLM_BASE_URL`.

**4.** Empty key: `get_chat_model()` raises `LLMConfigError("LLM_API_KEY is empty; set it in .env")`
before any network call, and `main.py` returns **503** with that message. OpenAI down, bad key or
timeout: `chain.invoke` raises, `evaluate_vendor` wraps it in `LLMCallError`, and `main.py` returns
**502** with the error text. No retry happens. The user can click again.

**5.** A downgrade means our code decided the model's claimed strength isn't backed by the profile
(the quote wasn't found). Showing "Strength: 5-axis capability" next to a verdict of
`not_evidenced` would contradict itself. Reasons must agree with the final verdicts, and the
verdicts are what the score is built on.

**6.** Because the prompt wording changed (v1 → v2), and the same vendor can get different verdicts
under different prompts. Every response records `prompt_version` (and Step 4 stores it with each
evaluation), so when someone asks "why did this vendor get 11 last week and 0 today?", the stored
version answers it. Same idea as recording `model`.
