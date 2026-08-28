"""Heuristic structured-field extraction from OCR output.

Rules of the road (see task requirement 10):
  * only emit a field when a pattern genuinely matches;
  * confidence is honest — it blends OCR word confidence with how strong the
    textual cue was (an explicit label beats a bare pattern);
  * never invent a value; a field we cannot find simply is not in the list.

Input is plain OCR text plus optional per-word geometry (for bounding boxes).
Output is a list of ``ExtractionField`` dicts from the shared contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from modules.contract import ExtractionField

from .engine import OcrWord

# --------------------------------------------------------------------------- #
# Date handling                                                               #
# --------------------------------------------------------------------------- #

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

_DATE_PATTERNS = [
    # 2024-07-31  /  2024.07.31
    re.compile(r"\b(?P<y>\d{4})[-/.](?P<m>\d{1,2})[-/.](?P<d>\d{1,2})\b"),
    # 31/07/2024  /  31-07-2024  /  31.07.24
    re.compile(r"\b(?P<d>\d{1,2})[-/.](?P<m>\d{1,2})[-/.](?P<y>\d{2,4})\b"),
    # 31 July 2024  /  31 Jul 2024
    re.compile(
        r"\b(?P<d>\d{1,2})\s+(?P<mon>[A-Za-z]{3,9})\.?\s+(?P<y>\d{4})\b"
    ),
    # July 31, 2024  /  Jul 31 2024
    re.compile(
        r"\b(?P<mon>[A-Za-z]{3,9})\.?\s+(?P<d>\d{1,2}),?\s+(?P<y>\d{4})\b"
    ),
]


def _iso_or_none(raw: str) -> str | None:
    """Best-effort normalization to YYYY-MM-DD; ``None`` if genuinely ambiguous."""
    for pat in _DATE_PATTERNS:
        m = pat.search(raw)
        if not m:
            continue
        gd = m.groupdict()
        year = gd.get("y")
        if year and len(year) == 2:
            year = ("20" if int(year) < 70 else "19") + year
        month = gd.get("m")
        if gd.get("mon"):
            month = str(_MONTHS.get(gd["mon"].lower().rstrip("."), 0) or "")
        if not (year and month and gd.get("d")):
            return None
        try:
            y, mo, d = int(year), int(month), int(gd["d"])
        except ValueError:
            return None
        if not (1 <= mo <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100):
            # day/month may be swapped in DD/MM vs MM/DD — bail rather than guess
            return None
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


def _find_dates(text: str) -> list[re.Match[str]]:
    seen: set[tuple[int, int]] = set()
    out: list[re.Match[str]] = []
    for pat in _DATE_PATTERNS:
        for m in pat.finditer(text):
            span = m.span()
            if any(span[0] < e and s < span[1] for s, e in seen):
                continue
            seen.add(span)
            out.append(m)
    return sorted(out, key=lambda m: m.start())


# --------------------------------------------------------------------------- #
# Other value patterns                                                        #
# --------------------------------------------------------------------------- #

_ID_VALUE = re.compile(r"\b(?=[A-Za-z0-9-]{5,20}\b)(?=[A-Za-z0-9-]*\d)[A-Za-z0-9-]+\b")
_MONEY = re.compile(
    r"(?P<cur>₹|Rs\.?|INR|\$|USD|US\$|€|EUR|£|GBP)\s?"
    r"(?P<amt>\d{1,3}(?:[,\s]\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_BARE_AMOUNT = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b|\b\d+\.\d{2}\b")
_SCORE = re.compile(
    r"\b(?P<num>\d{1,3}(?:\.\d{1,2})?)\s*(?P<suffix>%|/\s*100|/\s*10|out of \d+)?",
    re.IGNORECASE,
)
_NAME_VALUE = re.compile(r"[A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3}")

_LABELS = {
    "date_of_birth": re.compile(
        r"\b(date of birth|d\.?\s?o\.?\s?b\.?|birth\s?date|born on|date born)\b",
        re.IGNORECASE,
    ),
    "issue_date": re.compile(
        r"\b(date of issue|issue date|issued on|issued|doi)\b", re.IGNORECASE
    ),
    "expiry_date": re.compile(
        r"\b(date of expiry|expiry date|expires on|expiry|valid (?:till|until|upto|up to)|doe)\b",
        re.IGNORECASE,
    ),
    "document_number": re.compile(
        r"\b((?:id|identification|licen[cs]e|certificate|cert|registration|reg|"
        r"enrol(?:l)?ment|passport|document|reference|ref|roll|application|acc?ount)"
        r"\s*(?:no\.?|number|#|id)?)\b\s*[:\-#]?",
        re.IGNORECASE,
    ),
    "full_name": re.compile(
        r"\b(full name|name of (?:holder|candidate|student|employee|applicant)|"
        r"holder(?:'s)? name|candidate name|student name|employee name|name)\b\s*[:\-]",
        re.IGNORECASE,
    ),
    "address": re.compile(
        r"\b(address|residential address|permanent address|addr)\b\s*[:\-]",
        re.IGNORECASE,
    ),
    "gross_pay": re.compile(r"\b(gross (?:pay|salary|earnings)|gross)\b", re.IGNORECASE),
    "net_pay": re.compile(
        r"\b(net (?:pay|salary|amount)|take[-\s]?home|net)\b", re.IGNORECASE
    ),
    "salary": re.compile(r"\b(salary|ctc|basic pay|basic salary|wage)\b", re.IGNORECASE),
    "total": re.compile(r"\b(total|grand total|amount due|balance)\b", re.IGNORECASE),
    "score": re.compile(
        r"\b(score|marks(?: obtained)?|grade|percentage|percentile|cgpa|gpa|"
        r"result|band score|overall(?: band)?)\b\s*[:\-]?",
        re.IGNORECASE,
    ),
}


# --------------------------------------------------------------------------- #
# bbox mapping                                                                #
# --------------------------------------------------------------------------- #


def _norm_alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _bbox_for_value(
    value: str,
    words: list[OcrWord],
    page_w: int,
    page_h: int,
) -> list[float] | None:
    """Union the boxes of the shortest run of consecutive words whose text
    contains the value's alphanumerics. Returns page-fraction [x0,y0,x1,y1]."""
    target = _norm_alnum(value)
    if not target or not words or page_w <= 0 or page_h <= 0:
        return None
    norms = [_norm_alnum(w.text) for w in words]
    n = len(words)
    for i in range(n):
        if not norms[i]:
            continue
        acc = ""
        for j in range(i, min(n, i + 12)):
            acc += norms[j]
            if target in acc:
                run = words[i : j + 1]
                x0 = min(w.left for w in run)
                y0 = min(w.top for w in run)
                x1 = max(w.left + w.width for w in run)
                y1 = max(w.top + w.height for w in run)
                return [
                    round(max(0.0, x0 / page_w), 4),
                    round(max(0.0, y0 / page_h), 4),
                    round(min(1.0, x1 / page_w), 4),
                    round(min(1.0, y1 / page_h), 4),
                ]
            if len(acc) > len(target) + 24:
                break
    return None


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #


