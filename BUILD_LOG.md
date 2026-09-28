# Build Log

Fill this in as you go, or at the end. Keep it short — bullet points are fine.
This is read as carefully as the code.

---

## Stack

What you used and why. One line each.

- Frontend: Vite + vanilla TypeScript. One form and two lists don't need a framework.
- Backend: Python + FastAPI. Pydantic models serve as both request validation and the LLM output schema.
- Database: SQLite via stdlib `sqlite3`, no ORM. Two tables, zero setup.
- LLM / agent: OpenAI `gpt-6-luna` via LangChain (prompt template + structured output only). One call per evaluation, no agent loop.
- Run: Docker Compose (`docker compose up --build`).

---

## Scoring approach

How does your agent arrive at a number? What did you do to make that number
mean something?

**The LLM judges each requirement; code computes the number** (`backend/agents/scoring.py`).

- The RFQ is split into labelled lines (M = mandatory, T = technical incl. material/quantity/delivery, R = required, P = preferred).
- One LLM call returns a verdict per line (`met / partial / not_met / not_evidenced / not_applicable`) with a **verbatim quote** from the profile. It never outputs a score.
- Code then:
  - **downgrades** any `met`/`partial` whose quote isn't actually in the vendor text (catches invented/paraphrased evidence);
  - weights tiers **technical 40 / required 35 / preferred 25** (`met` 1, `partial` 0.5, else 0; `not_applicable` excluded);
  - **caps the score at 30 if any mandatory line isn't met**. A cap, not zero, so "strong but uncertified" ≠ "nothing matches".
- The prompt rubric targets the sample traps: vague claims → `not_evidenced`, exact certificate match only, lower Ra is finer, lead-time basis must match.

Results, all 9 combinations (`experiments/matrix_v2_low.md`):

| Vendor | RFQ-001 | RFQ-002 | RFQ-003 |
|---|---|---|---|
| A: strong machinist, no AS9100D | **30** (raw 77, capped) | 0 | 12 |
| B: AS9100D, can't make the part | **38** | 0 | 12 |
| C: marketing copy only | **0** | **0** | **0** |

---

## What you built

What works. Be specific.

- Single page: pick an RFQ, paste or upload a `.txt` profile, Evaluate → score /100, 3 reasons, 2 gaps, a banner when a mandatory requirement caps the score, and a per-requirement table with each verdict and its quote.
- Past evaluations listed newest first; click to reopen.
- RFQs seeded from `rfqs.json` on startup and via `python -m backend.seed` (idempotent).
- Every evaluation stored with verdicts, raw model output, token usage, model and prompt version (audit trail).
- Clear errors: 422 bad input, 404 unknown RFQ, 503 LLM not configured, 502 LLM call failed. SDK retries disabled, so one click = one call.
- README verified on a fresh clone.

---

## What you skipped

What you consciously left out, and why.

- Tests/CI (out of scope): replaced by two scripts, `experiments/scoring_sanity.py` (rules, hand-made verdicts) and `experiments/run_matrix.py` (9 live runs).
- Frontend framework, production build/nginx: the Vite dev server's proxy avoids CORS and works identically in Docker.
- MCP server from my starter scaffold: removed, nothing needed it.
- Auth, history pagination, editing RFQs, styling beyond legible.

---

## Where the spec was unclear

Anything ambiguous, contradictory, or underspecified. What did you assume,
and what did you do about it?

- **`rfqs.json` vs the `.md` files differ** (e.g. RFQ-002's `.md` has no Technical section) → JSON is the source of truth.
- **"AI agent" + "one LLM call"** → one structured call, no loop, no retries.
- **Exactly 3 reasons / 2 gaps even with no real strengths** (vendor C) → always 3/2; honest wording, code pads if short.
- **Duplicate requirements** (RFQ-002 "600 mm" technical and preferred) → deduped, counted once. RFQ-003's differently worded cut-to-size pair isn't caught (known).
- **Quantity/material/delivery sit outside the tiers** → judged as technical lines.
- **Lead time "from receipt of material" vs "from PO"** → at best `partial`.
- **History for all RFQs or only the selected one?** → all, newest first.

---

## What broke

Something that did not work first time. What was it, how did you diagnose it,
how did you fix it?

- **Prompt v1 let marketing copy score.** Scores looked plausible (vendor C 7–11), but the assistant's review of the per-line verdicts showed `partial` given to phrases like "multi-axis" (for 5-axis). The quote check couldn't catch it because the quotes were real. v2 added "partial needs specific evidence too" → C = 0 on all three RFQs. Both runs are kept in `experiments/`.
- **`temperature=0` rejected** (400): GPT-6 models are reasoning models. Removed it; set `reasoning_effort` instead.
- **Port 8000 taken** by another local project → host port made configurable (`BACKEND_PORT`).

---

## Working with AI

We expect you used AI assistants. This section is about how you worked with
them, not whether you did.

- Which tools you used, and roughly how you split the work with them:
  - **Claude Code** (one session, transcript in `AI_SESSION_TRANSCRIPT.jsonl`) wrote the plans, all the code, the prompts, the test scripts and the docs, ran everything (Docker, the 9-run matrix, a clean-clone test) and analysed the results.
  - **Me:** I set the project conventions beforehand (`CLAUDE.md`, from an earlier session), chose the stack and asked for Docker Compose, chose the gate policy (cap at 30) from the options offered, asked for the most cost-efficient capable current model (the assistant verified the options against my key), and set the working rhythm: one step per commit, a walkthrough and check questions after each backend step, and a spec audit before the final commit. I then questioned the design until I could explain it (DB initialisation, where the RFQ is flattened, the scoring maths, how the quote check works, why it isn't done by the LLM).
  - Time: about 2.5 hours from reading the spec to a working app, about 3 hours including README and BUILD_LOG; the rest of the session was studying the code (notes in `MD_files/build_logs/`).
- Something your AI assistant got wrong that you caught and corrected:
  - The plan assumed `temperature=0`. A smoke test returned a 400, and I pointed out that reasoning models are tuned with reasoning effort, not temperature, so `model.py` sets `reasoning_effort` instead.
  - I asked for the LangChain model setup to be checked before it was implemented. That check (by the assistant, in the installed source) found the SDK retries twice by default, which could make one evaluation 3 calls → `max_retries=0`.
  - Not my catch, but worth recording: the assistant chose the model by testing rather than memory (listed the models on my key, checked pricing, ran a trap question) and compared reasoning effort `low` vs `medium` over all 9 runs (same results, `low` ~2× faster).
- Something you decided to write yourself rather than generate, and why:
  - No code by hand. When offered the choice for the scoring code, I had the assistant write it and walk me through it line by line instead, because in the timebox I prioritised being able to explain and modify every line in the interview over typing it. What I did decide myself is the scoring policy (cap at 30, not zero) and the constraints the AI worked within (`CLAUDE.md`).

---

## Weakest part of this code

The thing you would be least comfortable defending. Be specific — name the
file or function.

**Verdict quality depends on the prompt (`backend/prompts/evaluator_system.md`).** Code can prove a quote exists (`quote_found()` in `scoring.py`) but not that the judgement on it is right, and nothing automated would catch a regression like v1's; that one was found only by reading the verdicts. Also: scores vary a few points between runs (no temperature 0), and the weights and cap are judgement calls.

---

## Next 48 hours

If you had two more days, what is the first thing you would change?

**A labelled evaluation set.** Hand-label the expected verdict per requirement for the 9 combinations, run each several times, and report agreement and score spread. Every prompt or model change then gets a number instead of an eyeball check.
