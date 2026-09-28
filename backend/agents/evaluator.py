"""Evaluate one vendor profile against one RFQ: build criteria -> ONE LLM call -> score in code."""

from langchain_core.prompts import ChatPromptTemplate

from backend.agents.scoring import compute_score, normalise
from backend.config import get_settings
from backend.model import get_chat_model
from backend.prompts import PROMPT_VERSION, load_prompt
from backend.schemas import Criterion, EvaluationOut, Finding, LLMEvaluation, ScoredCriterion

# Tier order matters: it's the priority used when two lines say the same thing.
TIER_PREFIX = {"mandatory": "M", "technical": "T", "required": "R", "preferred": "P"}

N_REASONS = 3
N_GAPS = 2


class LLMCallError(RuntimeError):
    """The LLM call failed or returned output we couldn't use."""


def evaluate_vendor(rfq: dict, vendor_text: str) -> tuple[EvaluationOut, dict]:
    """Returns (the evaluation for the API, the raw LLM output to keep for auditing)."""
    criteria = build_criteria(rfq)

    prompt = ChatPromptTemplate.from_messages([
        ("system", load_prompt("evaluator_system")),
        ("human", load_prompt("evaluator_user")),
    ])
    llm = get_chat_model().with_structured_output(
        LLMEvaluation, method="json_schema", strict=True, include_raw=True
    )
    chain = prompt | llm

    try:
        # ★ The one LLM call per evaluation. ★
        out = chain.invoke({
            "rfq_id": rfq["id"],
            "rfq_title": rfq["title"],
            "criteria_block": "\n".join(f"{c.id} [{c.tier}] {c.text}" for c in criteria),
            "vendor_text": vendor_text,
        })
    except Exception as e:  # network, auth, rate limit, timeout...
        raise LLMCallError(f"LLM call failed: {type(e).__name__}: {e}") from e

    parsed: LLMEvaluation | None = out["parsed"]
    if parsed is None:
        raise LLMCallError(f"LLM returned output that doesn't match the schema: {out['parsing_error']}")

    result = compute_score(criteria, parsed.criteria, vendor_text)
    raw = {"content": out["raw"].content, "usage": out["raw"].usage_metadata}

    evaluation = EvaluationOut(
        rfq_id=rfq["id"],
        vendor_name=parsed.vendor_name.strip() or "Unknown vendor",
        score=result.score,
        raw_score=result.raw_score,
        gate_passed=result.gate_passed,
        breakdown=result.breakdown,
        criteria=result.criteria,
        reasons=pick_reasons(parsed.reasons, result.criteria),
        gaps=pick_gaps(parsed.gaps, result.criteria),
        model=get_settings().llm_model,
        prompt_version=PROMPT_VERSION,
    )
    return evaluation, raw


def build_criteria(rfq: dict) -> list[Criterion]:
    """Flatten the RFQ JSON into labelled lines: M1.., T1.., R1.., P1..

    Quantity, material and delivery are judged as technical lines. A line whose text contains, or is
    contained in, a line already kept (from the same or a higher tier) is dropped as a duplicate,
    e.g. RFQ-002's preferred "Ability to handle parts up to 600 mm" vs technical "Parts up to 600 mm".
    """
    lines = {
        "mandatory": rfq.get("mandatory", []),
        "technical": [
            *rfq.get("technical", []),
            f"Material: {rfq['material']}",
            f"Quantity: {rfq['quantity']}",
            f"Delivery: {rfq['delivery']}",
        ],
        "required": rfq.get("required", []),
        "preferred": rfq.get("preferred", []),
    }

    criteria: list[Criterion] = []
    kept: list[str] = []  # normalised text of every line kept so far
    for tier, texts in lines.items():
        for text in texts:
            norm = normalise(text)
            if any(norm in k or k in norm for k in kept):
                continue
            kept.append(norm)
            number = sum(c.tier == tier for c in criteria) + 1
            criteria.append(Criterion(id=f"{TIER_PREFIX[tier]}{number}", tier=tier, text=text))
    return criteria


def pick_reasons(found: list[Finding], scored: list[ScoredCriterion]) -> list[Finding]:
    """Exactly 3 reasons that agree with the final verdicts."""
    by_id = {c.id: c for c in scored}
    # Drop reasons about unknown ids, or about lines whose verdict our code overrode.
    reasons = [f for f in found if f.criterion_id in by_id and not by_id[f.criterion_id].downgraded]
    reasons = reasons[:N_REASONS]

    # Too few? Fill from met/partial lines not already used.
    used = {f.criterion_id for f in reasons}
    for c in scored:
        if len(reasons) == N_REASONS:
            break
        if c.verdict in ("met", "partial") and c.id not in used:
            reasons.append(Finding(criterion_id=c.id, text=f"{c.text}: {c.rationale}"))
            used.add(c.id)
    while len(reasons) < N_REASONS:
        reasons.append(Finding(criterion_id="-", text="No further strengths are evidenced in the profile."))
    return reasons


def pick_gaps(found: list[Finding], scored: list[ScoredCriterion]) -> list[Finding]:
    """Exactly 2 gaps; a failed mandatory line is always the first gap."""
    by_id = {c.id: c for c in scored}
    gaps = [f for f in found if f.criterion_id in by_id]

    failed_mandatory = [c for c in scored if c.tier == "mandatory" and c.verdict != "met"]
    for c in reversed(failed_mandatory):  # reversed + insert(0) keeps their original order
        if c.id not in {f.criterion_id for f in gaps}:
            gaps.insert(0, Finding(criterion_id=c.id, text=f"Mandatory requirement not met: {c.text}."))
    gaps = gaps[:N_GAPS]

    # Too few? Fill from the weakest lines not already used.
    used = {f.criterion_id for f in gaps}
    for c in scored:
        if len(gaps) == N_GAPS:
            break
        if c.verdict in ("not_met", "not_evidenced") and c.id not in used:
            gaps.append(Finding(criterion_id=c.id, text=f"{c.text}: {c.rationale}"))
            used.add(c.id)
    while len(gaps) < N_GAPS:
        gaps.append(Finding(criterion_id="-", text="No further gaps identified against this RFQ."))
    return gaps
