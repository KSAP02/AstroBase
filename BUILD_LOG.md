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

**Frontend (Vite + vanilla TypeScript, one page)**
- RFQ dropdown filled from the DB, with the selected RFQ's tiers shown underneath.
- Vendor profile: paste into the textarea, or upload a `.txt` (read in the browser into the same textarea, so there's one backend input path).
- **Evaluate** (disabled while empty or running) → score out of 100 (colour-coded), a red banner when a mandatory requirement fails ("capped at 30, would have been 77"), **3 supporting reasons**, **2 gaps**, per-tier bars, and an expandable per-requirement table with each verdict and its quoted evidence.
- **Past evaluations**, newest first, refreshed after every run; click a row to show it again.
- API errors (422/404/502/503) appear as a readable message; all vendor/model text is HTML-escaped.
- Runs as a second Compose service; its dev-server proxy forwards `/api` to `http://backend:8000`, and it starts only once the backend's healthcheck passes.

---

## What you skipped

What you consciously left out, and why.

- MCP server (was in my starter scaffold) — removed; nothing in the spec needs agents calling into this app, and it would be surface area with no purpose.
- Frontend framework (React etc.): one form and two lists don't need one. Plain TypeScript + DOM keeps the UI readable in one file.
- Production frontend build / nginx image: the container runs the Vite dev server on purpose, so the `/api` proxy works identically in and out of Docker with no CORS or second web-server config. Not for deployment, which the spec rules out.
- Tests / CI: out of scope per the spec. The scoring rules are checked by `experiments/scoring_sanity.py` and model behaviour by the 9-combination matrix instead.
- Styling beyond legible, auth, pagination of history (latest 20 shown), editing or deleting RFQs.

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
- **Frontend build failed on the CSS import.** `tsc` reported `TS2882: Cannot find module or type declarations for side-effect import of './style.css'`. TypeScript doesn't know Vite handles `.css` imports; fixed with the standard `src/vite-env.d.ts` (`/// <reference types="vite/client" />`).
- **Clean-clone test of the non-Docker path.** Following the README from a fresh `git clone`, the Docker path worked first time (fresh DB seeded, evaluation 30 / raw 81, manual seed command reported "0 RFQs (3 already present)"). The non-Docker run first showed Vite `http proxy error … ECONNREFUSED`. Diagnosis: Node resolves `localhost` to IPv6 `::1` and uvicorn listens only on IPv4 `127.0.0.1`; on retest the failure was mainly my script querying Vite before uvicorn had started. Made it unambiguous anyway: the proxy's default target is now `http://127.0.0.1:8000`, and the README examples use `127.0.0.1`.
- **Port 8000 already taken.** `docker compose up` failed with "Bind for 0.0.0.0:8000 failed: port is already allocated", and a request to `:8000/api/evaluations` returned a 404 from a *different* app. `docker ps` + `/openapi.json` showed another local project's backend on 8000. Fix: the compose host port is now `${BACKEND_PORT:-8000}` (8000 by default; I run with `BACKEND_PORT=8001` in `.env`). The container still listens on 8000 internally.
- **"Evidence" wasn't verbatim.** In the same smoke test the model's `evidence` field paraphrased ("Ra 3.2 is rougher than…", with curly quotes) instead of quoting the vendor text. This confirmed the code-side quote check is needed; the prompt must say "copy the exact sentence, nothing else".

---

## Working with AI

We expect you used AI assistants. This section is about how you worked with
them, not whether you did.

- Which tools you used, and roughly how you split the work with them:
  - **Claude Code** (terminal agent) for the whole build. It read the candidate pack, wrote the design and step-by-step plans (`MD_files/`), then built one step at a time: code, running it (Docker, curl, the 9-run matrix), a per-step explainer with check questions in `MD_files/build_logs/`, and a commit.
  - **Me:** the decisions and the review. I chose the stack (FastAPI, SQLite, vanilla TS, OpenAI via LangChain, Docker Compose), the mandatory-gate policy (cap at 30, not zero), the model (after asking for the cheapest capable one to be verified against my key) and the working rhythm: after each backend step, a walkthrough, questions I answered, then the commit. I read the model's verdicts, not just the scores.
- Something your AI assistant got wrong that you caught and corrected:
  - The build plan hard-coded `temperature=0` from habit. I questioned it (reasoning models use reasoning effort, not temperature); testing confirmed `gpt-6-luna` rejects `temperature=0` with a 400, and `model.py` now sets `reasoning_effort` instead.
  - Hidden retries: `ChatOpenAI` leaves `max_retries` unset, so the OpenAI SDK's default of 2 automatic retries applies. One evaluation could silently become 3 API calls, breaking the "one LLM call" rule. Set `max_retries=0` explicitly. Found by reading the installed `langchain_openai` source before writing `model.py`.
  - The model's verdicts needed reading, not just the scores. Prompt v1 gave marketing claims `partial` (fixed in v2, see What broke). At `medium` effort it also marked vendor B's "9 to 11 weeks" as `partial` against "6 weeks from PO"; at `low` effort it correctly said `not_met`. Chose `low`: same pattern, 10–14 s per call instead of 14–30 s.
  - Reasoning effort values: the plan and LangChain's docstring list `minimal / low / medium / high`; `gpt-6-luna` actually accepts `none / low / medium / high / xhigh` and rejects `minimal`. Tested each value before choosing; it's an env setting (`LLM_REASONING_EFFORT=low`).
  - Model choice: rather than accept a model name from memory, I listed the models my key can access (`client.models.list()`), checked OpenAI's pricing page, and ran a trap question ("Ra 3.2 vs Ra 1.6") on the two candidates. Chose `gpt-6-luna` ($0.10 / $0.50 per 1M tokens; both it and `gpt-6-sol`, 20× the price, got the trap right).
- Something you decided to write yourself rather than generate, and why:
  - _TODO (fill in yourself before submitting). Suggested: do one of the scoring drills by hand in `backend/agents/scoring.py` (e.g. make `partial` worth 0.6, or change the gate), predict the result first, run `python experiments/scoring_sanity.py`, and describe what you changed and why here._

---

## Weakest part of this code

The thing you would be least comfortable defending. Be specific — name the
file or function.

**The verdict quality rests on the prompt, `backend/prompts/evaluator_system.md`, and code can only partly check it.** `scoring.py` can prove a quote exists in the profile (`quote_found()`), but not that the *judgement* on it is right. A real quote with the wrong verdict passes: at `medium` effort vendor B's "9 to 11 weeks" was marked `partial` against "6 weeks from PO"; a vague but real sentence ("Space-grade heritage.") would pass the quote check too. The v1 → v2 fix (vendor C 7–11 → 0) came from *reading* verdicts, and there's no automated check that catches that kind of regression.

Related, also weak:
- **Run-to-run variation.** GPT-6 doesn't accept temperature 0; vendor B × RFQ-001 scored 36, 42 and 38 across three runs (with prompt/effort changes in between). Per-line scoring limits the swing, but a re-run can give a slightly different number.
- **The policy numbers are judgement calls.** `TIER_WEIGHTS` (40/35/25) and `GATE_CAP = 30` in `scoring.py` aren't derived from data. With them, certified-but-incapable B (38) outranks capable-but-uncertified A (30, raw 77). That's intended, but defensible only as a stated policy.
- **`build_criteria()` dedupe is textual.** It catches RFQ-002's "600 mm" duplicate but not RFQ-003's differently worded cut-to-size pair, which counts twice.

---

## Next 48 hours

If you had two more days, what is the first thing you would change?

**Turn the 9-run matrix into a labelled evaluation set, so prompt and model changes are measured, not eyeballed.**
- Hand-label the expected verdict for every requirement line in the 9 vendor × RFQ combinations (vendors A and B on RFQ-001 are already labelled in `experiments/scoring_sanity.py`).
- A script that runs each combination ~5 times and reports per-line verdict agreement with the labels and the score spread. Every prompt edit (`PROMPT_VERSION`), model or reasoning-effort change then gets a number, and the v1 "marketing earns partial" regression would have been caught automatically.
- Then, in order: add a few harder vendor profiles (near-miss certificates, mixed evidence); make dedupe semantic (have `build_criteria` flag overlapping lines once per RFQ at seed time instead of by substring); show the raw score in the history list, not only in the result banner.
