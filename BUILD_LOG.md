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

---

## What broke

Something that did not work first time. What was it, how did you diagnose it,
how did you fix it?

---

## Working with AI

We expect you used AI assistants. This section is about how you worked with
them, not whether you did.

- Which tools you used, and roughly how you split the work with them:
- Something your AI assistant got wrong that you caught and corrected:
- Something you decided to write yourself rather than generate, and why:

---

## Weakest part of this code

The thing you would be least comfortable defending. Be specific — name the
file or function.

---

## Next 48 hours

If you had two more days, what is the first thing you would change?
