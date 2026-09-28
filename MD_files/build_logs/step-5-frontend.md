# Step 5: Frontend (short tour)

**Commit:** `Add single-page UI to pick an RFQ, evaluate a vendor and see history`
**Goal:** one legible page that calls the backend on button clicks. Generated in one go; this is the
tour you need to explain it, not a line-by-line study (the backend is where the interview focuses).

Open it: `docker compose up --build`, then **http://localhost:5173**.

---

## How the page talks to the backend

```
Browser  ──fetch("/api/...")──▶  Vite dev server :5173  ──proxy──▶  backend :8000 (in Docker: http://backend:8000)
```
- The browser only ever talks to **its own origin** (`localhost:5173`). Vite forwards anything under
  `/api` to the backend (`vite.config.ts` → `server.proxy`). The browser never sees a second origin, so **no CORS** is needed.
- The target comes from `VITE_PROXY_TARGET`: Compose sets it to `http://backend:8000`, because inside the
  Compose network each service is reachable by its **service name**. Outside Docker it defaults to `http://localhost:8000`.
- The browser never sees the OpenAI key. Only the backend has it.

## Which click calls which endpoint (`src/api.ts`)

| UI action | Function | Endpoint |
|---|---|---|
| Page load | `getRfqs()` + `getEvaluations()` | `GET /api/rfqs`, `GET /api/evaluations?limit=20` |
| Pick an RFQ | `getRfq(id)` | `GET /api/rfqs/{id}` → tier lists under the dropdown |
| Upload `.txt` | *(none)* | `file.text()` fills the textarea in the browser |
| **Evaluate** | `evaluate(rfqId, text)` | `POST /api/evaluations` → then `getEvaluations()` again |
| Click a history row | *(none)* | shows the already-loaded evaluation |

`request<T>()` in `api.ts` is the one fetch helper. On a non-2xx response it reads FastAPI's
`{"detail": ...}` (a string, or a list of validation errors for 422) and throws a readable `Error`,
which `main.ts` shows in the red error line.

## `src/main.ts`, top to bottom
- **`$()` + element refs**: grabs the DOM elements by id from `index.html`.
- **`esc()`**: HTML-escapes every string from the vendor text or the model before it goes into
  `innerHTML`. Otherwise a vendor profile containing `<script>` would run in the browser (XSS).
- **`updateButton()`**: Evaluate is disabled while no RFQ is chosen, the textarea is blank, or a
  request is running (`busy`), so double-clicks can't fire two LLM calls.
- **`renderRfq()`**: the selected RFQ's quantity, material, delivery and four tier lists.
- **`renderResult(ev)`**:
  - Score box, green ≥ 70 / amber ≥ 40 / red (`scoreClass`).
  - **Gate banner** when `gate_passed` is false: names the failed mandatory line and shows
    `raw_score` ("capped at 30, would have been 77"). This is the answer to the "A and B look alike" issue from Step 2.
  - 3 reasons + 2 gaps, each tagged with its criterion id.
  - Per-tier bars from `breakdown` (points / max).
  - `<details>` table: every requirement, its verdict badge, a ⚠ if our code downgraded it, the quote and the rationale.
- **`loadHistory()`**: table of past evaluations, newest first. Clicking a row finds it in the
  already-loaded list and calls `renderResult`. Rows share the POST response shape (Step 4), so one render function serves both.
- **Wiring**: event listeners for select change, typing, file upload and the Evaluate click
  (sets `busy` → calls the API → renders → refreshes history → `finally` resets `busy`).

## Other files
- `index.html`: the page skeleton (sections with ids that `main.ts` fills in).
- `style.css`: plain CSS with light/dark colours via `prefers-color-scheme`. No framework.
- `vite-env.d.ts`: tells TypeScript that Vite handles `import "./style.css"` (fixed a build error).
- `tsconfig.json`: `strict: true`, `noEmit` (Vite does the bundling; `tsc` only type-checks).
- `Dockerfile`: `node:lts-slim`, `npm install` before copying the code (layer caching), runs `vite --host 0.0.0.0`.
- `docker-compose.yml` → `frontend` service: `VITE_PROXY_TARGET=http://backend:8000`, port `${FRONTEND_PORT:-5173}`,
  `depends_on: backend: condition: service_healthy` (this is where the Step 1 healthcheck pays off).

## Verified
- `npm run build` (type-check + bundle) passes.
- `docker compose up --build`: backend healthy → frontend started; `GET :5173/` serves the page; `/api/rfqs`
  and `/api/evaluations` work **through the proxy**.
- `POST :5173/api/evaluations` with vendor B × RFQ-001 → id 3, score 38, gate passed, 15.9 s.
- Blank vendor text → 422 (shown in the UI as the error line).

## Check questions
1. Why doesn't the frontend need CORS settings on the backend?
2. Where does the OpenAI key live, and can the browser ever see it?
3. What stops a user from triggering two LLM calls by double-clicking Evaluate?

### Answers
1. The browser only calls its own origin (`localhost:5173/api/...`). The Vite server makes the
   request to the backend itself, server-to-server, and CORS only applies to browsers calling a *different* origin.
2. In the backend's environment only (root `.env` → Compose `env_file` → backend container → `config.py` →
   `model.py`). The frontend container doesn't get `.env`, and no API response contains the key.
3. `busy` is set to true before the request and back to false in `finally`, and `updateButton()` disables the
   button while `busy`. The backend also has no retries (`max_retries=0`), so one click is one call.
