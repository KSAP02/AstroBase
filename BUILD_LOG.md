# Build Log

Fill this in as you go, or at the end. Keep it short — bullet points are fine.
This is read as carefully as the code.

---

## Stack

What you used and why. One line each.

- Frontend: Vite + vanilla TypeScript, no UI framework — one page with a form and two lists doesn't need React.
- Backend: Python + FastAPI — fastest for me; Pydantic models double as request validation and the LLM output schema.
- Database: SQLite via stdlib `sqlite3` (no ORM) — two tables, local file in `data_warehouse/`, zero setup.
- LLM / agent: OpenAI through LangChain (`langchain-core` + `langchain-openai`) — used only for the prompt template and structured output; one call per evaluation, no agent loop.
- Local run: Docker Compose (backend + frontend containers) so a clean clone starts with `docker compose up --build`.

---

## Scoring approach

How does your agent arrive at a number? What did you do to make that number
mean something?

**The LLM judges each RFQ line; code computes the number** (`backend/agents/scoring.py`, pure functions, no I/O).

- The LLM returns one verdict per RFQ line (`met / partial / not_met / not_evidenced / not_applicable`), each with a verbatim quote from the vendor profile. It never outputs a score.
- **Quote check (code):** a `met`/`partial` verdict whose quote isn't actually in the vendor text (after normalising case, whitespace, `±`, quote marks) is downgraded to `not_evidenced`. Lines the model skipped count as `not_evidenced`, not as passes.
- **Weights:** technical (incl. quantity and delivery) 40, required 35, preferred 25. `met` = 1, `partial` = 0.5, otherwise 0. Each tier scores weight × average over its applicable lines; `not_applicable` lines are excluded, and a tier with none left hands its weight to the others.
- **Mandatory gate:** mandatory lines carry no points; they're pass/fail. If any isn't `met`, the score is capped at **30** (`GATE_CAP`). A cap rather than zero keeps "strong but missing one certificate" distinguishable from "nothing matches".
- Every score is explainable: the response carries each line's verdict, quote and a per-tier breakdown (`technical 36/40, required 35/35, preferred 12.5/25`).
- Checked with hand-made verdicts before any LLM was involved (`experiments/scoring_sanity.py`, 9 cases, all pass). Using real quotes from the sample files: vendor A × RFQ-001 → raw 84, capped to **30**; vendor B × RFQ-001 → **30** with the gate passed.
- **Evidence, all 9 combinations with the real model** (`gpt-6-luna`, prompt v2, reasoning effort `low`; `experiments/matrix_v2_low.md`):

  | Vendor | RFQ-001 machining | RFQ-002 coating | RFQ-003 titanium |
  |---|---|---|---|
  | A: strong machinist, no AS9100D | **30** (raw 77, gate ✗) | **0** | **12** (gate ✓) |
  | B: AS9100D, can't make the part | **38** (gate ✓) | **0** | **12** (gate ✗) |
  | C: marketing copy only | **0** | **0** | **0** |

  A is capped by the missing certificate but its raw 77 shows the strength; B passes the gate and earns only what it evidences; C's unsupported claims earn nothing; machine shops score near zero on the coating and raw-material RFQs. Zero quotes were downgraded in the final run.

---

## What you built

What works. Be specific.

**Backend (FastAPI + SQLite)**
- `GET /api/rfqs`, `GET /api/rfqs/{id}`: RFQs from SQLite, seeded from `rfqs.json` on startup (or `python -m backend.seed`), idempotent.
- `POST /api/evaluations`: one structured LLM call → per-requirement verdicts with verbatim quotes → score computed in code (quote check, 40/35/25 weights, mandatory gate capped at 30) → exactly 3 reasons and 2 gaps. Blank/oversized input → 422, unknown RFQ → 404, LLM not configured → 503, LLM call failed → 502.
- Every evaluation is saved with the vendor text, all verdicts, the raw model output and token usage, the model id and the prompt version (audit trail); `GET /api/evaluations` lists them newest first. History survives restarts (DB on a host volume).
- `docker compose up --build` runs it; host port configurable via `BACKEND_PORT`.

---

## What you skipped

What you consciously left out, and why.

- MCP server (was in my starter scaffold) — removed; nothing in the spec needs agents calling into this app, and it would be surface area with no purpose.

---

## Where the spec was unclear

Anything ambiguous, contradictory, or underspecified. What did you assume,
and what did you do about it?

- **`rfqs.json` and the `RFQ-00x.md` files disagree.** RFQ-002's `.md` has no Technical section, while the JSON lists "Coating per MIL-DTL-5541…" and "Parts up to 600 mm" as technical. The `.md` also uses `±` where the JSON uses `+/-`. Assumed the JSON is the source of truth (the spec calls it "ready to load"); the DB stores each RFQ's JSON unchanged and the `.md` files are only for humans.
- **"Backend invokes an AI agent" + "one LLM call per evaluation".** Read as: one structured LLM call (LangChain prompt template → `ChatOpenAI.with_structured_output`), no agent loop, no tools, no retries. `max_retries=0` so the SDK can't silently make extra calls.
- **"Three supporting reasons and two gaps"**: what if a vendor has no genuine strengths (vendor C)? Always return exactly 3 and 2. The prompt asks for honesty over invention; code drops reasons tied to lines it downgraded, puts a failed mandatory first among the gaps, and pads from the verdicts if the model returned too few.
- **Duplicate requirements in `rfqs.json`.** RFQ-002 lists "Parts up to 600 mm" as technical *and* "Ability to handle parts up to 600 mm" as preferred. `build_criteria()` drops a line whose text contains (or is contained in) a higher-priority line, so it's counted once, as technical. RFQ-003's "Cut-to-size capability" / "Ability to supply cut-to-size" use different words and are **not** caught, so it counts twice (documented, not fixed).
- **Quantity, material and delivery** aren't in any tier in the JSON. Treated as technical lines, since "can they make enough, fast enough, in this material" is core capability.
- **`not_applicable`**: some preferred lines have a precondition ("NADCAP subcontractors *for any outsourced steps*"). Added a verdict that removes the line from the average instead of scoring it 0. The model mostly returns `not_evidenced` there instead, which is the conservative choice.
- **Lead-time basis**: vendor A quotes "from receipt of material" and RFQ-001 says "from PO" (material is free-issue). The prompt makes this at best `partial` unless reconciled.
- **"Past evaluations are listed below, most recent first"**: all RFQs or only the selected one? Assumed all, newest first (`ORDER BY created_at DESC, id DESC`, limit 20), each row showing RFQ id, vendor and score. The spec says "past evaluations", not "past evaluations for this RFQ".
- **"Seed data loads via a documented command or on first run"**: did both. The API seeds on startup, and `python -m backend.seed` does the same by hand. Both use `INSERT OR IGNORE`, so re-running never duplicates rows.

