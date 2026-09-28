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

---

## What you built

What works. Be specific.

---

## What you skipped

What you consciously left out, and why.

- MCP server (was in my starter scaffold) — removed; nothing in the spec needs agents calling into this app, and it would be surface area with no purpose.

---

## Where the spec was unclear

Anything ambiguous, contradictory, or underspecified. What did you assume,
and what did you do about it?

- **`rfqs.json` and the `RFQ-00x.md` files disagree.** RFQ-002's `.md` has no Technical section, while the JSON lists "Coating per MIL-DTL-5541…" and "Parts up to 600 mm" as technical. The `.md` also uses `±` where the JSON uses `+/-`. Assumed the JSON is the source of truth (the spec calls it "ready to load"); the DB stores each RFQ's JSON unchanged and the `.md` files are only for humans.
- **"Seed data loads via a documented command or on first run"**: did both. The API seeds on startup, and `python -m backend.seed` does the same by hand. Both use `INSERT OR IGNORE`, so re-running never duplicates rows.

---

## What broke

Something that did not work first time. What was it, how did you diagnose it,
how did you fix it?

- **`temperature=0` rejected by the model.** The plan assumed temperature 0 for repeatable verdicts. A smoke test against `gpt-6-luna` and `gpt-6-sol` returned `400 — 'temperature' does not support 0.0 with this model. Only the default (1) value is supported.` These are reasoning models. Fix: don't pass `temperature`; repeatability comes from the design instead (small per-line judgements, score computed in code).
- **"Evidence" wasn't verbatim.** In the same smoke test the model's `evidence` field paraphrased ("Ra 3.2 is rougher than…", with curly quotes) instead of quoting the vendor text. This confirmed the code-side quote check is needed; the prompt must say "copy the exact sentence, nothing else".

---

## Working with AI

We expect you used AI assistants. This section is about how you worked with
them, not whether you did.

- Which tools you used, and roughly how you split the work with them:
- Something your AI assistant got wrong that you caught and corrected:
  - The build plan hard-coded `temperature=0` from habit; the model chosen rejects it. Caught by testing the model before writing `model.py`, not by trusting the plan.
  - Hidden retries: `ChatOpenAI` leaves `max_retries` unset, so the OpenAI SDK's default of 2 automatic retries applies. One evaluation could silently become 3 API calls, breaking the "one LLM call" rule. Set `max_retries=0` explicitly. Found by reading the installed `langchain_openai` source before writing `model.py`.
  - Reasoning models use `reasoning_effort` (none/low/medium/high/xhigh for `gpt-6-luna`; `minimal` is rejected), not temperature. Made it an env setting (`LLM_REASONING_EFFORT=medium`).
  - Model choice: rather than accept a model name from memory, I listed the models my key can access (`client.models.list()`), checked OpenAI's pricing page, and ran a trap question ("Ra 3.2 vs Ra 1.6") on the two candidates. Chose `gpt-6-luna` ($0.10 / $0.50 per 1M tokens; both it and `gpt-6-sol`, 20× the price, got the trap right).
- Something you decided to write yourself rather than generate, and why:

---

## Weakest part of this code

The thing you would be least comfortable defending. Be specific — name the
file or function.

---

## Next 48 hours

If you had two more days, what is the first thing you would change?
