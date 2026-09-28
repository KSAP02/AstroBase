# Step 2b: Scoring walkthrough (one real example, end to end)

Companion to [`step-2-scoring.md`](step-2-scoring.md). This file follows **one real example, vendor A
against RFQ-001**, through every function in `backend/agents/scoring.py`, shows how
`experiments/scoring_sanity.py` is set up, and explains what changes once an LLM produces the verdicts.

---

## Part 1: How `scoring.py` works

### The three inputs to `compute_score(criteria, verdicts, vendor_text)`

**`criteria`**: the RFQ broken into labelled lines. Each is a `Criterion(id, tier, text)`:
```
M1 mandatory  AS9100D certification
T1 technical  Tolerance +/-0.02 mm on critical features
T2 technical  Surface finish Ra 1.6
T3 technical  5-axis machining capability
T4 technical  Quantity: 250 units
T5 technical  Delivery: 6 weeks from PO
R1 required   CMM inspection with first-article inspection report per AS9102
R2 required   Material traceability to mill test certificate
P1 preferred  In-house CMM
P2 preferred  Prior aerospace structural work
P3 preferred  NADCAP-accredited subcontractors for any outsourced process steps
```

**`verdicts`**: one judgement per line. Each is a `CriterionVerdict(criterion_id, verdict, evidence, rationale)`:
```
M1 not_met        "ISO 9001:2015 certified (TUV SUD, valid to March 2028)."
T1 met            "Routine working tolerance +/-0.01 mm on 5-axis work"
T2 met            "surface finishes to Ra 0.8 achieved in production on aluminium alloys"
T3 met            "three DMG MORI 5-axis machines"
T4 met            "Typical lead time for batch quantities of 200-300 machined components"
T5 partial        "four to five weeks from receipt of material"
R1 met            "First-article inspection reports issued in AS9102 format on request"
R2 met            "Material traceability maintained against mill test certificates for all incoming stock."
P1 met            "two Zeiss CONTURA CMMs"
P2 not_evidenced  ""
P3 not_applicable ""
```

**`vendor_text`**: the full text of `vendor-a.txt`.

### Stage 1: `apply_verdicts()` decides which verdicts to trust

```python
by_id = {v.criterion_id: v for v in verdicts}
```
This builds a lookup table, `{"M1": <verdict>, "T1": <verdict>, ...}`, so each criterion can find its verdict by id.

```python
vendor_norm = normalise(vendor_text)
```
The whole vendor file is normalised **once**: lowercased, `±` turned into `+/-`, quote marks removed, and
every run of spaces or line breaks collapsed into a single space. In the file, "Routine" and
"working tolerance" are on separate lines. After normalising they read
`routine working tolerance +/-0.01 mm on 5-axis work`, one continuous string.

Then the function loops over **our** criteria, not the verdict list, and checks each one in turn:

| Check | Rule | Vendor A |
|---|---|---|
| 1. Is there a verdict for this id? | If not → `not_evidenced`, `downgraded=True` | All 11 present |
| 2. Is it `met` or `partial`? If so, is the quote really in the text? | `quote_found(evidence, vendor_norm)`; if False → `not_evidenced`, `downgraded=True` | T1: normalised quote `routine working tolerance +/-0.01 mm on 5-axis work` **is** inside `vendor_norm` → kept. Same for T2–T5, R1, R2, P1 |
| 3. Mandatory marked `not_applicable`? | Force to `not_met` | M1 is `not_met`, so no change |

Verdicts of `not_met`, `not_evidenced` and `not_applicable` skip the quote check. They don't claim the
vendor has anything, so there's nothing to prove.

**Output:** a list of `ScoredCriterion`. Each one is the RFQ line plus its final verdict and a
`downgraded` flag. For vendor A nothing was downgraded.

`quote_found` in more detail:
```python
fragments = [normalise(f) for f in re.split(r"\.\.\.|…", evidence)]
```
The quote is split on `...` in case the model joined two separate pieces. Each piece is normalised the
same way as the vendor text, then:
```python
return bool(fragments) and all(f in vendor_norm for f in fragments)
```
It returns True only if there's at least one piece and **every** piece appears in the vendor text.
`in` is Python's substring test.

### Stage 2: `score_tiers()` turns verdicts into points per tier

Points per verdict: `met = 1.0`, `partial = 0.5`, `not_met = 0`, `not_evidenced = 0`. `not_applicable`
is **left out**.

**Step 1, the average per tier, ignoring `not_applicable`:**

| Tier | Verdicts counted | Average |
|---|---|---|
| technical | T1 1, T2 1, T3 1, T4 1, T5 0.5 | 4.5 / 5 = **0.9** |
| required | R1 1, R2 1 | 2 / 2 = **1.0** |
| preferred | P1 1, P2 0 (P3 skipped) | 1 / 2 = **0.5** |

Mandatory isn't in `TIER_WEIGHTS`, so it's never averaged. It's only used for the gate.

**Step 2, how much each tier is worth:**
```python
active_weight = sum(weights of tiers that have at least one counted line)   # 40+35+25 = 100
tier_max = 100 * weight / active_weight                                     # 40, 35, 25
```
All three tiers have counted lines, so each tier is worth its normal weight. If every preferred line
had been `not_applicable`, `active_weight` would be 75, making technical worth 53.3 and required 46.7.
The total stays out of 100 (sanity case 4).

**Step 3, points = worth × average:**

| Tier | Calculation | Points |
|---|---|---|
| technical | 40 × 0.9 | **36.0 / 40** |
| required | 35 × 1.0 | **35.0 / 35** |
| preferred | 25 × 0.5 | **12.5 / 25** |

### Stage 3: back in `compute_score()`, sum and gate

