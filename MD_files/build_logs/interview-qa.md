# AstroBase: interview questions and answers

Questions an interviewer is likely to ask about this project, with answers grounded in the actual code.
Companion to [`final-end-to-end-guide.md`](final-end-to-end-guide.md). Answer in your own words; these
are here so you know what a complete answer contains.

**Contents:** 1 Problem & approach · 2 Scoring · 3 LLM & prompts · 4 Data & database · 5 Backend & API ·
6 Frontend · 7 Docker & config · 8 Spec ambiguities · 9 Weaknesses & trade-offs · 10 Working with AI ·
11 Live-modification scenarios (step-by-step)

---

## 1. Problem & approach

**Q1. In two sentences, what does this app do?**
It scores a supplier's profile against a stored RFQ: pick an RFQ, paste or upload the profile, and get a
score out of 100 with three reasons and two gaps, plus a history of past evaluations. One LLM call judges
each RFQ requirement separately with quoted evidence, and code turns those judgements into the score.

**Q2. Why not just ask the LLM for a score out of 100?**
Because that number can't be checked, explained or reproduced, and it's easily fooled. A confident profile
without the mandatory certificate (vendor A) would get ~85. Per-requirement verdicts with quotes can be
verified, and a score computed from them traces back to every point. The LLM does what it's good at
(reading and matching text); code does what it's good at (consistent maths and hard rules).

**Q3. What did you do to make the number mean something?** *(the BUILD_LOG question)*
Five things: (1) the LLM gives verdicts per line, never a number; (2) every positive verdict must quote the
profile, and code downgrades any quote that isn't really there; (3) fixed tier weights (40/35/25); (4) a
mandatory gate that caps the score at 30; (5) a prompt rubric aimed at the three sample-vendor traps. Then I
proved it: hand-made verdicts through the scoring code, and all 9 vendor × RFQ runs through the real model,
with the verdicts read, not just the scores.

**Q4. What are the three sample vendors testing?**
A: excellent but missing AS9100D (does the mandatory requirement matter?). B: certified but can't make the part
(does the certificate outweigh capability?). C: marketing copy with no evidence (does the system reward
claims?). Results: A 30 (raw 77, capped), B 38, C 0 against RFQ-001; C scores 0 everywhere.

**Q5. Is this an "AI agent"?**
It's a single structured LLM call, not a loop with tools. The SPEC says "one LLM call per evaluation" and allows
"direct API calls with tool use", so I read "agent" as "the component that makes the AI judgement". A
multi-step agent would break the one-call rule and add cost and failure points for a task that is one judgement over one document.

---

## 2. Scoring

**Q6. Walk me through `compute_score`.**
`apply_verdicts` pairs each of our criteria with the model's verdict and corrects it: missing → `not_evidenced`,
`met`/`partial` with a quote not in the text → `not_evidenced`, mandatory `not_applicable` → `not_met`. Then
`score_tiers` does weight × average points per tier over applicable lines. The raw score is the rounded sum.
If any mandatory line isn't `met`, the score is `min(raw, 30)`.

**Q7. Why is mandatory a gate, not weighted points?**
Because in procurement a missing mandatory certificate disqualifies regardless of everything else. If it
were just points, vendor A's strengths would drown it out. So it carries no points; it only caps the score.

**Q8. Why cap at 30 and not zero?**
So "excellent but missing one certificate" (A) is still distinguishable from "nothing matches" (C = 0). The
UI also shows the uncapped raw score in the gate banner ("would have been 77"). It's a stated policy
choice; changing it is one constant.

**Q9. Why do `not_met` and `not_evidenced` both score 0? Why keep both?**
For the score they're equal: either way the buyer can't rely on it. But a buyer cares about the difference:
"they told us they can't" vs "they didn't say", which is a question to ask the vendor. So the verdict is kept and shown.

**Q10. Why is `not_applicable` excluded instead of scored 0?**
Some lines have a precondition, like "NADCAP subcontractors *for any outsourced steps*". A vendor who outsources
nothing shouldn't lose points for it. Excluding it averages over the lines that apply; if a whole tier drops
out, its weight is shared by the others so the total stays out of 100.

**Q11. What does the quote check catch, and what doesn't it catch?**
It catches invented or paraphrased quotes: the normalised quote must be a substring of the normalised
vendor text. It can't catch a *wrong judgement on a real quote* (e.g. "9 to 11 weeks" marked partial against
6 weeks), or a vague but real sentence ("Space-grade heritage."). Those are handled by the prompt rubric and
by reading the verdicts.

