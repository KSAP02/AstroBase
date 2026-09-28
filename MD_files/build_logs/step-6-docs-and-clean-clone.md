# Step 6: README, final BUILD_LOG, clean-clone test

**Commit:** `Document setup and record build decisions`
**Goal:** the two remaining required deliverables (a README that works on a clean clone, and a
complete BUILD_LOG), proven by actually following the README from a fresh clone.

---

## README.md: what a reviewer gets
- **Prerequisites:** Docker Desktop and an OpenAI key (or Python 3.11+ and Node LTS without Docker).
- **Quick start:** `git clone` → `cp .env.example .env` (PowerShell variant included) → set `LLM_API_KEY`,
  `LLM_MODEL=gpt-6-luna`, `LLM_REASONING_EFFORT=low` → `docker compose up --build` → http://localhost:5173.
- **Environment variable table:** every key in `.env.example`, whether it's required, its default and purpose.
- **Seed data:** automatic on startup, the manual command (Docker and non-Docker forms), and how to reset (delete the DB file).
- **Running without Docker:** venv, `pip install`, `uvicorn`, `npm install`, `npm run dev`, plus how to point the proxy at another port.
- **Using the app, the API table with error codes, how scoring works** (short, linking to BUILD_LOG),
  project layout, and the two check scripts.

## BUILD_LOG.md: what was completed in this step
- **Working with AI → tools and split:** Claude Code built it step by step; I made the decisions (stack,
  gate policy, model choice after verification, working rhythm) and reviewed each step.
- **Got wrong → temperature:** now credited correctly. I questioned `temperature=0` because reasoning
  models use reasoning effort; testing confirmed the 400.
- Fixed a mis-indented bullet and the stale "medium" effort value (`low` is what's used).
- **Weakest part:** one clear pick. The verdict quality rests on `backend/prompts/evaluator_system.md`,
  and code can only verify that a quote exists, not that the judgement is right. Variation between runs,
  judgement-call weights and textual dedupe are listed as related weaknesses.
- **Next 48 hours:** turn the 9-run matrix into a labelled evaluation set with repeat runs, so prompt
  and model changes are measured rather than eyeballed.
- **Write yourself:** left as a clearly marked **TODO for you**. It must be your own answer (suggestion:
  do a scoring drill by hand and describe it).

## Clean-clone test: what was actually run
Cloned `HEAD` into a temporary folder, then followed the README word for word, as a separate Compose
project on ports 8002/5174 so it didn't touch the running app:

| Check | Result |
|---|---|
| Clone contains no `.env`, DB, `node_modules` or venv | ✓ none |
| `cp .env.example .env` + set key / model / effort | ✓ |
| `docker compose up --build` | ✓ backend healthy → frontend started |
| Page at the frontend port | ✓ "AstroBase: Vendor Scoring" |
| RFQs through the frontend proxy | ✓ RFQ-001, RFQ-002, RFQ-003 |
| Fresh DB created in the clone's `data_warehouse/` | ✓ |
| One evaluation (vendor A × RFQ-001) through the UI path | ✓ score 30, raw 81, gate ✗, 3 reasons, 2 gaps |
| README's manual seed command (`docker compose exec backend python -m backend.seed`) | ✓ "Seeded 0 RFQs (3 already present)" |
| History | ✓ 1 row |
| Non-Docker: `python -m backend.seed` + `uvicorn` + `npm install` + `vite` | ✓ after ordering fix (see below) |

**What came up:** the first non-Docker attempt showed Vite `http proxy error … ECONNREFUSED`. Two causes
were investigated: (1) Node resolves `localhost` to IPv6 `::1`, but uvicorn listens on IPv4 only;
(2) my test script queried Vite before uvicorn had finished starting. On a controlled retest, both
`localhost` and `127.0.0.1` targets worked once uvicorn was up, so (2) was the main cause. The default
proxy target was still changed to `http://127.0.0.1:8000` (and the README examples updated) so (1) can
never happen on a reviewer's machine. The non-Docker test reused the existing venv's packages rather
than a fresh `pip install` (the Docker test did a full fresh install inside the image).

Afterwards the test containers and images were removed and the temporary clone deleted.

## Check questions
1. What must a reviewer do before `docker compose up --build` works, and what happens if they skip it?
2. How does a reviewer load the seed data?
3. Why did we test from a fresh clone instead of just running the app we already had?

### Answers
1. Create `.env` from `.env.example` and set `LLM_API_KEY` and `LLM_MODEL`. If `.env` doesn't exist,
   Compose refuses to start (`env_file: .env` is required). If the key is empty, the app starts and
   loads RFQs, but Evaluate returns a clear **503** "LLM_API_KEY is empty; set it in .env".
2. They don't need to do anything: the API seeds on startup. The documented manual command is
   `docker compose exec backend python -m backend.seed` (or `python -m backend.seed` without Docker).
3. Our working folder has things a reviewer won't: a filled `.env`, an existing DB, `node_modules`, a venv,
   cached Docker layers. A fresh clone only has what's committed, so it's the only honest test of "the
   README works on a clean clone". It also confirmed that no secrets or runtime files are in git.
