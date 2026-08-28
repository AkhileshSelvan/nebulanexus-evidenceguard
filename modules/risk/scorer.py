"""Risk aggregation, recommendation, and explanation.

Owner: Risk developer.
Produces: ``Risk`` (§6, per-document *and* per-bundle), ``Recommendation`` (§7),
``Explanation`` (§8).

This module only *combines* signals that other modules produced. It never
generates a raw signal of its own, never calls an external service, and never
imports FastAPI or backend/frontend code.

WHAT THIS IS NOT
----------------
This is a **risk-triage** engine. It does not prove a document is genuine and it
does not prove a document is fraudulent. It ranks how much human attention a
bundle deserves, and shows its working. The score is an ordinal triage number,
not a calibrated probability of fraud.


The model: bounded log-additive noisy-OR
========================================

1. Normalise every admissible signal into an evidence probability::

       p = (signal_score / 100) x source_weight x confidence

2. Convert to "evidence mass" and combine in log space::

       u_i = -ln(1 - p_i)
       U   = sum(u_i)              # after dedupe + per-source ceiling
       S   = 100 * (1 - e^-U)      # the score

3. Attribute exactly. Because ``U`` is a plain sum, each signal's share is::

       contribution_i = S * (u_i / U)      =>   sum(contribution_i) == S

Why this model
--------------
* **Bounded by construction.** ``1 - e^-U < 1`` for every finite U, so the score
  can never reach 100 — no clamping needed, and no clamping means attribution is
  never silently destroyed.
* **Exactly traceable.** The contributions add up to the score. A reviewer can
  audit the arithmetic by hand.
* **Diminishing returns.** Twenty trivial signals cannot impersonate certainty
  the way a weighted sum lets them.
* **Missing evidence is neutral.** An absent signal contributes no term, so the
  product is unchanged. Absence never pushes the score up.
* **Deterministic.** Pure arithmetic over sorted inputs. Same input, same output.
* **Single signals cannot convict.** ``MAX`` source weight is 0.60, and with one
  term the score is exactly ``100 * p`` — so the strongest possible lone signal
  scores 60 ("high" -> review), never the 75+ needed to recommend rejection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Sequence

from modules.contract import (
    Consistency,
    DEFAULT_DECISION_FOR_SEVERITY,
    Explanation,
    ExplanationEvidence,
    ExplanationFactor,
    Extraction,
    Forensics,
    GlossaryEntry,
    Metadata,
    Recommendation,
    RecommendationBasis,
    Risk,
    RiskContribution,
    RiskModelInfo,
    Severity,
    severity_for_score,
)

ENGINE = "evidenceguard-risk"
ENGINE_VERSION = "1.0.0"
MODEL_METHOD = "bounded_log_noisy_or"
MODEL = RiskModelInfo(method=MODEL_METHOD, version=ENGINE_VERSION)

Source = Literal["ocr", "forensics", "metadata", "consistency"]


# --------------------------------------------------------------------------- #
# Tunable policy constants — every number the engine uses lives here.          #
# --------------------------------------------------------------------------- #

#: How much each class of evidence is trusted. All are < 1.0 on purpose: with a
#: single signal the score is exactly ``100 * signal_score/100 * weight * conf``,
#: so the largest weight is also the ceiling for any lone signal. 0.60 keeps that
#: ceiling inside the "high" band (50-74 -> review) and out of "critical" (75+
#: -> reject). This is the mechanism behind "no single signal proves fraud".
SOURCE_WEIGHTS: dict[Source, float] = {
    "consistency": 0.60,  # cross-document contradiction is the hardest to explain away
    "forensics": 0.55,  # pixel/file tampering evidence
    "metadata": 0.35,  # circumstantial: edit gaps have many innocent causes
    "ocr": 0.15,  # document *quality*, not fraud evidence — nudges only
}

#: Ceiling on the combined evidence probability a single source may reach, no
#: matter how many signals it fires. Prevents one noisy module from saturating
#: the score, and stops the same underlying defect (reported as several related
#: signals) from being counted many times over.
#:
#: POLICY: every ceiling is < 0.75, so **no single source can independently
#: produce a reject decision** — a saturated source lands in "high" (review) at
#: worst, and reaching "critical" requires corroboration from a second source.
#: This is the stricter sibling of the per-signal rule enforced by
#: ``SOURCE_WEIGHTS``: one signal cannot convict, and neither can one module.
SOURCE_PROBABILITY_CEILING: dict[Source, float] = {
    "consistency": 0.72,  # saturated -> 72 ("high" -> review), never critical
    "forensics": 0.70,  # saturated -> 70 ("high" -> review), never critical
    "metadata": 0.55,  # saturated -> 55 ("high" -> review), never critical
    "ocr": 0.30,  # saturated -> 30 ("medium" -> review), never critical
}

#: A module that reports concern but leaves ``confidence`` at 0.0 has not told us
#: how sure it is. Treating that as "no evidence" would silently discard real
#: findings; treating it as certainty would overstate them. We treat it as
#: moderate and say so in the explanation.
UNREPORTED_CONFIDENCE = 0.5

#: Per-document evidence is slightly discounted when rolled into the bundle: a
#: finding already reflected in that document's own score should not carry full
#: force a second time at bundle level.
DOCUMENT_MASS_DAMPING = 0.85

#: Recommendation confidence is never 1.0. A triage engine that claims certainty
#: is lying; this constant makes that refusal explicit.
MAX_RECOMMENDATION_CONFIDENCE = 0.95
MIN_RECOMMENDATION_CONFIDENCE = 0.05

#: Confidence assigned when nothing fired. "No signals" is genuinely ambiguous —
#: it can mean "clean" or "nobody looked" — so a clean bundle is reported with
#: moderate, not total, confidence.
CLEAN_BUNDLE_CONFIDENCE = 0.6

#: Below this OCR text confidence the extracted values are treated as shaky.
OCR_CONFIDENCE_FLOOR = 0.55

#: Thresholds for the qualitative weight label on an explanation factor.
FACTOR_MAJOR_POINTS = 20.0
FACTOR_MODERATE_POINTS = 8.0


#: Stable reason codes. These are the vocabulary the UI and the demo script can
#: rely on; the human sentence after the code may be reworded freely.
REASON_CODES = {
    "NO_SIGNALS": "No module reported a concern.",
    "FORENSIC_SIGNALS": "Image or file forensics raised concern.",
    "METADATA_SIGNALS": "File metadata looks implausible.",
    "CONSISTENCY_SIGNALS": "Documents disagree with each other.",
    "OCR_QUALITY": "Document text could not be read reliably.",
    "CORROBORATED": "Independent sources agree that something is wrong.",
    "SINGLE_SOURCE": "Concern rests on one source only.",
    "COVERAGE_GAP": "Some checks did not run, so this verdict is partial.",
    "NEAR_BOUNDARY": "Score sits close to a severity boundary.",
}


# --------------------------------------------------------------------------- #
# Internal evidence representation                                            #
# --------------------------------------------------------------------------- #


#: Bundle-level contributions tag each signal with the document that raised it,
#: as ``"<signal_id>@<document_id>"``, so a reviewer can tell the two apart when
#: several documents fire the same check. Producing modules are *not* forbidden
#: from using "@" inside their own ids, so the tag is always split from the
#: RIGHT — the last "@" is the one we appended. Splitting from the left would
#: silently truncate an id such as ``"checks@issuer_domain"``.
_DOCUMENT_TAG = "@"


def _tag_signal_id(signal_id: str, document_id: str | None) -> str:
    if document_id is None:
        return signal_id
    return f"{signal_id}{_DOCUMENT_TAG}{document_id}"


def _untag_signal_id(raw: str) -> tuple[str, str | None]:
    """Inverse of :func:`_tag_signal_id`. Returns ``(signal_id, document_id)``."""
    head, separator, tail = raw.rpartition(_DOCUMENT_TAG)
    if not separator:
        return raw, None
    return head, (tail or None)


@dataclass(frozen=True)
class _Evidence:
    """One admitted signal, normalised and ready to fuse."""

    source: Source
    signal_id: str
    signal_score: float  # [0,100] as reported by the producing module
    weight: float  # [0,1] source weight actually applied
    probability: float  # [0,1) p = score/100 * weight * confidence
    label: str  # human label from the producing module (never invented)
    detail: str  # human detail from the producing module (never invented)
    document_id: str | None
    confidence_reported: bool

    @property
    def mass(self) -> float:
        """Evidence mass in nats: ``-ln(1 - p)``."""
        return -math.log(max(1e-12, 1.0 - self.probability))


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(out) or math.isinf(out):
        return default
    return out


def _make_evidence(
    *,
    source: Source,
    signal_id: str,
    raw_score: Any,
    raw_confidence: Any,
    label: str,
    detail: str,
    document_id: str | None = None,
) -> _Evidence | None:
    """Normalise one raw signal. Returns ``None`` if it carries no concern."""
    score = _clamp(_as_float(raw_score), 0.0, 100.0)
    if score <= 0.0:
        return None  # clean or unmeasured — contributes nothing

    reported = _as_float(raw_confidence)
    confidence_reported = reported > 0.0
    confidence = _clamp(reported) if confidence_reported else UNREPORTED_CONFIDENCE

    weight = SOURCE_WEIGHTS[source]
    probability = _clamp((score / 100.0) * weight * confidence, 0.0, 0.999999)
    if probability <= 0.0:
        return None

    return _Evidence(
        source=source,
        signal_id=signal_id,
        signal_score=round(score, 4),
        weight=weight,
        probability=probability,
        label=label or signal_id,
        detail=detail or "",
        document_id=document_id,
        confidence_reported=confidence_reported,
    )


# --------------------------------------------------------------------------- #
# Section readers — defensive, so a partial/absent section is never a crash    #
# --------------------------------------------------------------------------- #


def _iter_mapping_list(section: Any, key: str) -> Iterable[Mapping[str, Any]]:
    if not isinstance(section, Mapping):
        return ()
    items = section.get(key)
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        return ()
    return [item for item in items if isinstance(item, Mapping)]


def _forensics_evidence(
    forensics: Forensics | None, document_id: str | None
) -> list[_Evidence]:
    out: list[_Evidence] = []
    for signal in _iter_mapping_list(forensics, "signals"):
        if signal.get("passed") is True:
            continue  # explicitly clean
        ev = _make_evidence(
            source="forensics",
            signal_id=str(signal.get("id") or "unnamed_forensic_signal"),
            raw_score=signal.get("score"),
            raw_confidence=signal.get("confidence"),
            label=str(signal.get("label") or ""),
            detail=str(signal.get("detail") or ""),
            document_id=document_id,
        )
        if ev is not None:
            out.append(ev)
    return out


def _metadata_evidence(
    metadata: Metadata | None, document_id: str | None
) -> list[_Evidence]:
    out: list[_Evidence] = []
    for signal in _iter_mapping_list(metadata, "signals"):
        if signal.get("passed") is True:
            continue
        ev = _make_evidence(
            source="metadata",
            signal_id=str(signal.get("id") or "unnamed_metadata_signal"),
            raw_score=signal.get("score"),
            raw_confidence=signal.get("confidence"),
            label=str(signal.get("label") or ""),
            detail=str(signal.get("detail") or ""),
            document_id=document_id,
        )
        if ev is not None:
            out.append(ev)
    return out


def _consistency_evidence(consistency: Consistency | None) -> list[_Evidence]:
    out: list[_Evidence] = []
    for check in _iter_mapping_list(consistency, "checks"):
        status = str(check.get("status") or "")
        if status in ("pass", "not_applicable"):
            continue  # agreement, or nothing to compare — not evidence of a problem
        ev = _make_evidence(
            source="consistency",
            signal_id=str(check.get("id") or "unnamed_consistency_check"),
            raw_score=check.get("score"),
            raw_confidence=check.get("confidence"),
            label=str(check.get("label") or ""),
            detail=str(check.get("detail") or ""),
            document_id=None,  # bundle-scoped by definition
        )
        if ev is not None:
            out.append(ev)
    return out


def _extraction_evidence(
    extraction: Extraction | None, document_id: str | None
) -> list[_Evidence]:
    """Derive *document-quality* signals from the OCR section.

    These are deliberately weak. Unreadable text is a reason to look again, not
    evidence of forgery. If the OCR engine never ran we emit nothing at all —
    missing evidence must never read as positive evidence of fraud.
    """
    if not isinstance(extraction, Mapping):
        return []

    engine = str(extraction.get("engine") or "")
    if not engine or engine.endswith("-unavailable") or engine.endswith("-error"):
        return []  # coverage gap, handled by recommendation confidence instead

    out: list[_Evidence] = []
    full_text = str(extraction.get("full_text") or "").strip()
    text_confidence = _clamp(_as_float(extraction.get("text_confidence")))

    if not full_text:
        ev = _make_evidence(
            source="ocr",
            signal_id="ocr_no_text_extracted",
            raw_score=40.0,
            raw_confidence=0.5,
            label="No readable text",
            detail="OCR ran but produced no readable text for this document.",
            document_id=document_id,
        )
        if ev is not None:
            out.append(ev)
    elif 0.0 < text_confidence < OCR_CONFIDENCE_FLOOR:
        shortfall = (OCR_CONFIDENCE_FLOOR - text_confidence) / OCR_CONFIDENCE_FLOOR
        ev = _make_evidence(
            source="ocr",
            signal_id="ocr_low_text_confidence",
            raw_score=round(shortfall * 100.0, 4),
            raw_confidence=0.6,
            label="Low OCR confidence",
            detail=(
                f"Mean OCR confidence was {text_confidence:.2f}, "
                f"below the {OCR_CONFIDENCE_FLOOR:.2f} reliability floor."
            ),
            document_id=document_id,
        )
        if ev is not None:
            out.append(ev)

    return out


# --------------------------------------------------------------------------- #
# Dedupe + per-source ceiling                                                 #
# --------------------------------------------------------------------------- #


def _dedupe(evidence: Sequence[_Evidence]) -> list[_Evidence]:
    """Collapse repeats of the same ``(source, signal_id, document_id)``.

    The same underlying finding reported twice is one piece of evidence, not two.
    The strongest report wins; ties resolve deterministically by signal id.
    """
    best: dict[tuple[str, str, str | None], _Evidence] = {}
    for ev in evidence:
        key = (ev.source, ev.signal_id, ev.document_id)
        current = best.get(key)
        if current is None or ev.probability > current.probability:
            best[key] = ev
    return sorted(
        best.values(),
        key=lambda e: (-e.probability, e.source, e.signal_id, e.document_id or ""),
    )


def _capped_masses(evidence: Sequence[_Evidence]) -> dict[int, float]:
    """Return ``{id(evidence): mass}`` after applying each source's ceiling.

    Scaling inside a source keeps relative attribution intact, so a capped source
    still shows which of its signals mattered most.
    """
    by_source: dict[Source, list[_Evidence]] = {}
    for ev in evidence:
        by_source.setdefault(ev.source, []).append(ev)

    masses: dict[int, float] = {}
    for source, items in by_source.items():
        raw = {id(ev): ev.mass for ev in items}
        total = sum(raw.values())
        ceiling_p = SOURCE_PROBABILITY_CEILING[source]
        ceiling_mass = -math.log(max(1e-12, 1.0 - ceiling_p))
        scale = (ceiling_mass / total) if total > ceiling_mass and total > 0 else 1.0
        for key, value in raw.items():
            masses[key] = value * scale
    return masses


# --------------------------------------------------------------------------- #
# The fusion core                                                             #
# --------------------------------------------------------------------------- #


def _aggregate(evidence: Sequence[_Evidence]) -> float:
    """Fuse normalised evidence into a single 0-100 risk score.

    Bounded log-additive noisy-OR::

        U = sum(-ln(1 - p_i))          (after per-source ceilings)
        S = 100 * (1 - e^-U)

    ``S`` is mathematically confined to ``[0, 100)``: it approaches 100
    asymptotically and can never reach or exceed it, so no clamp is required.
    An empty evidence list gives ``U = 0`` and therefore ``S = 0`` — absence of
    evidence is scored as absence of concern, never as concern.
    """
    if not evidence:
        return 0.0
    total_mass = sum(_capped_masses(evidence).values())
    if total_mass <= 0.0:
        return 0.0
    return round(100.0 * (1.0 - math.exp(-total_mass)), 4)


def _attribute(evidence: Sequence[_Evidence], score: float) -> list[RiskContribution]:
    """Split ``score`` across the evidence exactly, in proportion to mass.

    Because the fusion is additive in log space, ``sum(contribution) == score``
    up to floating-point rounding. That identity is what makes an elevated score
    auditable rather than merely asserted.
    """
    if not evidence or score <= 0.0:
        return []

    masses = _capped_masses(evidence)
    total_mass = sum(masses.values())
    if total_mass <= 0.0:
        return []

    contributions = [
        RiskContribution(
            source=ev.source,
            signal_id=_tag_signal_id(ev.signal_id, ev.document_id),
            signal_score=ev.signal_score,
            weight=round(ev.weight, 4),
            contribution=round(score * (masses[id(ev)] / total_mass), 4),
        )
        for ev in evidence
    ]
    # Most important first; ties broken deterministically so repeat runs match.
    contributions.sort(
        key=lambda c: (-c["contribution"], c["source"], c["signal_id"])
    )
    return contributions


def _risk(
    *,
    scope: Literal["document", "bundle"],
    subject_id: str,
    evidence: Sequence[_Evidence],
) -> Risk:
    ordered = _dedupe(evidence)
    score = _aggregate(ordered)
    return Risk(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        scope=scope,
        subject_id=subject_id,
        score=score,
        severity=severity_for_score(score),
        contributions=_attribute(ordered, score),
        model=MODEL,
    )


# --------------------------------------------------------------------------- #
# Per-document risk (contract §6, scope="document")                           #
# --------------------------------------------------------------------------- #
def score_document(
    document_id: str,
    forensics: Forensics | None = None,
    metadata: Metadata | None = None,
    extraction: Extraction | None = None,
) -> Risk:
    """Score one document from its own forensics, metadata and OCR-quality signals.

    ``extraction`` is optional and additive: callers that do not pass it get
    exactly the previous behaviour. Any section may be ``None`` or malformed —
    it is then simply not counted, never counted against the document.
    """
    evidence: list[_Evidence] = []
    evidence += _forensics_evidence(forensics, document_id)
    evidence += _metadata_evidence(metadata, document_id)
    evidence += _extraction_evidence(extraction, document_id)
    return _risk(scope="document", subject_id=document_id, evidence=evidence)


# --------------------------------------------------------------------------- #
# Bundle risk (contract §6, scope="bundle")                                   #
# --------------------------------------------------------------------------- #
def score_bundle(
    bundle_id: str,
    document_risks: Sequence[Risk] | None = None,
    consistency: Consistency | None = None,
) -> Risk:
    """Fuse per-document evidence with bundle-wide consistency evidence.

    Document evidence is re-used from the already-computed per-document
    contributions rather than re-read from the raw sections, so nothing is
    counted twice; it enters at ``DOCUMENT_MASS_DAMPING`` because it has already
    been reflected in that document's own score. Consistency evidence is genuinely
    new information — it only exists at bundle level — so it enters at full
    weight, which is how document-to-document contradictions meaningfully raise
    the bundle score.
    """
    evidence: list[_Evidence] = []

    for doc_risk in document_risks or []:
        if not isinstance(doc_risk, Mapping):
            continue
        subject = str(doc_risk.get("subject_id") or "unknown_document")
        doc_score = _clamp(_as_float(doc_risk.get("score")), 0.0, 100.0)
        contributions = list(_iter_mapping_list(doc_risk, "contributions"))
        if doc_score <= 0.0 or not contributions:
            continue

        # Invert the document's own attribution to recover each signal's mass.
        # Because attribution was contribution_i = S * (u_i / U), we get
        # u_i = U * (contribution_i / S) exactly — which preserves the
        # confidence, dedupe and source ceilings already applied at document
        # level instead of re-deriving them (and double counting) here.
        doc_mass = -math.log(max(1e-12, 1.0 - doc_score / 100.0))

        for contribution in contributions:
            source = str(contribution.get("source") or "")
            if source not in SOURCE_WEIGHTS:
                continue
            share = _as_float(contribution.get("contribution"))
            if share <= 0.0:
                continue
            raw_id = str(contribution.get("signal_id") or "unnamed_signal")
            signal_id, _ = _untag_signal_id(raw_id)
            signal_mass = doc_mass * (share / doc_score) * DOCUMENT_MASS_DAMPING
            probability = _clamp(1.0 - math.exp(-signal_mass), 0.0, 0.999999)
            if probability <= 0.0:
                continue
            evidence.append(
                _Evidence(
                    source=source,  # type: ignore[arg-type]
                    signal_id=signal_id,
                    signal_score=_clamp(
                        _as_float(contribution.get("signal_score")), 0.0, 100.0
                    ),
                    weight=SOURCE_WEIGHTS[source],  # type: ignore[index]
                    probability=probability,
                    label=signal_id,
                    detail="",
                    document_id=subject,
                    confidence_reported=True,
                )
            )

    evidence += _consistency_evidence(consistency)
    return _risk(scope="bundle", subject_id=bundle_id, evidence=evidence)


# --------------------------------------------------------------------------- #
# Recommendation (contract §7)                                                #
# --------------------------------------------------------------------------- #


def _sources_present(risk: Risk) -> list[str]:
    seen: list[str] = []
    for contribution in _iter_mapping_list(risk, "contributions"):
        source = str(contribution.get("source") or "")
        if source and source not in seen:
            seen.append(source)
    return sorted(seen)


def _band_margin(score: float) -> float:
    """Distance to the nearest severity boundary, normalised to [0,1].

    A score of 24.6 is a coin-flip between accept and review; saying so is more
    useful than pretending the band edge is meaningful to two decimal places.
    """
    boundaries = (25.0, 50.0, 75.0)
    nearest = min(abs(score - b) for b in boundaries)
    return _clamp(nearest / 12.5)


def recommend(
    bundle_risk: Risk,
    *,
    coverage_gaps: Sequence[str] | None = None,
) -> Recommendation:
    """Turn the bundle risk into a reviewer-facing recommendation.

    ``coverage_gaps`` names sections that could not run (e.g. ``["ocr"]`` when
    the OCR engine was unavailable). Gaps *lower confidence*; they never raise
    the score, because a check that did not run is not evidence of anything.
    """
    score = _clamp(_as_float(bundle_risk.get("score")), 0.0, 100.0)
    severity: Severity = bundle_risk.get("severity") or severity_for_score(score)
    if severity not in DEFAULT_DECISION_FOR_SEVERITY:
        severity = severity_for_score(score)
    decision = DEFAULT_DECISION_FOR_SEVERITY[severity]

    headline = {
        "accept": "Low risk — no concerns surfaced",
        "review": "Review required — a human should look at this",
        "reject": "High risk — recommend rejection pending review",
    }[decision]

    contributions = list(_iter_mapping_list(bundle_risk, "contributions"))
    sources = _sources_present(bundle_risk)
    gaps = sorted({str(g) for g in (coverage_gaps or []) if str(g)})

    reasons: list[str] = []
    suggested: list[str] = []

    if not contributions:
        reasons.append(f"[NO_SIGNALS] {REASON_CODES['NO_SIGNALS']}")
    else:
        by_source: dict[str, list[Mapping[str, Any]]] = {}
        for contribution in contributions:
            by_source.setdefault(str(contribution.get("source")), []).append(
                contribution
            )
        code_for = {
            "forensics": "FORENSIC_SIGNALS",
            "metadata": "METADATA_SIGNALS",
            "consistency": "CONSISTENCY_SIGNALS",
            "ocr": "OCR_QUALITY",
        }
        for source in sorted(
            by_source,
            key=lambda s: -sum(
                _as_float(c.get("contribution")) for c in by_source[s]
            ),
        ):
            items = by_source[source]
            top = max(items, key=lambda c: _as_float(c.get("contribution")))
            points = sum(_as_float(c.get("contribution")) for c in items)
            code = code_for.get(source, "OCR_QUALITY")
            reasons.append(
                f"[{code}] {len(items)} {source} signal(s) contributed "
                f"{points:.1f} points; strongest: {top.get('signal_id')}."
            )

        if len(sources) >= 2:
            reasons.append(
                f"[CORROBORATED] {REASON_CODES['CORROBORATED']} "
                f"Sources agreeing: {', '.join(sources)}."
            )
        else:
            reasons.append(
                f"[SINGLE_SOURCE] {REASON_CODES['SINGLE_SOURCE']} "
                f"Only '{sources[0]}' raised anything."
            )
            suggested.append(
                "Corroborate with a second source before acting on this alone."
            )

    if gaps:
        reasons.append(
            f"[COVERAGE_GAP] {REASON_CODES['COVERAGE_GAP']} "
            f"Did not run: {', '.join(gaps)}."
        )
        suggested.append(f"Re-run once these checks are available: {', '.join(gaps)}.")

    margin = _band_margin(score)
    if contributions and margin < 0.25:
        reasons.append(
            f"[NEAR_BOUNDARY] {REASON_CODES['NEAR_BOUNDARY']} "
            f"Score {score:.1f} is close to a band edge."
        )

    if decision == "review":
        suggested.append("Have a reviewer inspect the flagged evidence below.")
    elif decision == "reject":
        suggested.append("Escalate to a senior reviewer before any final decision.")
        suggested.append("Request original documents directly from the issuer.")

    # ---- confidence -------------------------------------------------------- #
    if not contributions:
        confidence = CLEAN_BUNDLE_CONFIDENCE
    else:
        breadth = _clamp(0.55 + 0.15 * len(sources))  # 1 source .70, 3 sources 1.0
        confidence = 0.75 * breadth * (0.72 + 0.28 * margin)
    if gaps:
        confidence *= max(0.4, 1.0 - 0.2 * len(gaps))
    confidence = round(
        _clamp(confidence, MIN_RECOMMENDATION_CONFIDENCE, MAX_RECOMMENDATION_CONFIDENCE),
        4,
    )

    return Recommendation(
        decision=decision,
        confidence=confidence,
        headline=headline,
        reasons=reasons,
        suggested_actions=suggested,
        based_on=RecommendationBasis(
            bundle_risk_score=round(score, 4),
            severity=severity,
        ),
    )


# --------------------------------------------------------------------------- #
# Explanation (contract §8)                                                   #
# --------------------------------------------------------------------------- #

#: RiskContribution.source -> ExplanationEvidence.section
_SECTION_FOR_SOURCE: dict[str, str] = {
    "ocr": "extraction",
    "forensics": "forensics",
    "metadata": "metadata",
    "consistency": "consistency",
}

_SOURCE_TITLES: dict[str, str] = {
    "forensics": "Image or file forensics raised concern",
    "metadata": "File metadata looks implausible",
    "consistency": "Documents disagree with each other",
    "ocr": "Document text could not be read reliably",
}

_GLOSSARY: list[GlossaryEntry] = [
    {
        "term": "Risk score",
        "definition": (
            "A 0-100 triage number showing how much human attention this bundle "
            "deserves. It is not a probability that the document is fraudulent."
        ),
    },
    {
        "term": "Contribution",
        "definition": (
            "How many of the score's points a single signal is responsible for. "
            "Contributions add up to the total score."
        ),
    },
    {
        "term": "Evidence fusion",
        "definition": (
            "Independent signals are combined so that corroborating findings "
            "raise the score more than any one of them could alone, while the "
            "total stays bounded below 100."
        ),
    },
    {
        "term": "ELA",
        "definition": (
            "Error-level analysis: highlights areas of an image that were "
            "re-saved at a different JPEG quality, a common sign of local editing."
        ),
    },
]


def _weight_label(points: float) -> Literal["minor", "moderate", "major"]:
    if points >= FACTOR_MAJOR_POINTS:
        return "major"
    if points >= FACTOR_MODERATE_POINTS:
        return "moderate"
    return "minor"


def explain(
    bundle_risk: Risk,
    document_risks: Sequence[Risk] | None = None,
    consistency: Consistency | None = None,
    *,
    coverage_gaps: Sequence[str] | None = None,
) -> Explanation:
    """Assemble the human-facing narrative.

    Every sentence is derived from values already present in the structured
    inputs: contribution points, signal ids, scores and weights. Nothing is
    inferred, estimated, or invented, and no claim is made about whether the
    document is genuine.
    """
    score = _clamp(_as_float(bundle_risk.get("score")), 0.0, 100.0)
    severity = bundle_risk.get("severity") or severity_for_score(score)
    contributions = list(_iter_mapping_list(bundle_risk, "contributions"))
    gaps = sorted({str(g) for g in (coverage_gaps or []) if str(g)})

    # Detail text keyed by consistency check id, so factors can quote the real
    # wording the consistency module produced rather than paraphrasing it.
    detail_by_id: dict[str, str] = {}
    for check in _iter_mapping_list(consistency, "checks"):
        check_id = str(check.get("id") or "")
        detail = str(check.get("detail") or "")
        if check_id and detail:
            detail_by_id[check_id] = detail

    by_source: dict[str, list[Mapping[str, Any]]] = {}
    for contribution in contributions:
        by_source.setdefault(str(contribution.get("source")), []).append(contribution)

    factors: list[ExplanationFactor] = []
    for source in sorted(
        by_source,
        key=lambda s: -sum(_as_float(c.get("contribution")) for c in by_source[s]),
    ):
        items = sorted(
            by_source[source],
            key=lambda c: (-_as_float(c.get("contribution")), str(c.get("signal_id"))),
        )
        points = sum(_as_float(c.get("contribution")) for c in items)

        evidence: list[ExplanationEvidence] = []
        for contribution in items:
            raw_id = str(contribution.get("signal_id") or "")
            signal_id, doc_id = _untag_signal_id(raw_id)
            signal_score = _as_float(contribution.get("signal_score"))
            weight = _as_float(contribution.get("weight"))
            share = _as_float(contribution.get("contribution"))
            quote = detail_by_id.get(signal_id) or (
                f"{source} reported '{signal_id}' at concern {signal_score:.0f}/100; "
                f"weighted {weight:.2f}, contributing {share:.1f} points."
            )
            evidence.append(
                ExplanationEvidence(
                    document_id=doc_id,
                    section=_SECTION_FOR_SOURCE.get(source, "forensics"),  # type: ignore[typeddict-item]
                    signal_id=signal_id,
                    quote=quote,
                    page=None,
                    bbox=None,
                )
            )

        factors.append(
            ExplanationFactor(
                title=_SOURCE_TITLES.get(source, f"{source} raised concern"),
                impact="increases_risk",
                weight=_weight_label(points),
                evidence=evidence,
            )
        )

    doc_count = len(list(document_risks or []))
    if not contributions:
        summary = (
            f"No module reported a concern across {doc_count} document(s), so the "
            f"triage score is {score:.0f}/100 ({severity}). This means nothing was "
            "flagged — it is not a finding that the documents are genuine."
        )
    else:
        source_names = ", ".join(sorted(by_source))
        summary = (
            f"Triage score {score:.0f}/100 ({severity}) across {doc_count} "
            f"document(s), built from {len(contributions)} signal(s) across "
            f"{len(by_source)} source(s): {source_names}. Contributions below add "
            "up to the score. This is a prompt for human review, not a "
            "determination of fraud."
        )
    if gaps:
        summary += (
            f" Coverage is partial — these checks did not run: {', '.join(gaps)}."
        )

    return Explanation(summary=summary, factors=factors, glossary=list(_GLOSSARY))
