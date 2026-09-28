"""Turn per-requirement verdicts into a score out of 100.

Pure functions: no database, no LLM, no I/O. The same inputs always give the same score.
The LLM judges each RFQ line; this file does the maths and enforces the rules.
"""

import re

from backend.schemas import Criterion, CriterionVerdict, ScoredCriterion, ScoreResult, TierScore

# How much each tier is worth (sums to 100). Mandatory has no weight: it's a pass/fail gate.
TIER_WEIGHTS = {"technical": 40, "required": 35, "preferred": 25}

# Points per verdict. not_applicable is absent on purpose: those lines are left out of the average.
VERDICT_POINTS = {"met": 1.0, "partial": 0.5, "not_met": 0.0, "not_evidenced": 0.0}

# If any mandatory criterion isn't met, the score can't go above this.
GATE_CAP = 30

# Verdicts that claim the vendor has something, so they must be backed by a real quote.
NEEDS_EVIDENCE = {"met", "partial"}


def compute_score(
    criteria: list[Criterion], verdicts: list[CriterionVerdict], vendor_text: str
) -> ScoreResult:
    """The whole scoring pipeline: check verdicts -> score each tier -> sum -> apply the gate."""
    scored = apply_verdicts(criteria, verdicts, vendor_text)
    breakdown = score_tiers(scored)
    raw_score = round(sum(t.points for t in breakdown.values()))

    gate_passed = all(c.verdict == "met" for c in scored if c.tier == "mandatory")
    score = raw_score if gate_passed else min(raw_score, GATE_CAP)

    return ScoreResult(
        score=score,
        raw_score=raw_score,
        gate_passed=gate_passed,
        breakdown=breakdown,
        criteria=scored,
    )


def apply_verdicts(
    criteria: list[Criterion], verdicts: list[CriterionVerdict], vendor_text: str
) -> list[ScoredCriterion]:
    """Pair each RFQ criterion with the model's verdict, and correct verdicts we can't trust."""
    by_id = {v.criterion_id: v for v in verdicts}  # ids the model made up are never looked up
    vendor_norm = normalise(vendor_text)
    scored = []

    for c in criteria:
        v = by_id.get(c.id)
        if v is None:
            # The model skipped this line: treat it as "no evidence", not as a pass.
            scored.append(ScoredCriterion(
                **c.model_dump(), verdict="not_evidenced", evidence="",
                rationale="No verdict returned by the model.", downgraded=True,
            ))
            continue

        verdict, downgraded = v.verdict, False

        # Anti-hallucination: a positive verdict must quote text that really is in the profile.
        if verdict in NEEDS_EVIDENCE and not quote_found(v.evidence, vendor_norm):
            verdict, downgraded = "not_evidenced", True

        # A mandatory requirement always applies; "not applicable" would dodge the gate.
        if c.tier == "mandatory" and verdict == "not_applicable":
            verdict, downgraded = "not_met", True

        scored.append(ScoredCriterion(
            **c.model_dump(), verdict=verdict, evidence=v.evidence,
            rationale=v.rationale, downgraded=downgraded,
        ))
    return scored


def score_tiers(scored: list[ScoredCriterion]) -> dict[str, TierScore]:
    """Points per tier = tier weight x average verdict points over the lines that apply.

    If every line in a tier is not_applicable, that tier drops out and its weight is shared
    proportionally by the remaining tiers, so the total is still out of 100.
    """
    averages = {}
    for tier in TIER_WEIGHTS:
        points = [VERDICT_POINTS[c.verdict] for c in scored
                  if c.tier == tier and c.verdict != "not_applicable"]
        if points:
            averages[tier] = sum(points) / len(points)

    active_weight = sum(TIER_WEIGHTS[t] for t in averages)
    breakdown = {}
    for tier, weight in TIER_WEIGHTS.items():
        if tier in averages:
            tier_max = 100 * weight / active_weight  # = weight itself when no tier dropped out
            breakdown[tier] = TierScore(points=round(tier_max * averages[tier], 1), max=round(tier_max, 1))
        else:
            breakdown[tier] = TierScore(points=0.0, max=0.0)
    return breakdown


def quote_found(evidence: str, vendor_norm: str) -> bool:
    """True if the (normalised) evidence appears in the (normalised) vendor text.

    Quotes joined with "..." are split, and every fragment must be present.
    """
    fragments = [normalise(f) for f in re.split(r"\.\.\.|…", evidence)]
    fragments = [f for f in fragments if f]
    return bool(fragments) and all(f in vendor_norm for f in fragments)


def normalise(text: str) -> str:
    """Make text comparable: lowercase, one symbol set, single spaces, no quote marks or edge punctuation."""
    text = text.lower()
    text = text.replace("±", "+/-").replace("–", "-").replace("—", "-")
    text = re.sub(r"[\"'“”‘’]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,;:")
