"""Risk aggregation, recommendation, and explanation.

Owner: Risk developer.
Produces: ``Risk`` (§6, per-document *and* per-bundle), ``Recommendation`` (§7),
``Explanation`` (§8).

This module only *combines* signals that other modules produced. It never
generates a raw signal of its own.

FOUNDATION STATUS: the plumbing is complete and contract-valid, but the actual
weighting model in ``score_document`` / ``score_bundle`` is a deliberate
placeholder (returns 0.0 / "low"). See the TODO in ``_aggregate`` — that
function is the one meaningful design decision in this module and is left for
the Risk developer to implement.
"""

from __future__ import annotations

from modules.contract import (
    Consistency,
    DEFAULT_DECISION_FOR_SEVERITY,
    Explanation,
    Forensics,
    Metadata,
    Recommendation,
    RecommendationBasis,
    Risk,
    RiskContribution,
    RiskModelInfo,
    Severity,
    severity_for_score,
)

ENGINE = "stub-risk"
ENGINE_VERSION = "0.0.0"
MODEL = RiskModelInfo(method="placeholder", version="0.0.0")


# --------------------------------------------------------------------------- #
# The one real decision in this module.                                       #
# --------------------------------------------------------------------------- #
def _aggregate(signals: list[RiskContribution]) -> float:
    """Combine per-signal contributions into a single 0–100 risk score.

    TODO(risk-dev): implement the aggregation model. This is a genuine design
    choice with real trade-offs — pick one and document why in the PR:

      * weighted sum     — simple, explainable; weights must be tuned so a
                           single strong signal can still dominate.
      * noisy-or         — P(fraud) = 1 - Π(1 - pᵢ·wᵢ); good when any one
                           strong signal should push the score up on its own.
      * max + dampened   — take the worst signal, add a fraction of the rest.
      * small rule set    — e.g. "any forensics signal ≥ 80 ⇒ score ≥ 75".

    Constraints:
      * result MUST be clamped to [0, 100];
      * `contribution` on each RiskContribution should reflect this function
        (so the explanation stays traceable);
      * be deterministic — the demo re-runs the same bundle repeatedly.

    The stub returns 0.0 so the pipeline is exercised end to end.
    """
    return 0.0


# --------------------------------------------------------------------------- #
# Per-document risk (contract §6, scope="document")                           #
# --------------------------------------------------------------------------- #
def score_document(
    document_id: str,
    forensics: Forensics,
    metadata: Metadata,
) -> Risk:
    """Score one document from its own forensics + metadata signals."""
    contributions: list[RiskContribution] = []  # TODO(risk-dev): build from signals
    score = _aggregate(contributions)
    return Risk(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        scope="document",
        subject_id=document_id,
        score=score,
        severity=severity_for_score(score),
        contributions=contributions,
        model=MODEL,
    )


# --------------------------------------------------------------------------- #
# Bundle risk (contract §6, scope="bundle")                                   #
# --------------------------------------------------------------------------- #
def score_bundle(
    bundle_id: str,
    document_risks: list[Risk],
    consistency: Consistency,
) -> Risk:
    """Roll per-document risk + bundle-wide consistency into one score."""
    contributions: list[RiskContribution] = []  # TODO(risk-dev): build from inputs
    score = _aggregate(contributions)
    return Risk(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        scope="bundle",
        subject_id=bundle_id,
        score=score,
        severity=severity_for_score(score),
        contributions=contributions,
        model=MODEL,
    )


# --------------------------------------------------------------------------- #
# Recommendation (contract §7)                                                #
# --------------------------------------------------------------------------- #
def recommend(bundle_risk: Risk) -> Recommendation:
    """Turn the bundle risk score into a reviewer-facing recommendation."""
    severity: Severity = bundle_risk["severity"]
    decision = DEFAULT_DECISION_FOR_SEVERITY[severity]
    headline = {
        "accept": "Looks clean — safe to accept",
        "review": "Manual review recommended",
        "reject": "High fraud risk — recommend reject",
    }[decision]
    return Recommendation(
        decision=decision,
        confidence=0.0,
        headline=headline,
        reasons=["Foundation stub: no signals evaluated yet."],
        suggested_actions=[],
        based_on=RecommendationBasis(
            bundle_risk_score=bundle_risk["score"],
            severity=severity,
        ),
    )


# --------------------------------------------------------------------------- #
# Explanation (contract §8)                                                   #
# --------------------------------------------------------------------------- #
def explain(
    bundle_risk: Risk,
    document_risks: list[Risk],
    consistency: Consistency,
) -> Explanation:
    """Assemble the human-facing narrative. Presentation data only."""
    return Explanation(
        summary=(
            "Foundation stub: the pipeline ran end to end but no detection "
            "logic is implemented yet, so there is nothing to explain."
        ),
        factors=[],
        glossary=[
            {
                "term": "ELA",
                "definition": (
                    "Error-level analysis: highlights areas of an image that "
                    "were re-saved at a different JPEG quality, a common sign "
                    "of local editing."
                ),
            },
        ],
    )
