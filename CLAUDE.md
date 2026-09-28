# CLAUDE.md

Guidance for Claude Code when working in this repository.

This is a **lean starter scaffold**, not a fixed architecture. It exists to give a new
project somewhere to put things on day one — it does not lock in a framework, a
database, or a model provider. Every choice below is a default, override freely as the
project's actual needs become clear.

---

## 1. Directory layout

```
<project-root>/
├── .claude/                 # Claude Code config (project-level, committed)
│   ├── settings.json        # Shared settings: permissions, hooks wiring, env. Starts as {}
│   ├── hooks/               # Hook scripts that settings.json points at
│   └── skills/              # Project skills, one folder each: skills/<name>/SKILL.md
├── backend/                 # API layer — the single source of truth for logic
│   ├── main.py              # Entrypoint — wiring only: app, routes, startup/shutdown
│   ├── config.py            # Settings loaded from env (whatever lib you like)
│   ├── model.py             # THE ONLY place a model client gets constructed — see §3
│   ├── agents/              # Agent/orchestration logic lives here (calls model.py)
│   └── db.py                # Optional. Delete if the project has no database.
├── mcp-server/                # Optional. A thin pathway INTO the backend — see §4
│   ├── .env                  # MCP-only config (BACKEND_URL, transport) — never committed
│   ├── .env.example          # Mirrors mcp-server/.env with no values
│   └── src/                  # Import layers, one-directional: config <- tools <- server
│       ├── config.py         # Layer 0. Loads mcp-server/.env — how to reach the backend, nothing else
│       ├── tools.py          # Layer 1. Each tool = one call to the backend's HTTP API, nothing more
│       └── server.py         # Layer 2. FastMCP instance + transport (stdio/HTTP); owns registration
├── frontend/                 # Node.js + TypeScript. Framework inside is open — see §6
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
├── data_warehouse/           # Datasets, sample repos, seed data, exported metrics
├── experiments/              # Scratch notebooks, prototypes, throwaway scripts
├── MD_files/                 # Idea docs, design notes, generated artifacts
├── .env                      # Secrets — never committed
├── .env.example              # Every key in .env, mirrored with no values
├── .gitignore
├── docker-compose.yml        # Optional. Add services only once they're real.
├── requirements.txt          # Python deps (backend + mcp-server)
└── README.md
```

Empty folders are fine — keep a `.gitkeep` in ones with nothing in them yet. Delete
anything above that the project genuinely doesn't need (no frontend? delete it) rather
than leaving a hollow placeholder around "in case."