---

## What broke

Something that did not work first time. What was it, how did you diagnose it,
how did you fix it?

- **`temperature=0` rejected by the model.** The plan assumed temperature 0 for repeatable verdicts. A smoke test against `gpt-6-luna` and `gpt-6-sol` returned `400 — 'temperature' does not support 0.0 with this model. Only the default (1) value is supported.` These are reasoning models. Fix: don't pass `temperature`; repeatability comes from the design instead (small per-line judgements, score computed in code).
- **Prompt v1 let marketing copy earn `partial`.** The first 9-run matrix looked right on scores (vendor C 7–11), but reading the verdicts showed where C's points came from: "multi-axis" → partial 5-axis, "conversion coating to international aerospace specifications" → partial MIL-DTL-5541, "aerospace-grade alloys in a wide range of forms and specifications" → partial AMS 4911. The rubric said vague claims are `not_evidenced`, and the model used `partial` as a loophole. The quote check couldn't catch it (the quotes are real). Fix: prompt **v2** adds "partial needs specific evidence too" with those exact examples. Vendor C went to **0 / 0 / 0**. Both matrices are kept in `experiments/` (`matrix_v1_medium.md`, `matrix_v2_medium.md`).
- **Port 8000 already taken.** `docker compose up` failed with "Bind for 0.0.0.0:8000 failed: port is already allocated", and a request to `:8000/api/evaluations` returned a 404 from a *different* app. `docker ps` + `/openapi.json` showed another local project's backend on 8000. Fix: the compose host port is now `${BACKEND_PORT:-8000}` (8000 by default; I run with `BACKEND_PORT=8001` in `.env`). The container still listens on 8000 internally.
- **"Evidence" wasn't verbatim.** In the same smoke test the model's `evidence` field paraphrased ("Ra 3.2 is rougher than…", with curly quotes) instead of quoting the vendor text. This confirmed the code-side quote check is needed; the prompt must say "copy the exact sentence, nothing else".

---

## Working with AI

We expect you used AI assistants. This section is about how you worked with
them, not whether you did.

- Which tools you used, and roughly how you split the work with them:
- Something your AI assistant got wrong that you caught and corrected:
  - The build plan hard-coded `temperature=0` from habit; the model chosen rejects it. Caught by testing the model before writing `model.py`, not by trusting the plan.
  - Hidden retries: `ChatOpenAI` leaves `max_retries` unset, so the OpenAI SDK's default of 2 automatic retries applies. One evaluation could silently become 3 API calls, breaking the "one LLM call" rule. Set `max_retries=0` explicitly. Found by reading the installed `langchain_openai` source before writing `model.py`.
  - The model's verdicts needed reading, not just the scores. Prompt v1 gave marketing claims `partial` (fixed in v2, see What broke). At `medium` effort it also marked vendor B's "9 to 11 weeks" as `partial` against "6 weeks from PO"; at `low` effort it correctly said `not_met`. Chose `low`: same pattern, 10–14 s per call instead of 14–30 s.
- Reasoning models use `reasoning_effort` (none/low/medium/high/xhigh for `gpt-6-luna`; `minimal` is rejected), not temperature. Made it an env setting (`LLM_REASONING_EFFORT=medium`).
  - Model choice: rather than accept a model name from memory, I listed the models my key can access (`client.models.list()`), checked OpenAI's pricing page, and ran a trap question ("Ra 3.2 vs Ra 1.6") on the two candidates. Chose `gpt-6-luna` ($0.10 / $0.50 per 1M tokens; both it and `gpt-6-sol`, 20× the price, got the trap right).
- Something you decided to write yourself rather than generate, and why:

---

## Weakest part of this code

The thing you would be least comfortable defending. Be specific — name the
file or function.

- (Candidate, found in Step 2) `scoring.py`: with hand-made verdicts, vendors A and B **both scored 30** on RFQ-001 for opposite reasons. With the real model B scores 36–42 and A is capped at 30, so a certified vendor that can't make the part outranks an uncertified one that can. That's the intended policy, but `GATE_CAP` and the weights are judgement calls, not derived from data.
- (Candidate, found in Step 3) Run-to-run variation: GPT-6 doesn't accept temperature 0, and the same inputs gave B × RFQ-001 36, 42 and 38 across three runs (prompt and effort changes included). Per-line scoring keeps the swing to a few points, but the same vendor can still get a slightly different number on a re-run.
- (Candidate) `quote_found()` checks that a quote exists, not that it's *specific*: a vague but real sentence ("Space-grade heritage.") passes it. The prompt's specificity rule carries that (Step 3).

---

## Next 48 hours

If you had two more days, what is the first thing you would change?
