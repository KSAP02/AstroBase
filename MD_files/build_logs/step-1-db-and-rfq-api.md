# Step 1: SQLite, seeding, RFQ API and the backend container

**Commit:** `Store RFQs in SQLite and serve them through the API`
**Goal:** the three RFQs live in a database, the API serves them, and `docker compose up --build`
starts it all. No LLM yet.

---

## The big picture

```
                    ┌──────────────────────── backend/ ───────────────────────────┐
 curl / browser ──▶ │ main.py  (routes)  ──▶  db.py  (SQL)  ──▶  astrobase.db      │
                    │    │                      ▲                                  │
                    │    └── on startup ────────┘ init_db() + seed_rfqs()          │
                    │                           ▲                                  │
                    │ config.py (reads .env) ───┘ db_file / seed_file paths        │
                    │ seed.py  (python -m backend.seed: same seeding, by hand)     │
                    └──────────────────────────────────────────────────────────────┘
```
Import direction (no cycles): `config ← db ← main`, `config + db ← seed`.

---

## File by file

### `backend/config.py`: the only place configuration is read
- `ROOT_DIR = Path(__file__).resolve().parent.parent`: the repo root, worked out from this file's
  own location. On your machine it's `D:\...\AstroBase`; inside Docker it's `/app`.
- `class Settings(BaseSettings)`: **pydantic-settings** fills each field from an environment
  variable with the same name (case-insensitive), falling back to the `.env` file, then the default.
  `LLM_MODEL=gpt-6-luna` in `.env` becomes `settings.llm_model == "gpt-6-luna"`.
  - `extra="ignore"`: unknown keys in `.env` don't crash the app.
  - A **missing** `.env` is fine. In Docker, Compose's `env_file:` passes the same values as real
    environment variables, and `.env` itself is never copied into the image.
- `db_file` / `seed_file` properties turn the relative strings from `.env` into absolute paths
  anchored at `ROOT_DIR` (via `_from_root`). **Why:** so the app finds the DB no matter which folder
  you start it from, and the same `DB_PATH=data_warehouse/astrobase.db` works on Windows and in the container.
- `@lru_cache get_settings()`: builds `Settings` once and then returns the same object on every
  call. It's cheap and consistent, and it's the single seam for config (CLAUDE.md §3).

### `backend/db.py`: all SQL lives here
- `SCHEMA`: two `CREATE TABLE IF NOT EXISTS` statements. `IF NOT EXISTS` makes creating the tables
  safe to repeat. The `evaluations` table is created now but only written to in Step 4.
- **Why the RFQ is one JSON column (`data`)** instead of separate tables for technical, mandatory
  and so on: we never query *inside* an RFQ with SQL. We only ever load a whole RFQ and hand it to the
  evaluator. `id`, `title` and `category` are real columns because the dropdown needs them.
- `get_conn()`: a small **context manager** (`with get_conn() as conn:`):
  1. opens the SQLite file,
  2. sets `row_factory = sqlite3.Row` so rows act like dicts (`row["title"]`),
  3. turns on foreign keys (SQLite leaves them off by default),
  4. **commits** if the `with` block finished without an error,
  5. **always closes** the connection (`finally`).
  Why not `with sqlite3.connect(...) as conn:`? That form commits but **doesn't close** the
  connection, a common sqlite3 gotcha.
- `init_db()`: creates `data_warehouse/` if it's missing, then runs the schema.
- `seed_rfqs()`: reads `rfqs.json` and runs `INSERT OR IGNORE` for each RFQ. `OR IGNORE` means "if
  this primary key already exists, skip it quietly". `cur.rowcount` is 1 for an insert and 0 for a
  skip, which gives the `(inserted, already_present)` counts.
- `list_rfqs()`: `SELECT id, title, category ... ORDER BY id` → list of dicts (for the dropdown).
- `get_rfq(id)`: selects the `data` column and `json.loads` it back into a dict, or returns **`None`**
  if there's no such id. The DB layer doesn't know about HTTP, so it reports "not found" as `None`
  and lets the route decide that this means a 404.
- **`?` placeholders** (`WHERE id = ?`): values are passed separately from the SQL text, so input
  can never be run as SQL (no SQL injection).

### `backend/seed.py`: the documented seed command
`python -m backend.seed` → `init_db()` + `seed_rfqs()` → prints `Seeded 3 RFQs (0 already present)`.
The `-m` form runs it as a module of the `backend` package, which is why `backend/__init__.py`
matters. It does exactly what startup does; it's there because the SPEC asks for "a documented
command **or** first run", and we provide both.

### `backend/main.py`: wiring only
- `lifespan(app)`: FastAPI runs the code **before `yield`** once when the server starts, and code
  after `yield` on shutdown. We create the tables and seed there, so a brand-new clone works with
  no manual step.
- `app = FastAPI(title="AstroBase", lifespan=lifespan)`.
- Three routes:
  - `GET /api/health` → `{"status": "ok"}`. Docker's healthcheck calls this.
  - `GET /api/rfqs` → `db.list_rfqs()`. FastAPI turns the list of dicts into JSON.
  - `GET /api/rfqs/{rfq_id}` → `db.get_rfq()`, and `None` becomes `HTTPException(404, ...)`, which
    FastAPI returns as `{"detail": "RFQ NOPE not found"}` with status 404.
