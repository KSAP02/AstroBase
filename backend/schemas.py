"""Data shapes shared across the backend (Pydantic models).

- Criterion / ScoredCriterion / ScoreResult: what scoring.py works with and returns.
- CriterionVerdict / Finding / LLMEvaluation: the exact JSON the LLM must return.
  Field descriptions are sent to the model as part of the JSON schema, so they are written for it.
- EvaluationRequest / EvaluationOut: the body and response of POST /api/evaluations.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Tier = Literal["mandatory", "technical", "required", "preferred"]
Verdict = Literal["met", "partial", "not_met", "not_evidenced", "not_applicable"]


# ---- One RFQ line, and what scoring makes of it -------------------------------------------

class Criterion(BaseModel):
    """One line of an RFQ, e.g. {id: "T1", tier: "technical", text: "Tolerance +/-0.02 mm"}."""
    id: str
    tier: Tier
    text: str


class ScoredCriterion(Criterion):
    """A criterion plus its final verdict, after scoring.py's checks."""
    verdict: Verdict
    evidence: str
    rationale: str
    downgraded: bool = False  # True if code overrode the model's verdict


class TierScore(BaseModel):
    points: float  # points earned in this tier
    max: float     # points this tier was worth (after redistribution)


class ScoreResult(BaseModel):
    score: int         # final score shown to the user (capped if the gate failed)
    raw_score: int     # score before the mandatory gate
    gate_passed: bool  # every mandatory criterion was met
    breakdown: dict[str, TierScore]
    criteria: list[ScoredCriterion]


# ---- What the LLM must return --------------------------------------------------------------

class CriterionVerdict(BaseModel):
    criterion_id: str = Field(description="The criterion id exactly as given, e.g. 'T1'.")
    verdict: Verdict
    evidence: str = Field(
        description="The exact sentence or phrase copied character-for-character from the vendor "
        "profile that supports the verdict. Empty string if there is none."
    )
    rationale: str = Field(description="One short sentence explaining the verdict.")


class Finding(BaseModel):
    criterion_id: str = Field(description="The criterion id this point is about, e.g. 'M1'.")
    text: str = Field(description="One sentence for a procurement reader.")


class LLMEvaluation(BaseModel):
    vendor_name: str = Field(description="Company name from the profile, or 'Unknown vendor'.")
    criteria: list[CriterionVerdict] = Field(description="One entry per criterion id, in order.")
    reasons: list[Finding] = Field(description="Exactly 3 supporting reasons for the score.")
    gaps: list[Finding] = Field(description="Exactly 2 most important gaps or risks.")


# ---- API: POST /api/evaluations ------------------------------------------------------------

class EvaluationRequest(BaseModel):
    rfq_id: str
    # Whitespace is stripped first, so "   " counts as empty. FastAPI returns 422 if these fail.
    vendor_text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000)]


class EvaluationOut(BaseModel):
    rfq_id: str
    vendor_name: str
    score: int
    raw_score: int
    gate_passed: bool
    breakdown: dict[str, TierScore]
    criteria: list[ScoredCriterion]
    reasons: list[Finding]  # always exactly 3
    gaps: list[Finding]     # always exactly 2
    model: str
    prompt_version: str
