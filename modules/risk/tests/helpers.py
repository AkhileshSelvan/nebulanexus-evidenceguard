"""Builders for contract-shaped sections. No I/O, no network, no fixtures on disk."""

from __future__ import annotations

from typing import Any


def forensic_signal(
    signal_id: str,
    score: float,
    confidence: float = 0.8,
    *,
    passed: bool = False,
    label: str = "",
    detail: str = "",
) -> dict[str, Any]:
    return {
        "id": signal_id,
        "label": label or signal_id.replace("_", " ").title(),
        "score": score,
        "confidence": confidence,
        "passed": passed,
        "pages": [1],
        "regions": [],
        "detail": detail or f"{signal_id} detail",
    }


def forensics(*signals: dict[str, Any], score: float = 0.0) -> dict[str, Any]:
    return {
        "engine": "test-forensics",
        "engine_version": "1.0.0",
        "signals": list(signals),
        "score": score,
        "summary": "test forensics",
    }


def metadata_signal(
    signal_id: str,
    score: float,
    confidence: float = 0.8,
    *,
    passed: bool = False,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "id": signal_id,
        "label": signal_id.replace("_", " ").title(),
        "score": score,
        "confidence": confidence,
        "passed": passed,
        "detail": detail or f"{signal_id} detail",
    }


def metadata(*signals: dict[str, Any], score: float = 0.0) -> dict[str, Any]:
    return {
        "engine": "test-metadata",
        "engine_version": "1.0.0",
        "container": "pdf",
        "raw": {},
        "derived": {
            "created_at": None,
            "modified_at": None,
            "producer": None,
            "creator_tool": None,
            "has_gps": False,
            "software_edits": [],
        },
        "signals": list(signals),
        "score": score,
        "summary": "test metadata",
    }


def consistency_check(
    check_id: str,
    score: float,
    status: str = "fail",
    confidence: float = 0.9,
    *,
    field: str | None = None,
    detail: str = "",
    observed: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "label": check_id.replace("_", " ").title(),
        "field": field,
        "status": status,
        "score": score,
        "confidence": confidence,
        "observed": observed or [],
        "detail": detail or f"{check_id} detail",
    }


def consistency(*checks: dict[str, Any], score: float = 0.0) -> dict[str, Any]:
    return {
        "engine": "test-consistency",
        "engine_version": "1.0.0",
        "checks": list(checks),
        "cross_references": [],
        "score": score,
        "summary": "test consistency",
    }


def extraction(
    *,
    engine: str = "tesseract-5.3.0",
    full_text: str = "some readable text",
    text_confidence: float = 0.9,
) -> dict[str, Any]:
    return {
        "engine": engine,
        "engine_version": "0.1.0",
        "language": "eng",
        "full_text": full_text,
        "text_confidence": text_confidence,
        "fields": [],
        "tables": [],
        "warnings": [],
        "pages": [],
    }


CLEAN_FORENSICS = forensics(forensic_signal("ela_hotspot", 0.0, 0.9, passed=True))
CLEAN_METADATA = metadata(metadata_signal("modified_after_creation", 0.0, 0.9, passed=True))
CLEAN_CONSISTENCY = consistency(consistency_check("name_match", 0.0, "pass", 0.95))