```python
raw_score = round(36.0 + 35.0 + 12.5)        # round(83.5) → 84
gate_passed = all(c.verdict == "met" for c in scored if c.tier == "mandatory")   # M1 is not_met → False
score = raw_score if gate_passed else min(raw_score, GATE_CAP)                   # min(84, 30) → 30
```
It returns `ScoreResult(score=30, raw_score=84, gate_passed=False, breakdown={...}, criteria=[...])`.

The result shows **why** vendor A got 30: it would have earned 84, but it lacks AS9100D.

---

## Part 2: How `scoring_sanity.py` uses it

It's a plain script, not a test framework. It does four things.

**1. Makes `backend` importable.**
```python
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
```
Run as `python experiments/scoring_sanity.py`, Python only looks for imports in `experiments/`. Adding
the repo root lets `from backend.agents.scoring import compute_score` work.

**2. Provides stand-ins for what Step 3 will automate.**
- `RFQ_001 = [Criterion(...), ...]` is the criteria list typed by hand. In Step 3 `build_criteria()`
  makes it from the database.
- `v(cid, verdict, evidence)` is a shortcut for building one `CriterionVerdict` (the rationale is just a
  placeholder). These stand in for the LLM's output.
- `vendor("a")` reads `data_warehouse/samples/vendor-a.txt`.

**3. Runs each case and asserts the expected result.**
```python
check(label, compute_score(criteria, verdicts, text), expected_score=30, expected_gate=False)
```
`check()` prints PASS or FAIL, the per-tier breakdown and any downgraded ids, then uses `assert`. On the
first wrong result the script stops with an error.

**4. Has two kinds of cases:**
- **Synthetic (1–6):** a 4-line mini RFQ and a one-paragraph vendor text we wrote ourselves. Each case
  isolates **one rule**: everything met, the gate, an invented quote, redistribution, a skipped line,
  and a mandatory line marked not-applicable. When one fails, you know which rule broke.
- **Real (A, B, A′):** the full RFQ-001 and the real vendor files, with quotes copied exactly. These
  prove the quote check copes with real formatting, such as line breaks and `+/-`. A′ is vendor A with
  one paraphrased quote, the same mistake the model made in the Step 0 smoke test. It gets downgraded
  and the raw score drops from 84 to 76.

It's set up this way so we can check the rules before paying for any LLM calls. Because the verdicts
were written by hand, the correct score is known in advance, and any difference is a bug in `scoring.py`.

**Try your own example** (save as a file in `experiments/`, run from the repo root with the venv's Python):
```python
import sys; sys.path.insert(0, ".")
from backend.agents.scoring import compute_score
from backend.schemas import Criterion, CriterionVerdict as V

criteria = [Criterion(id="M1", tier="mandatory", text="AS9100D"),
            Criterion(id="T1", tier="technical", text="5-axis")]
text = "We are AS9100D certified. We have no 5-axis machines."
r = compute_score(criteria, [V(criterion_id="M1", verdict="met", evidence="AS9100D certified", rationale=""),
                             V(criterion_id="T1", verdict="not_met", evidence="", rationale="")], text)
print(r.score, r.gate_passed, r.breakdown)
```
Change `"AS9100D certified"` to `"AS9100 certified"`: the quote check downgrades M1 and the gate fails.

---

## Part 3: What changes once the LLM is involved (Step 3)

**`compute_score()` doesn't change at all.** It gets the same three inputs; only their source changes:

| Input | Now | Step 3 |
|---|---|---|
| `criteria` | typed by hand | `build_criteria(rfq)` from the database |
| `verdicts` | typed by hand, carefully | `gpt-6-luna`'s answer, as a validated `LLMEvaluation` |
| `vendor_text` | sample file | whatever the user pastes or uploads |

### Problems the code already catches
- **Paraphrased or invented quotes:** downgraded by `quote_found`. We already saw Luna paraphrase.
- **Skipped lines:** `by_id.get()` returns `None`, so the line counts as `not_evidenced`.
- **Made-up ids** such as `"X9"`: never looked up, because we loop over our own criteria.
- **Made-up verdicts** such as `"mostly_met"`: impossible, since the schema allows only the 5 values and
  structured output enforces it.
- **Dodging the gate** by marking AS9100D `not_applicable`: forced to `not_met`.

### Problems the code can't catch (the prompt and our review handle these)
- **Wrong judgement with a real quote.** For example, it quotes "Surface finish typically Ra 3.2" and
  says `met`. The quote is genuine, so the check passes, but the verdict is wrong. The prompt rule
  "lower Ra is better" handles this, plus reading the verdicts in the 9-run table.
- **Vague claims counted as met.** Vendor C's "Space-grade heritage." really is in the text. The prompt
  rule "`met` needs a specific fact" handles this.
- **Near-miss certificates:** IATF 16949 treated as AS9100D. The prompt rule "exact certificate only"
  handles this.

### Other differences
- **Answers vary a little between runs.** GPT-6 doesn't accept temperature 0, so running the same
  vendor twice might change one line from `met` to `partial`. Because the score is built from separate
  lines, that moves it by a few points, never 40. That's one reason we don't ask the LLM for the number directly.
- **Extra outputs:** the LLM also writes the 3 reasons and 2 gaps. These don't affect the score; they're
  shown to the user, and Step 3 makes sure there are exactly 3 and 2.
- **Cost and failure:** about $0.001 and a few seconds per call. The call can fail (network, bad key),
  which becomes a clear 502 or 503 with no hidden retries. Hand-made verdicts are free, instant and
  can't fail.

### In one sentence
`scoring.py` doesn't trust verdicts blindly, whoever writes them. With hand-made verdicts we test the
rules; with LLM verdicts, the rules protect the score from the model's mistakes as far as code can,
and the prompt and a human reading the verdicts handle the rest.