- The routes are plain `def`, not `async def`. FastAPI runs plain `def` routes in a worker thread,
  which is right for blocking calls like `sqlite3`. Each call opens its own connection in its own
  thread, so there are no "SQLite objects created in a thread…" errors.

### `backend/Dockerfile`
1. `FROM python:3.13-slim`: small official Python image (same version as your venv).
2. `COPY requirements.txt` + `pip install` **before** copying the code. Docker caches each step, so
   editing a `.py` file doesn't reinstall every package, only changing `requirements.txt` does.
3. `COPY backend/` and `COPY data_warehouse/seed/`: the code and the seed JSON.
4. `CMD uvicorn backend.main:app --host 0.0.0.0 --port 8000`. `0.0.0.0` means "listen on all
   interfaces", needed so traffic from outside the container can reach it (`127.0.0.1` would only
   accept traffic from inside the container).
- Build context is the **repo root** (set in compose), and `.dockerignore` keeps `.env`, the venv
  and the DB out. Verified: `/app` in the container has no `.env`.

### `docker-compose.yml` (backend service only for now)
- `build: context: . / dockerfile: backend/Dockerfile`: build from the repo root.
- `env_file: .env`: injects `LLM_*` etc. as environment variables **at runtime**.
- `ports: "8000:8000"`: host port 8000 → container port 8000.
- `volumes: ./data_warehouse:/app/data_warehouse`: the container's `data_warehouse` folder **is**
  your local folder, so `astrobase.db` appears on your disk and survives `docker compose down`.
- `healthcheck`: every 5 s, run a tiny Python snippet that requests `/api/health`. The container
  shows `healthy` once it answers. In Step 5 the frontend waits for this before starting.

---

## What we verified
| Check | Result |
|---|---|
| `python -m backend.seed` twice | `3 (0 already present)`, then `0 (3 already present)` |
| Tables | `rfqs`, `evaluations`, plus `sqlite_sequence` (SQLite's internal counter for `AUTOINCREMENT`) |
| Deleted the DB, then `docker compose up --build` | Container became `healthy`; DB recreated **on the host** |
| `GET /api/health` | `{"status":"ok"}` |
| `GET /api/rfqs` | 3 RFQs (id, title, category) |
| `GET /api/rfqs/RFQ-002` | Full JSON |
| `GET /api/rfqs/NOPE` | `{"detail":"RFQ NOPE not found"}`, HTTP 404 |
| `.env` inside the image? | Not present |
| `docker compose restart backend` | Still exactly 3 RFQs |

Nothing failed in this step.

---

## Drill (try one; they're the kind of change the interview asks for)
- **A.** Add `?category=Machining` filtering to `GET /api/rfqs`.
  *Hint:* add `category: str | None = None` to the route's parameters (FastAPI treats it as a query
  parameter), pass it to `db.list_rfqs(category)`, and add `WHERE category = ?` when it's set.
- **B.** Make `/api/health` also return how many RFQs are in the DB: `{"status": "ok", "rfqs": 3}`.

---

## Check questions

1. If I delete `astrobase.db` and restart, what happens and why?
2. Where would a 4th RFQ go, and what makes it appear in the dropdown?
3. Why does `get_rfq` return `None` instead of raising, and who turns that into a 404?
4. Why is the Docker `CMD` using `--host 0.0.0.0`?
5. Why is `requirements.txt` copied and installed before the code in the Dockerfile?

### Answers

**1.** On the next start, `lifespan` runs `init_db()`, which recreates the folder and both tables
(`CREATE TABLE IF NOT EXISTS`), then `seed_rfqs()` reinserts the 3 RFQs from `rfqs.json`. You get a
fresh DB with the RFQs but **no past evaluations**, because those only ever existed in the deleted
file. (We tested exactly this before starting the container.)

**2.** Add it as a new object in `data_warehouse/seed/rfqs.json` with the same fields, then restart the
API or run `python -m backend.seed`. `INSERT OR IGNORE` skips the 3 existing ids and inserts the new
one. The dropdown calls `GET /api/rfqs` → `list_rfqs()` → `SELECT … FROM rfqs`, so it shows up with
no code change. (Editing an *existing* RFQ in the JSON would **not** update it, because `OR IGNORE`
skips existing ids. You'd delete the DB or switch to an upsert.)

**3.** Separation of layers: `db.py` knows about data, not HTTP. "No such RFQ" is a normal result,
not an error, so it returns `None`. The **route in `main.py`** decides what that means for an API
client and raises `HTTPException(status_code=404)`. The evaluator in Step 3 reuses `get_rfq` and
makes the same check.

**4.** Inside a container, `127.0.0.1` means *the container itself*. Docker's port mapping
(`8000:8000`) forwards traffic arriving from outside the container, which only reaches uvicorn if
it listens on all interfaces (`0.0.0.0`). With `127.0.0.1` the container would be "running" but
`curl localhost:8000` on your machine would get no response.

**5.** Layer caching. Docker reuses a step's cached result if its inputs haven't changed. Code
changes often and dependencies rarely, so installing dependencies first means a code-only change
rebuilds in seconds instead of reinstalling FastAPI and LangChain every time.
