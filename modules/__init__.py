"""EvidenceGuard analysis modules.

Each subpackage is an independent library owned by one developer:

    ocr          -> text & field extraction          (§2 of the contract)
    forensics    -> image forensics + metadata        (§3, §4)
    consistency  -> cross-document checks             (§5)
    risk         -> risk score, recommendation, why   (§6, §7, §8)

Rules (see README.md §4):
  * a module takes plain data in and returns a contract-shaped dict out;
  * a module must NOT import from ``backend`` or from a sibling module;
  * the backend is the only orchestrator.

Shared types live in ``modules.contract``.
"""