**One-shot scaffold** (skip any line for a piece you're not using):

```bash
mkdir -p .claude/hooks .claude/skills backend/agents mcp-server/src frontend/src data_warehouse experiments MD_files
[ -f .claude/settings.json ] || echo '{}' > .claude/settings.json
touch .claude/hooks/.gitkeep .claude/skills/.gitkeep
touch backend/main.py backend/config.py backend/model.py \
      mcp-server/src/config.py mcp-server/src/server.py mcp-server/src/tools.py \
      mcp-server/.env mcp-server/.env.example \
      frontend/package.json frontend/tsconfig.json \
      .env .env.example .gitignore docker-compose.yml requirements.txt README.md
touch data_warehouse/.gitkeep experiments/.gitkeep MD_files/.gitkeep
```

```powershell
$dirs = '.claude/hooks','.claude/skills','backend/agents','mcp-server/src','frontend/src','data_warehouse','experiments','MD_files'
$dirs | ForEach-Object { New-Item -ItemType Directory -Force $_ | Out-Null }
$files = 'backend/main.py','backend/config.py','backend/model.py',
         'mcp-server/src/config.py','mcp-server/src/server.py','mcp-server/src/tools.py',
         'mcp-server/.env','mcp-server/.env.example',
         'frontend/package.json','frontend/tsconfig.json',
         '.env','.env.example','.gitignore','docker-compose.yml','requirements.txt','README.md'
$files | ForEach-Object { if (-not (Test-Path $_)) { New-Item -ItemType File $_ | Out-Null } }
if (-not (Test-Path .claude/settings.json)) { Set-Content -Encoding ascii .claude/settings.json '{}' }
'.claude/hooks','.claude/skills','data_warehouse','experiments','MD_files' | ForEach-Object {
  $k = Join-Path $_ '.gitkeep'; if (-not (Test-Path $k)) { New-Item -ItemType File $k | Out-Null }
}
```

> Never use `New-Item -Force` on a **file** — it truncates anything already there.
>
> `.claude/settings.json` starts as `{}`, not an empty file, because an empty file isn't
> valid JSON. It's written as ASCII so Windows PowerShell 5.1 doesn't prepend a BOM.
> Personal overrides go in `.claude/settings.local.json`, which stays uncommitted.

---

## 2. Stack — starting defaults, not requirements

| Layer | Default | Swap freely for |
| --- | --- | --- |
| Backend | **Python**, FastAPI + Uvicorn, latest stable | The framework only — Flask, Django, etc. Language is fixed to Python. |
| Frontend | **Node.js + TypeScript**, latest LTS, plain server or static page | The framework only — Vite/React, Next.js, etc. Runtime/language is fixed. |
| Agent/LLM layer | One `agents/` module, provider chosen via `.env` | Any orchestration approach — see §3 |
| MCP server | **`fastmcp`** (the standalone package), skip until an agent needs tool-calling in | A thin proxy in front of the backend — see §4 (Python, same as backend) |
| Database | None until actually needed | SQLite/DuckDB to start, Postgres if it grows |
| Packaging | `docker-compose.yml`, added incrementally | Whatever ships it |

Backend language (Python) and frontend language/runtime (Node.js + TypeScript) are
settled up front and not revisited per-project — everything else in this table is a
framework-level choice, made when the project's actual needs are known. No version is
pinned anywhere on purpose: use whatever "latest stable" resolves to when you set up.
Pin a version later only if reproducibility actually requires it (e.g. a Docker base
image for a deploy target).

Don't reach for a heavier tool (a multi-agent framework, a vector DB, a message queue)
until the simple version has actually run out of room. Early on, the simple version
usually hasn't.

---

## 3. The one rule that actually matters: model/provider choice is config, not code

The project may end up calling a hosted API (Anthropic/OpenAI/Gemini/etc.), a local
model, or more than one of these at once. Whatever it is, **isolate the model client
construction in exactly one module** (`backend/model.py`) and have every other file
call *that*, never a provider SDK directly.

```
LLM_PROVIDER=<anthropic | openai | ibm | ollama | ...>
LLM_MODEL=<provider's model id>
LLM_API_KEY=<key, or blank for a local/keyless endpoint>
LLM_BASE_URL=<optional: any OpenAI-compatible endpoint>
```

- The **root** `.env` holds these; `.env.example` documents the keys with no values.
  `backend/config.py` is the only reader — `model.py` gets them via `get_settings()`.
  The MCP server has its own `.env` and never sees a model key (see §4).
- Swapping models/providers mid-project should be an `.env` edit, not a code change.
- It's fine to use a framework (LangChain, LangGraph, CrewAI, an agent platform's own
  orchestration, or nothing at all — direct SDK calls) — the framework choice is
  separate from this rule. The rule is just: one seam, not model names scattered across call sites.
- If a key/package is missing, fail with a clear message naming what's missing and how
  to fix it — never let it surface as a raw `ImportError` or an opaque 500 deep in a
  request handler.

---

## 4. If there's an MCP server, it's a pathway — not a second backend

`mcp-server/` exists only to let any MCP-speaking agent call into this project as a
set of tools. It is a **connector, not a place logic lives twice**:

```
agent (MCP client) ──MCP──▶ mcp-server/src/tools.py ──HTTP──▶ backend API ──▶ db / model / etc.
```

- **Every tool in `mcp-server/src/tools.py` is a thin wrapper**: take the tool call's
  arguments, hit the backend's HTTP API (`BACKEND_URL`), return the result. No business
  logic, no direct database access, no model calls from inside the MCP server.
- **The backend is the only source of truth.** If both the REST API and an MCP tool need
  to do the same thing, that behavior lives once in `backend/`, and the tool just calls
  it. Duplicating logic between the two is exactly what this structure is meant to avoid.
- Type hints and docstrings on each tool become the schema the agent sees — write them
  for that reader, but keep the actual work on the backend side of the HTTP call.
- **`mcp-server/` has its own `.env` and `src/config.py`**, separate from the root `.env`.
  It is deliberately narrow: how to reach the backend and how to serve MCP, nothing else.
  No `LLM_*` keys belong here — the MCP server never talks to a model.
- **No circular imports, by construction.** `src/` is three one-directional layers —
  `config` (imports no sibling) ← `tools` (imports `config`) ← `server` (imports both).
  Never import "upward": `tools.py` must not import `server`. Concretely, `tools.py`
  exports **plain functions** plus a `TOOLS` list, and `server.py` is the only module
  that touches the FastMCP object — it registers them with `mcp.add_tool(fn)`. The
  tempting `@mcp.tool` in `tools.py` + `from server import mcp` is the cycle; avoid it.
  A new tool is a function plus one entry in `TOOLS`, nothing else.
