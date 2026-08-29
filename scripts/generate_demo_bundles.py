"""Generate the text-bearing demo bundles used in the EvidenceGuard demo.

Companion to ``generate_fixtures.py``, which produces *forensic* fixtures
(tampered images, contradictory metadata). Those carry no OCR-readable text,
so they exercise the forensics path but leave OCR and cross-document
consistency with nothing to compare.

This script produces the two identity bundles the demo narrates:

  Demo A -- demoA_id_card.pdf + demoA_payslip.pdf
      One synthetic person, stated identically on both documents.
      Expected: name/DOB/address checks PASS, LOW risk, ACCEPT.

  Demo B -- demoB_id_card.pdf + demoB_payslip.pdf
      The same ID card, paired with a payslip naming a different person,
      born on a different date, living at a different address.
      Expected: name/DOB/address checks FAIL, HIGH risk, REVIEW.

Every person, employer, address and identifier below is invented. Nothing
here is derived from a real person or a real document.

Layout notes -- the pipeline rasterizes PDFs with PyMuPDF at 200 DPI and
reads them with Tesseract (there is no text-layer shortcut), so pages use a
plain serif/sans face at 12pt with generous leading, which renders to ~33px
glyphs at that DPI.

Field labels are chosen to match the extractor's own label patterns in
``modules/ocr/fields.py`` ("Full Name:", "Date of Birth:", "Address:",
"ID Number:", "Reference No:", "Gross Pay", "Net Pay").

Run from the repo root:
    python scripts/generate_demo_bundles.py

Writes into data/demo/cases/.
"""

from __future__ import annotations

import os

import pymupdf

OUT_DIR = os.path.join("data", "demo", "cases")

# A fixed, self-consistent timestamp. Creation == modification so the
# metadata analyzer has no date anomaly to report -- the demo bundles are
# about identity consistency, not metadata forensics.
STAMP = "D:20250412090000+00'00'"

PAGE_W, PAGE_H = 595, 842  # A4 points
MARGIN_X = 64
TITLE_SIZE = 16
HEAD_SIZE = 11
BODY_SIZE = 12
LEADING = 26


def _write_pdf(path: str, title: str, subtitle: str, rows: list[tuple[str, str]],
               footer: list[str]) -> None:
    """Render one single-page document with a title and label/value rows."""
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)

    y = 96
    page.insert_text((MARGIN_X, y), title, fontsize=TITLE_SIZE, fontname="hebo")
    y += 24
    page.insert_text((MARGIN_X, y), subtitle, fontsize=HEAD_SIZE, fontname="helv")
    y += 14
    page.draw_line(pymupdf.Point(MARGIN_X, y), pymupdf.Point(PAGE_W - MARGIN_X, y))
    y += 34

    for label, value in rows:
        if not label and not value:
            y += LEADING // 2
            continue
        # One label and its value on a single line: the extractor reads the
        # tail of the label's own line, and (for addresses) at most the two
        # lines after it.
        page.insert_text((MARGIN_X, y), f"{label}: {value}", fontsize=BODY_SIZE, fontname="helv")
        y += LEADING

    y += 18
    page.draw_line(pymupdf.Point(MARGIN_X, y), pymupdf.Point(PAGE_W - MARGIN_X, y))
    y += 24
    for line in footer:
        page.insert_text((MARGIN_X, y), line, fontsize=HEAD_SIZE - 1, fontname="helv")
        y += 18

    doc.set_metadata({
        "title": title,
        "author": "EvidenceGuard demo generator",
        "subject": "Synthetic document for software testing",
        "creator": "EvidenceGuard demo generator",
        "producer": "EvidenceGuard demo generator",
        "creationDate": STAMP,
        "modDate": STAMP,
    })
    doc.save(path)
    doc.close()
    print(f"  wrote {path}")


FOOTER = [
    "Synthetic document generated for software testing.",
    "It does not describe a real person and has no legal validity.",
]

# --------------------------------------------------------------------------- #
# Demo A -- one person, stated consistently                                    #
# --------------------------------------------------------------------------- #