@dataclass
class FieldExtractionResult:
    fields: list[ExtractionField]
    warnings: list[str]


_CONF_LABELLED = 0.92
_CONF_PATTERN = 0.6
_CONF_WEAK = 0.45
_MIN_OCR_CONF_FLOOR = 0.35  # used when OCR reported 0 confidence but text exists


def _mk_field(
    key: str,
    value: str,
    data_type: str,
    cue_strength: float,
    ocr_conf: float,
    page: int,
    words: list[OcrWord],
    page_w: int,
    page_h: int,
    normalized: str | None = None,
) -> ExtractionField:
    value = value.strip(" \t:;,-–—")
    base = ocr_conf if ocr_conf > 0 else _MIN_OCR_CONF_FLOOR
    confidence = round(max(0.0, min(1.0, base * cue_strength)), 4)
    norm = normalized if normalized is not None else re.sub(r"\s+", " ", value).strip().lower()
    return ExtractionField(
        key=key,
        value=value,
        value_normalized=norm or None,
        data_type=data_type,  # type: ignore[typeddict-item]
        confidence=confidence,
        page=page,
        bbox=_bbox_for_value(value, words, page_w, page_h),
    )


def extract_fields(
    text: str,
    words: list[OcrWord],
    *,
    page: int = 1,
    page_width: int = 0,
    page_height: int = 0,
    ocr_confidence: float = 0.0,
) -> FieldExtractionResult:
    """Pull structured fields out of one page's OCR text."""
    fields: list[ExtractionField] = []
    warnings: list[str] = []
    if not text or not text.strip():
        return FieldExtractionResult(fields, warnings)

    lines = [ln.strip() for ln in text.splitlines()]
    claimed_date_spans: list[tuple[int, int]] = []

    def add(field: ExtractionField) -> None:
        # de-dupe on (key, normalized value)
        for existing in fields:
            if existing["key"] == field["key"] and (
                existing["value_normalized"] == field["value_normalized"]
            ):
                if field["confidence"] > existing["confidence"]:
                    fields.remove(existing)
                    break
                return
        fields.append(field)

    # ---- labelled dates: DOB / issue / expiry ---------------------------- #
    for key in ("date_of_birth", "issue_date", "expiry_date"):
        label = _LABELS[key]
        for ln in lines:
            if not label.search(ln):
                continue
            dm = _find_dates(ln)
            if not dm:
                continue
            m = dm[0]
            raw = m.group(0)
            add(
                _mk_field(
                    key, raw, "date", _CONF_LABELLED, ocr_confidence, page,
                    words, page_width, page_height, normalized=_iso_or_none(raw) or None,
                )
            )
            claimed_date_spans.append(m.span())

    # ---- remaining unlabelled dates ------------------------------------- #
    for m in _find_dates(text):
        if any(s < m.end() and m.start() < e for s, e in claimed_date_spans):
            continue
        raw = m.group(0)
        add(
            _mk_field(
                "date", raw, "date", _CONF_PATTERN, ocr_confidence, page,
                words, page_width, page_height, normalized=_iso_or_none(raw) or None,
            )
        )

    # ---- document / certificate number -------------------------------- #
    label = _LABELS["document_number"]
    for ln in lines:
        lm = label.search(ln)
        if not lm:
            continue
        tail = ln[lm.end():]
        vm = _ID_VALUE.search(tail)
        if not vm:
            continue
        val = vm.group(0)
        if _iso_or_none(val):  # a date, not an id
            continue
        add(
            _mk_field(
                "document_number", val, "id", _CONF_LABELLED, ocr_confidence,
                page, words, page_width, page_height,
                normalized=val.upper().replace(" ", ""),
            )
        )

    # ---- full name --------------------------------------------------- #
    label = _LABELS["full_name"]
    for ln in lines:
        lm = label.search(ln)
        if not lm:
            continue
        tail = ln[lm.end():].strip(" :\t-")
        if not tail or any(ch.isdigit() for ch in tail):
            continue
        nm = _NAME_VALUE.search(tail) or re.match(r"[A-Za-z'’.\- ]{3,60}", tail)
        if not nm:
            continue
        val = nm.group(0).strip()
        if len(val.split()) < 2:
            continue
        # "name" alone is a weak cue; the more specific labels are strong.
        strong = bool(re.search(r"full name|candidate|student|employee|holder|applicant", ln, re.IGNORECASE))
        add(
            _mk_field(
                "full_name", val, "string",
                _CONF_LABELLED if strong else _CONF_WEAK,
                ocr_confidence, page, words, page_width, page_height,
            )
        )

    # ---- address --------------------------------------------------- #
    label = _LABELS["address"]
    for idx, ln in enumerate(lines):
        lm = label.search(ln)
        if not lm:
            continue
        parts = [ln[lm.end():].strip(" :\t-")]
        for cont in lines[idx + 1 : idx + 3]:
            if not cont or _is_label_line(cont):
                break
            parts.append(cont)
        val = ", ".join(p for p in parts if p)
        if len(val) < 6:
            continue
        add(
            _mk_field(
                "address", val, "string", _CONF_LABELLED, ocr_confidence,
                page, words, page_width, page_height,
            )
        )
        break

    # ---- monetary amounts: gross / net / salary / total / amount ---- #
    for ln in lines:
        for mm in _MONEY.finditer(ln):
            amount = mm.group(0)
            key = _money_key_for_line(ln)
            add(
                _mk_field(
                    key, amount, "currency",
                    _CONF_LABELLED if key != "amount" else _CONF_PATTERN,
                    ocr_confidence, page, words, page_width, page_height,
                    normalized=_normalize_amount(mm.group("amt")),
                )
            )

    # ---- score / marks / grade ------------------------------------- #
    label = _LABELS["score"]
    for ln in lines:
        lm = label.search(ln)
        if not lm:
            continue
        tail = ln[lm.end():]
        sm = _SCORE.search(tail)
        if not sm or not sm.group("num"):
            continue
        raw = sm.group(0).strip()
        add(
            _mk_field(
                "score", raw, "number", _CONF_LABELLED, ocr_confidence,
                page, words, page_width, page_height,
                normalized=sm.group("num"),
            )
        )

    low = [f["key"] for f in fields if f["confidence"] < 0.5]
    if low:
        warnings.append(
            f"page {page}: low-confidence field(s): {', '.join(sorted(set(low)))}"
        )
    return FieldExtractionResult(fields, warnings)


def _is_label_line(line: str) -> bool:
    return any(pat.search(line) for pat in _LABELS.values())


def _money_key_for_line(line: str) -> str:
    if _LABELS["net_pay"].search(line):
        return "net_pay"
    if _LABELS["gross_pay"].search(line) or _LABELS["salary"].search(line):
        return "gross_pay"
    if _LABELS["total"].search(line):
        return "total"
    return "amount"


def _normalize_amount(amt: str) -> str:
    cleaned = amt.replace(",", "").replace(" ", "")
    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return cleaned