- **Errors get translated, not leaked.** A tool raises `ToolError` carrying the backend's
  own `detail` (and a "backend unreachable at …, start it with …" message when the
  backend is down). Otherwise the agent just sees an opaque `503` — see §3's last bullet.
  Translation is the *only* thing a tool is allowed to do besides the HTTP call.
- If the project never needs agent tool-calling into itself, delete `mcp-server/`
  entirely rather than leaving it as dead scaffolding.

`mcp-server/.env`:

```
MCP_SERVER_NAME=<name the agent sees>
MCP_TRANSPORT=<stdio | http | sse | streamable-http>
MCP_HOST=127.0.0.1
MCP_PORT=8765
BACKEND_URL=http://localhost:8000
REQUEST_TIMEOUT=120
```

**Use `fastmcp`, the standalone package** (`pip install fastmcp`, in `requirements.txt`)
— `from fastmcp import FastMCP`. Two traps worth knowing:

- **Not** `from mcp.server.fastmcp import FastMCP`. That's the low-level `mcp` SDK, now
  at 2.x, where `FastMCP` was renamed `MCPServer` and that import path raises
  `ModuleNotFoundError`. `fastmcp` pulls `mcp` in as a dependency; depend on `fastmcp`.
- `host`/`port` are **`run()` kwargs, not constructor args** — `FastMCP(name)`, then
  `mcp.run(transport=..., host=..., port=...)`. `stdio` accepts neither.

Transports: `stdio` (local agent) | `http` | `sse` | `streamable-http`.

---

## 5. Light conventions

- **`backend/main.py` is wiring only.** Routes, middleware, startup/shutdown. Actual
  logic lives in `model.py` / `agents/` (or wherever it naturally belongs) — keeps
  `main.py` readable as the project grows.
- **Two `.env` files, two owners.** Root `.env` = backend + frontend (`LLM_*`, `PORT`,
  `BACKEND_URL`). `mcp-server/.env` = the MCP server only. Both are gitignored; both
  have a committed `.example` mirror.
- **Optional subsystems (a database, an extra agent framework) are imported inside the
  handler that needs them, not at module top.** That way the app still boots when an
  optional piece isn't installed or configured yet.
- **No inline comments in `.env` files.** `env_file` in Docker Compose doesn't strip a
  trailing `# ...` — it becomes part of the value. Comments go on their own line.
- **Secrets never committed.** `.gitignore` should cover at minimum: `.env`,
  `mcp-server/.env` (if it has its own), `__pycache__/`, `.venv/`, `node_modules/`,
  `dist/`, and any bulk data dropped into `data_warehouse/`.
- Keep the manifest (`requirements.txt`, `package.json`) flat and honest — add a
  dependency when you use it, remove it when you stop.
- **Import direction is a rule, not a style.** Within any package, keep sibling imports
  one-directional (`config` ← `tools` ← `server` in `mcp-server/src/`; `config` ←
  `model` ← `main` in `backend/`). If two modules want each other, the shared thing
  belongs in a lower layer — or one of them should take it as an argument.

---

## 6. Deliberately left open

Pick these once the actual shape of the project is clear — don't pre-decide them here:

- **Agent orchestration approach** — plain API calls, a framework, or an agent
  platform's own agent/subagent mode — whatever the task makes easiest.
- **Backend framework** — FastAPI is the default; Flask/Django/etc. are fine too.
  Python itself is the only fixed part.
- **Database** — skip it until there's real state to persist.
- **Frontend framework** — a static page is a legitimate UI; upgrade to
  Vite/React/Next/etc. only if the project needs it. Node.js + TypeScript itself is the
  only fixed part.
- **Version pins** — none. Use latest stable; pin later only if reproducibility needs it.
- **Testing/CI/linting** — not set up here. Add it when the project warrants it.

---

## 7. Commands (adjust once the real stack is chosen)

```bash
python -m venv .venv && source .venv/bin/activate       # macOS / Linux
python -m venv .venv && source .venv/Scripts/activate    # Windows Git Bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

cd mcp-server && python src/server.py    # only if mcp-server/ is in use; needs the backend up
                                         # transport/port come from mcp-server/.env

cd frontend && npm install && npm run dev

docker compose up --build     # once docker-compose.yml has real services in it
```