A_NAME = "Priya Raman"
A_DOB = "1994-03-12"
A_ADDRESS = "42 Marina Crescent, Chennai 600004"


def gen_demo_a() -> None:
    _write_pdf(
        os.path.join(OUT_DIR, "demoA_id_card.pdf"),
        "NORTHAVEN NATIONAL IDENTITY CARD",
        "Office of the Civil Registry - Chennai Central",
        [
            ("Full Name", A_NAME),
            ("Date of Birth", A_DOB),
            ("Address", A_ADDRESS),
            ("ID Number", "NX-4471982"),
            ("", ""),
            ("Date of Issue", "2019-06-04"),
            ("Date of Expiry", "2029-06-03"),
            ("Nationality", "Northaven"),
        ],
        FOOTER,
    )

    _write_pdf(
        os.path.join(OUT_DIR, "demoA_payslip.pdf"),
        "NORTHAVEN LOGISTICS LIMITED",
        "Monthly salary statement - April 2025",
        [
            ("Employee Name", A_NAME),
            ("Date of Birth", A_DOB),
            ("Address", A_ADDRESS),
            # Deliberately NOT the ID-card number: a payroll reference and a
            # national ID are different identifiers, and repeating one value
            # across both documents would trip the document_number_reuse check.
            ("Reference No", "NL-2208734"),
            ("", ""),
            ("Pay Period", "2025-04-01 to 2025-04-30"),
            # No "Basic Salary" line: _money_key_for_line maps the `salary`
            # label onto the gross_pay key, so a basic-pay row registers as a
            # second gross_pay and _best_value can pick the smaller of the two,
            # making net look like it exceeds gross.
            ("Gross Pay", "INR 62500.00"),
            ("Deductions", "INR 9375.00"),
            ("Net Pay", "INR 53125.00"),
        ],
        FOOTER,
    )


# --------------------------------------------------------------------------- #
# Demo B -- the same ID card, a payslip for someone else                       #
# --------------------------------------------------------------------------- #

B_NAME_CONFLICT = "Meera Krishnan"
B_DOB_CONFLICT = "1988-11-27"
B_ADDRESS_CONFLICT = "9 Harbour View Road, Kochi 682001"


def gen_demo_b() -> None:
    _write_pdf(
        os.path.join(OUT_DIR, "demoB_id_card.pdf"),
        "NORTHAVEN NATIONAL IDENTITY CARD",
        "Office of the Civil Registry - Chennai Central",
        [
            ("Full Name", A_NAME),
            ("Date of Birth", A_DOB),
            ("Address", A_ADDRESS),
            ("ID Number", "NX-4471982"),
            ("", ""),
            ("Date of Issue", "2019-06-04"),
            ("Date of Expiry", "2029-06-03"),
            ("Nationality", "Northaven"),
        ],
        FOOTER,
    )

    _write_pdf(
        os.path.join(OUT_DIR, "demoB_payslip.pdf"),
        "NORTHAVEN LOGISTICS LIMITED",
        "Monthly salary statement - April 2025",
        [
            # Three independent contradictions against the ID card above.
            ("Employee Name", B_NAME_CONFLICT),
            ("Date of Birth", B_DOB_CONFLICT),
            ("Address", B_ADDRESS_CONFLICT),
            ("Reference No", "NL-3391775"),
            ("", ""),
            ("Pay Period", "2025-04-01 to 2025-04-30"),
            # No "Basic Salary" line: _money_key_for_line maps the `salary`
            # label onto the gross_pay key, so a basic-pay row registers as a
            # second gross_pay and _best_value can pick the smaller of the two,
            # making net look like it exceeds gross.
            ("Gross Pay", "INR 62500.00"),
            ("Deductions", "INR 9375.00"),
            ("Net Pay", "INR 53125.00"),
        ],
        FOOTER,
    )


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Generating demo bundles into", OUT_DIR)
    gen_demo_a()
    gen_demo_b()
    print("Done.")
