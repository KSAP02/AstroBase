# Step 4: Save evaluations and list them (history API)

**Commit:** `Persist evaluations and list them newest first`
**Goal:** every evaluation leaves a row in SQLite, and `GET /api/evaluations` returns them newest
first. That covers the SPEC's "past evaluations are listed below, most recent first", plus an audit trail.

---

## What changed

### `backend/db.py`: two new functions
**`insert_evaluation(evaluation, vendor_text, raw) -> (id, created_at)`**
- `created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")`, e.g. `2026-09-28T08:24:47+00:00`.
  UTC so it's unambiguous; ISO-8601 strings **sort correctly as text**, which is what makes
  `ORDER BY created_at` work in SQLite (which has no real date type).
- One `INSERT` with `?` placeholders. Columns worth noting:
  - `score`, `gate_passed`, `vendor_name`, `model`, `prompt_version` are real columns: cheap to
    filter or sort on later.
  - `result` is a JSON blob: `{"evaluation": <the API response>, "raw": {"content": <model's JSON text>, "usage": <tokens>}}`.
    Everything needed to redisplay the result *and* to audit what the model actually said.
  - `gate_passed` stored as `int(...)`: SQLite has no boolean type; 0/1 is the convention.
- `cur.lastrowid` is the id SQLite assigned (`AUTOINCREMENT`).

**`list_evaluations(limit=20) -> list[dict]`**
- `SELECT id, created_at, result ... ORDER BY created_at DESC, id DESC LIMIT ?`. Newest first; `id`
  breaks ties when two evaluations land in the same second.
- Each row is rebuilt into the **same shape as the POST response** (`{**evaluation, "id", "created_at"}`),
  so the frontend renders a history item and a fresh result with the same code.

### `backend/schemas.py`
`EvaluationOut` gained `id: int | None = None` and `created_at: str | None = None`. They're `None` inside
the evaluator (not saved yet) and filled in by `main.py` after the insert.

### `backend/main.py`
```python
evaluation, raw = evaluate_vendor(rfq, req.vendor_text)          # _raw is no longer thrown away
eval_id, created_at = db.insert_evaluation(evaluation.model_dump(), req.vendor_text, raw)
return evaluation.model_copy(update={"id": eval_id, "created_at": created_at})
```
- `model_dump()` turns the Pydantic object into a plain dict for `db.py`, which deliberately knows
  nothing about Pydantic, only dicts and SQL.
- `model_copy(update=...)` returns a copy with the two new fields set.
- New route `GET /api/evaluations?limit=20`. `Query(20, ge=1, le=100)` means FastAPI rejects
  `limit=0` or `limit=1000` with a 422 before our code runs.
- Only a **successful** evaluation is saved. A 502 or 503 raises before the insert, so failed calls leave no row.

---

## Verified
| Check | Result |
|---|---|
| POST A × RFQ-001, then C × RFQ-002 | ids 1 and 2, with `created_at`; scores 30 and 0 |
| `GET /api/evaluations` | id 2 first, then id 1; each with 3 reasons, 2 gaps |
| `?limit=0` | 422 |
| `docker compose down` → `up` | still 2 rows (DB file on the host volume) |
| DB row | `model=gpt-6-luna`, `prompt=v2`, raw usage stored: 1 757 input / 1 154 output tokens (368 reasoning), ≈ $0.0008 |

---

## Drill
Add `?rfq_id=RFQ-001` filtering to `GET /api/evaluations`: an optional `rfq_id: str | None = None` in the
route, passed to `list_evaluations`, adding `WHERE rfq_id = ?` when set. (There's already an
`rfq_id` column, which is why it's a real column and not only inside the JSON.)

---

## Check questions
1. A reviewer asks "why did vendor A get 30 last Tuesday?" What in the DB answers that?
2. What changes for old rows when we bump `PROMPT_VERSION` to v3?
3. Why is `created_at` a text column, and why does sorting it work?
4. Does a failed LLM call create a row?

### Answers
**1.** The row's `result` JSON holds every line's verdict, quote and rationale, the per-tier
breakdown, and the model's raw output, plus the `model` and `prompt_version` columns and the exact
`vendor_text`. You can see which line failed (M1 AS9100D → gate capped at 30) and what the model said,
under which prompt and model.

**2.** Nothing. Old rows keep `prompt_version = "v2"` and their stored verdicts. New rows get `"v3"`.
Nothing is recomputed. That's the point: history shows what was actually decided at the time, and
the version tells you under which rules.

**3.** SQLite has no date type. ISO-8601 strings in one fixed format and time zone
(`2026-09-28T08:24:47+00:00`) sort alphabetically in the same order as chronologically, so
`ORDER BY created_at DESC` is newest first.

**4.** No. `evaluate_vendor` raises (`LLMConfigError` or `LLMCallError`), `main.py` turns it into a 503 or
502, and the `insert_evaluation` line is never reached.