**Q12. What does `normalise` do and why?**
Lowercase, `±` → `+/-`, en/em dash → `-`, remove quote marks, collapse whitespace and line breaks, strip edge
punctuation. It's applied to both sides so formatting differences (a line break inside a sentence, `±` vs
`+/-`) don't fail an honest quote, while real rewording still does.

**Q13. Work out vendor B × RFQ-001 from the hand-made verdicts.**
Technical: all not_met → 0/40. Required: R1 partial 0.5 + R2 met 1 → 0.75 × 35 = 26.25. Preferred: 0 + 0.5 + 0
→ 0.167 × 25 = 4.17. Raw 30.4 → 30. M1 AS9100D met → gate passes → 30. (The live model gave 36–42 because it
judged a couple of lines more generously.)

**Q14. Why is `scoring.py` pure (no DB, no LLM)?**
So it can be tested with hand-made data for free, explained line by line, and changed live with an instant
check (`experiments/scoring_sanity.py`). It also keeps the LLM's job narrow.

**Q15. Why `round(83.5)` = 84 but `round(82.5)` = 82?**
Python rounds exact halves to the nearest even number (banker's rounding). A small detail, but it can move a score by 1.

---

## 3. LLM & prompts

**Q16. Where exactly is the LLM call, and how do you know there's only one?**
`chain.invoke(...)` in `backend/agents/evaluator.py`, inside `evaluate_vendor`. It's called once per request, there's no
loop, structured output is enforced inside that same request, and `model.py` sets `max_retries=0` so the SDK
can't silently retry (its default is 2).

**Q17. Which model and why?**
`gpt-6-luna`. I listed the models my key can access, checked the pricing page ($0.10 / $0.50 per 1M tokens vs
$2 / $10 for `gpt-6-sol`), and ran a trap question (Ra 3.2 vs Ra 1.6) on both; both got it right. At ~2.9k tokens
per evaluation it's about $0.001. Switching is an `.env` change.

**Q18. Why no temperature? Isn't it less deterministic?**
GPT-6 models are reasoning models; `temperature=0` returns a 400 ("only the default (1) is supported"). Instead
they have `reasoning_effort`. Stability comes from the design: small per-line judgements and a score computed in
code, so one line flipping moves the score a few points, not 40. Observed: B × RFQ-001 was 36, 42 and 38 across runs.

**Q19. What is reasoning effort and why `low`?**
How much the model thinks before answering (`none | low | medium | high | xhigh` for Luna). I ran all 9
combinations at medium and at low. Low gave the same pattern in 10–14 s instead of 14–30 s, and it even fixed one
lenient verdict (B's 9–11 weeks → not_met).

**Q20. Where are the prompts and what's in them?**
`backend/prompts/`. `evaluator_system.md` is the rubric: verdict definitions, "copy evidence character for
character", judgement rules (specific beats general; partial needs specific evidence; exact certificate match;
lower Ra is finer; lead-time basis; different line of business), and the rules for 3 reasons / 2 gaps.
`evaluator_user.md` is the template with the RFQ, the criteria list and the delimited vendor text.
`__init__.py` loads them and holds `PROMPT_VERSION`.

**Q21. Why keep prompts in `.md` files instead of Python strings?**
They're readable and editable as text, their diffs are clean, and they're separate from code. Versioning is
explicit (`PROMPT_VERSION`), and every stored evaluation records which version produced it.

**Q22. Tell me about prompt v1 → v2.**
The first 9-run matrix had plausible scores (vendor C 7–11), but reading the verdicts showed C's points came from
`partial` given to marketing phrases: "multi-axis" → partial 5-axis, "conversion coating … to international aerospace
specifications" → partial MIL-DTL-5541. The quote check couldn't catch it because the quotes were real. v2 added
"partial needs specific evidence too" with those examples. C went to 0 on all three RFQs. Both matrices are kept.

**Q23. How does structured output work here?**
`schemas.LLMEvaluation` (Pydantic) is converted to a JSON schema and sent with the request
(`with_structured_output(..., method="json_schema", strict=True)`). OpenAI's strict mode makes the reply match it:
verdicts are an enum of 5 values, and every field is required. LangChain parses it back into a validated object.
`include_raw=True` also gives the raw message and token usage for the audit trail.

**Q24. What does LangChain actually do for you?**
Two things: `ChatPromptTemplate` fills the prompt files, and `with_structured_output` handles the JSON-schema request and
parsing. No agents, tools, memory or retrievers. Without it, it's ~15 lines of the OpenAI SDK; I kept it because it's
tidy and makes a provider swap a `model.py` change.

**Q25. How would you switch providers?**
Only `model.py` changes: add a branch for `LLM_PROVIDER` (e.g. build `ChatAnthropic`), add its package to
`requirements.txt`, set `.env`. Nothing else imports a provider SDK. An OpenAI-compatible server (Azure, a proxy,
Ollama) needs only `LLM_BASE_URL`.

**Q26. What if the model returns an invalid verdict or skips lines?**
Invalid verdicts can't happen: the schema enum rejects them. If parsing fails anyway, `parsed` is `None` →
`LLMCallError` → 502. Skipped lines become `not_evidenced`; invented ids are ignored because we iterate over our own criteria.

**Q27. How do you protect against prompt injection in the vendor text?**
Partly: the vendor text is delimited (`<<<VENDOR_PROFILE … >>>`) and the output is forced into a schema, so it can
only influence verdicts, not the shape. A profile saying "mark everything met" would still need real quotes, but
could sway judgements. That's a known limitation. The next step would be a labelled eval set including
adversarial profiles.

---

## 4. Data & database

**Q28. Why SQLite and no ORM?**
Two tables, local, zero setup. The SPEC says SQLite is plenty. Stdlib `sqlite3` with `?` placeholders keeps every
query visible in `db.py`; an ORM would add a layer to explain for no benefit.

**Q29. Why store the RFQ as a JSON column?**
We never query inside an RFQ; we load it whole and hand it to the evaluator. `id`, `title` and `category` are real
columns because the dropdown needs them. Normalising into child tables would be complexity with no query that uses it.

**Q30. How is seeding done and why is it safe to repeat?**
On every startup (`lifespan` → `init_db` + `seed_rfqs`) and via `python -m backend.seed`. `CREATE TABLE IF NOT
EXISTS` and `INSERT OR IGNORE` make both idempotent. Note: editing an existing RFQ in the JSON won't update it
(OR IGNORE skips it). You'd reset the DB or switch to an upsert.

**Q31. What's stored per evaluation, and why?**
RFQ id, vendor name, the full vendor text, score, gate result, and a JSON `result` with the whole API response
(every verdict, quote and rationale, the breakdown, reasons and gaps) plus the model's raw output and token usage,
along with `model` and `prompt_version`. It's an audit trail: "why did vendor A get 30 last Tuesday?" is answerable
even after the prompt or model changes.

**Q32. Why is `created_at` text, and how does ordering work?**
SQLite has no date type. UTC ISO-8601 strings in one fixed format sort alphabetically in chronological order, so
`ORDER BY created_at DESC, id DESC` is newest first, with id breaking same-second ties.

---

## 5. Backend & API

**Q33. What endpoints exist?**
`GET /api/health`, `GET /api/rfqs`, `GET /api/rfqs/{id}`, `POST /api/evaluations`, `GET /api/evaluations?limit=20`.

**Q34. How are errors handled?**
422 from FastAPI validation (blank text after stripping, over 20 000 chars, bad `limit`); 404 for an unknown RFQ;
503 `LLMConfigError` (e.g. "LLM_API_KEY is empty; set it in .env"); 502 `LLMCallError` (network, auth, timeout, schema
mismatch). Always `{"detail": "..."}`, never a bare 500. Failed evaluations aren't saved.

**Q35. Why are the routes `def` and not `async def`?**
`sqlite3` and the LangChain `invoke` call block. FastAPI runs plain `def` routes in a worker thread, so a slow LLM call
doesn't block the event loop, and each request opens its own SQLite connection in its own thread.

**Q36. What does `lifespan` do?**
Code before `yield` runs once at startup (create tables, seed RFQs); code after it would run at shutdown (nothing
needed). It means a clean clone works with no manual setup step.

**Q37. Why does `main.py` contain no logic?**
Convention from the scaffold: `main.py` is wiring (routes, startup, error translation). Logic lives in `db.py`,
`evaluator.py` and `scoring.py`, which keeps each file small and each concern testable on its own.

---

## 6. Frontend

**Q38. Why vanilla TypeScript and not React?**
One form, one result card and one list. A framework would add build complexity and code to explain. `main.ts` is
readable top to bottom.

**Q39. How does the frontend reach the backend without CORS?**
The browser only calls its own origin (`localhost:5173/api/...`). Vite's dev-server proxy forwards `/api` to the
backend (in Docker `http://backend:8000`, via the Compose service name). CORS only applies to browsers calling a different origin.

**Q40. How is upload handled?**
In the browser: `file.text()` fills the same textarea used for pasting, so there's one backend input path and no multipart endpoint.

**Q41. Any security considerations in the UI?**
All vendor and model text is HTML-escaped (`esc()`) before going into `innerHTML`, preventing XSS from a malicious
profile. The API key never reaches the browser. Evaluate is disabled while a request runs, so double-clicks can't fire two LLM calls.

---

## 7. Docker & configuration

**Q42. What happens on `docker compose up --build`?**
Build both images → start the backend with `.env` injected and `./data_warehouse` mounted → uvicorn boots, `lifespan`
creates tables and seeds → the healthcheck (`/api/health` every 5 s) turns it `healthy` → only then does the frontend
start (`depends_on: service_healthy`), with `VITE_PROXY_TARGET=http://backend:8000`.

**Q43. How do secrets stay safe?**
The key lives only in the root `.env`: gitignored, excluded from images by `.dockerignore`, injected at runtime by
`env_file`, read only by `config.py`, used only in `model.py`. The frontend container never receives it.

**Q44. Why `--host 0.0.0.0` in the containers?**
Inside a container `127.0.0.1` is the container itself; Docker's port mapping delivers outside traffic to the
container's network interface, which uvicorn/Vite only see if they listen on all interfaces.

**Q45. Why is the backend host port configurable?**
Port 8000 was taken by another local project (`docker compose up` failed with "port is already allocated", and a
request got a 404 from the other app). The compose file uses `${BACKEND_PORT:-8000}`, and the container still listens on 8000 internally.

**Q46. I changed `LLM_MODEL` in `.env` but nothing changed. Why?**
Environment variables are read when the container starts. `docker compose restart` reuses the old container config;
use `docker compose up -d --force-recreate`. For code changes, `docker compose up --build`, because the code is baked
into the image (no bind mount, no reload).

---

## 8. Spec ambiguities (and what I assumed)

**Q47. What was unclear in the spec?**
- `rfqs.json` vs the `.md` files disagree → JSON is the source of truth.
- "AI agent" + "one LLM call" → one structured call, no loop, no retries.
- Always exactly 3 reasons / 2 gaps, even for vendor C → yes; honest wording, code pads if short.
- Duplicate requirements (600 mm in RFQ-002; cut-to-size in RFQ-003) → textual dedupe (catches the first, not the second).
- Quantity, material and delivery sit outside the tiers → judged as technical lines.
- Lines with preconditions → a `not_applicable` verdict.
- Lead time "from receipt of material" vs "from PO" → at best partial.
- History: all RFQs or only the selected one → all, newest first.
- Seed "via a command or on first run" → both.

---

## 9. Weaknesses & trade-offs

**Q48. What's the weakest part of this code?**
Verdict quality rests on the prompt (`evaluator_system.md`). Code can prove a quote exists but not that the judgement
on it is right, and there's no automated check for a regression like v1's "marketing earns partial"; I caught it by
reading verdicts. Related: run-to-run variation (no temperature 0), judgement-call weights and cap, textual dedupe.

**Q49. What would you do with two more days?**
Turn the 9-run matrix into a labelled evaluation set: hand-label the expected verdict per line, run each combination
several times, and report agreement and score spread. Then every prompt, model or effort change is measured, not
eyeballed. After that: harder profiles (near-miss certificates, injection attempts), semantic dedupe, and the raw score in the history list.

**Q50. B (can't make the part) scores higher than A (can). Is that right?**
It's the policy: a missing mandatory certificate disqualifies, so A is capped at 30, while B, certified, earns what it
evidences (~38). Neither is a good choice for RFQ-001; the UI shows why (A's banner with raw 77, B's empty technical
bar). If the business disagreed, lower `GATE_CAP` or change the gate to zero.

**Q51. Latency is 10–15 s. How would you improve it?**
Options: `reasoning_effort=none` (test the verdict quality first), a shorter rubric, streaming the reasoning to the UI, or
a background job with polling. For a buyer evaluating one vendor, 10–15 s with a clear "Evaluating…" status is acceptable.

**Q52. Why no tests?**
The SPEC puts test suites out of scope. The equivalent checks exist as scripts: `scoring_sanity.py` (rules, with
asserts) and `run_matrix.py` (model behaviour across all 9 combinations).

---

## 10. Working with AI

**Q53. How did you use AI tools?**
Claude Code built it step by step from a plan it wrote and I approved. I made the decisions (stack, gate policy, model
after verification, working rhythm), and after each backend step I got a walkthrough and answered check questions
before committing. I read the model's verdicts, not just scores.

**Q54. What did the AI get wrong that you caught?**
It planned `temperature=0`; I questioned it because reasoning models use effort instead, and testing confirmed a 400.
Also: hidden SDK retries (fixed with `max_retries=0`), the effort values in docs vs what the model accepts
(`minimal` rejected), and prompt v1's `partial` loophole, found by reading verdicts.

**Q55. What did you write yourself?**
*(Your own answer: the BUILD_LOG TODO. Have a concrete example ready, e.g. a scoring drill you did by hand.)*

---

## 11. Live-modification scenarios (step by step)

Each: what to change, where, and how to check. After any code change: `docker compose up --build`.

**L1. "Make a failed mandatory requirement give 0 instead of capping at 30."**
`backend/agents/scoring.py`: set `GATE_CAP = 0` (then `min(raw, 0)` = 0). Update the gate text in `frontend/src/main.ts`
("Score capped at 30"). Check: `python experiments/scoring_sanity.py`; the gate cases now expect 0, so update their
expected values. Mention: A and C would both show 0, losing the distinction.

**L2. "Change the weights to 50/30/20."**
`TIER_WEIGHTS = {"technical": 50, "required": 30, "preferred": 20}`. Predict vendor A by hand first: 0.9×50 + 1.0×30 +
0.5×20 = 85 → still capped at 30. Run the sanity script and update the numbers that change.

**L3. "Make partial worth 0.6."**
`VERDICT_POINTS["partial"] = 0.6`. Vendor A (hand verdicts): T5 → 0.6 → technical 4.6/5 × 40 = 36.8 → raw 84.3 → 84.

**L4. "Add a confidence level to each verdict."**
1. `schemas.py`: `confidence: Literal["low", "medium", "high"]` on `CriterionVerdict` (with a description), and on
   `ScoredCriterion` (default `"medium"` so the missing-verdict path still works).
2. `scoring.apply_verdicts`: pass `confidence=v.confidence` when building `ScoredCriterion`.
3. `prompts/evaluator_system.md`: one line on what confidence means; bump `PROMPT_VERSION`.
4. `frontend/src/api.ts` + `main.ts`: add the field and a column in the breakdown table.
Structured output picks up the new schema automatically.

**L5. "Filter history by RFQ."**
`db.list_evaluations(limit, rfq_id=None)` → add `WHERE rfq_id = ?` when given. `main.list_evaluations(limit, rfq_id: str | None = None)`.
Frontend: `getEvaluations(rfqId)` → `?rfq_id=...`, called on dropdown change. Check: `curl ':8001/api/evaluations?rfq_id=RFQ-001'`.

**L6. "Return 4 reasons."**
`evaluator.N_REASONS = 4`, update the prompt ("exactly 4") and the `LLMEvaluation.reasons` description. The frontend
renders whatever list it gets. `pick_reasons` pads to 4 if the model returns fewer.

**L7. "Switch to a stronger model."**
`.env`: `LLM_MODEL=gpt-6-sol` → `docker compose up -d --force-recreate` → run one evaluation. The stored rows now show
`model=gpt-6-sol`. No code change.

**L8. "Add a new RFQ."**
Append an object to `data_warehouse/seed/rfqs.json` with the same fields → restart the backend (or
`docker compose exec backend python -m backend.seed`). It appears in the dropdown; `build_criteria` handles it with no code change.

**L9. "Show the raw score in the history list."**
`frontend/src/main.ts` → `loadHistory()`: add a column `${e.gate_passed ? "" : `(raw ${e.raw_score})`}`. The data is already in each history item.

**L10. "Add an endpoint to delete an evaluation."**
`db.delete_evaluation(eval_id) -> bool` (`DELETE FROM evaluations WHERE id = ?`, return `rowcount == 1`);
`@app.delete("/api/evaluations/{eval_id}")` → 404 if False, else `{"deleted": eval_id}`.

**L11. "Make mandatory worth points instead of a gate."**
Add `"mandatory": 20` to `TIER_WEIGHTS` (and rebalance the others to sum to 100), then remove or keep the cap. Discuss
the trade-off: A's strengths could now outweigh a missing certificate.

**L12. "Fix RFQ-003's cut-to-size double count."**
Simplest honest fix: in `build_criteria`, a small alias map of known overlaps, or treat lines sharing a key phrase
("cut-to-size") as duplicates. Better long term: flag overlapping lines once per RFQ at seed time. Check by printing
`build_criteria` for RFQ-003 (R2 should disappear).
