"""Sanity checks for backend/agents/scoring.py using hand-made verdicts (no LLM, no cost).

Run from the repo root:  python experiments/scoring_sanity.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so "backend" is importable when run as a script

from backend.agents.scoring import compute_score  # noqa: E402
from backend.schemas import Criterion, CriterionVerdict  # noqa: E402

# RFQ-001 as criteria (Step 3 builds this list automatically from rfqs.json).
RFQ_001 = [
    Criterion(id="M1", tier="mandatory", text="AS9100D certification"),
    Criterion(id="T1", tier="technical", text="Tolerance +/-0.02 mm on critical features"),
    Criterion(id="T2", tier="technical", text="Surface finish Ra 1.6"),
    Criterion(id="T3", tier="technical", text="5-axis machining capability"),
    Criterion(id="T4", tier="technical", text="Quantity: 250 units"),
    Criterion(id="T5", tier="technical", text="Delivery: 6 weeks from PO"),
    Criterion(id="R1", tier="required", text="CMM inspection with first-article inspection report per AS9102"),
    Criterion(id="R2", tier="required", text="Material traceability to mill test certificate"),
    Criterion(id="P1", tier="preferred", text="In-house CMM"),
    Criterion(id="P2", tier="preferred", text="Prior aerospace structural work"),
    Criterion(id="P3", tier="preferred", text="NADCAP-accredited subcontractors for any outsourced process steps"),
]


def v(cid: str, verdict: str, evidence: str = "") -> CriterionVerdict:
    return CriterionVerdict(criterion_id=cid, verdict=verdict, evidence=evidence, rationale="(hand-made)")


def vendor(name: str) -> str:
    return (ROOT / "data_warehouse" / "samples" / f"vendor-{name}.txt").read_text(encoding="utf-8")


def check(label: str, result, expected_score: int, expected_gate: bool) -> None:
    ok = result.score == expected_score and result.gate_passed == expected_gate
    tiers = ", ".join(f"{t} {s.points}/{s.max}" for t, s in result.breakdown.items())
    downgraded = [c.id for c in result.criteria if c.downgraded]
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    print(f"       score={result.score} raw={result.raw_score} gate_passed={result.gate_passed} | {tiers}"
          + (f" | downgraded={downgraded}" if downgraded else ""))
    assert ok, f"expected score={expected_score}, gate_passed={expected_gate}"


# ---- Synthetic cases: a tiny RFQ and vendor text we fully control ----------------------------
MINI = [
    Criterion(id="M1", tier="mandatory", text="ISO 9001"),
    Criterion(id="T1", tier="technical", text="5-axis"),
    Criterion(id="R1", tier="required", text="CMM"),
    Criterion(id="P1", tier="preferred", text="Aerospace work"),
]
MINI_TEXT = "We are ISO 9001 certified. We run 5-axis machines. We own a CMM. We supply aerospace primes."

check("1. Everything met -> 100",
      compute_score(MINI, [v("M1", "met", "ISO 9001 certified"), v("T1", "met", "We run 5-axis machines"),
                           v("R1", "met", "We own a CMM"), v("P1", "met", "We supply aerospace primes")], MINI_TEXT),
      expected_score=100, expected_gate=True)

check("2. Mandatory not met, everything else met -> capped at 30",
      compute_score(MINI, [v("M1", "not_met"), v("T1", "met", "We run 5-axis machines"),
                           v("R1", "met", "We own a CMM"), v("P1", "met", "We supply aerospace primes")], MINI_TEXT),
      expected_score=30, expected_gate=False)

check("3. Invented quote on T1 -> downgraded to not_evidenced, loses the 40 technical points",
      compute_score(MINI, [v("M1", "met", "ISO 9001 certified"), v("T1", "met", "We run 9-axis machines"),
                           v("R1", "met", "We own a CMM"), v("P1", "met", "We supply aerospace primes")], MINI_TEXT),
      expected_score=60, expected_gate=True)

check("4. Preferred tier all not_applicable -> its 25 points shared out (tech 53.3 + required 46.7)",
      compute_score(MINI, [v("M1", "met", "ISO 9001 certified"), v("T1", "met", "We run 5-axis machines"),
                           v("R1", "not_met"), v("P1", "not_applicable")], MINI_TEXT),
      expected_score=53, expected_gate=True)

check("5. Model skipped R1 and P1 -> both treated as not_evidenced",
      compute_score(MINI, [v("M1", "met", "ISO 9001 certified"), v("T1", "met", "We run 5-axis machines")], MINI_TEXT),
      expected_score=40, expected_gate=True)

check("6. Mandatory marked not_applicable -> forced to not_met, gate fails",
      compute_score(MINI, [v("M1", "not_applicable"), v("T1", "met", "We run 5-axis machines"),
                           v("R1", "met", "We own a CMM"), v("P1", "met", "We supply aerospace primes")], MINI_TEXT),
      expected_score=30, expected_gate=False)

# ---- Real vendor text, verdicts as a careful human would give them ---------------------------
print()
vendor_a = [
    v("M1", "not_met", "ISO 9001:2015 certified (TUV SUD, valid to March 2028)."),
    v("T1", "met", "Routine working tolerance +/-0.01 mm on 5-axis work"),
    v("T2", "met", "surface finishes to Ra 0.8 achieved in production on aluminium alloys"),
    v("T3", "met", "three DMG MORI 5-axis machines"),
    v("T4", "met", "Typical lead time for batch quantities of 200-300 machined components"),
    v("T5", "partial", "four to five weeks from receipt of material"),
    v("R1", "met", "First-article inspection reports issued in AS9102 format on request"),
    v("R2", "met", "Material traceability maintained against mill test certificates for all incoming stock."),
    v("P1", "met", "two Zeiss CONTURA CMMs"),
    v("P2", "not_evidenced"),
    v("P3", "not_applicable"),
]
check("Vendor A x RFQ-001: strong machinist, no AS9100D -> raw 84, capped to 30",
      compute_score(RFQ_001, vendor_a, vendor("a")), expected_score=30, expected_gate=False)

vendor_b = [
    v("M1", "met", "AS9100D certified (valid to August 2027)."),
    v("T1", "not_met", "Demonstrated working tolerance +/-0.05 mm."),
    v("T2", "not_met", "Surface finish typically Ra 3.2 as machined"),
    v("T3", "not_met", "No 5-axis capability"),
    v("T4", "not_met", "Largest single order to date: 120 pieces."),
    v("T5", "not_met", "Typical lead time for batches above 100 pieces is 9 to 11 weeks."),
    v("R1", "partial", "AS9102 first-article reports prepared in-house using outsourced measurement data"),
    v("R2", "met", "Full material traceability to mill test certificate"),
    v("P1", "not_met", "No in-house CMM."),
    v("P2", "partial", "Machining of aluminium and mild steel components for aerospace ground support equipment"),
    v("P3", "not_evidenced"),
]
check("Vendor B x RFQ-001: has AS9100D, fails every technical line -> 30, gate passed",
      compute_score(RFQ_001, vendor_b, vendor("b")), expected_score=30, expected_gate=True)

vendor_a_paraphrased = list(vendor_a)
vendor_a_paraphrased[2] = v("T2", "met", "Ra 0.8 is finer than the required Ra 1.6")  # the model's own words
check("Vendor A with a paraphrased T2 quote -> T2 downgraded, raw drops 84 -> 76 (still capped 30)",
      compute_score(RFQ_001, vendor_a_paraphrased, vendor("a")), expected_score=30, expected_gate=False)

print("\nAll scoring checks passed.")
