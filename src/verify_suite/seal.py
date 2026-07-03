"""verify_suite.seal — seal the aggregate verdict through verity's audit chain.

The shared seam across the whole verification-layer family is ``verity.audit``
(``AuditChain`` / ``entry_hash`` / ``GENESIS``). verify-suite does NOT re-implement
the hash chain — it imports the ONE pinned ``verity-core`` and appends the rollup
as a single audit entry, matching the calibration-log / scorecheck / groundtruth
precedent.

Honest fallback: ``verity-core`` is a local-only package. If it is not importable
in this environment, the receipt is still written to disk but is flagged
``"sealed": false`` with the reason — never a fake seal.

Canonical JSON: the event payload is built float-free (levels are ints, fractions
are recorded as ``passed``/``applicable`` integer pairs) so receipts cross-verify
byte-for-byte, per the family convention.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def _payload(root: str, results: list, scored: dict) -> dict:
    """Build the canonical, float-free event payload for the rollup."""
    dims = []
    for r in results:
        dims.append({
            "key": r.key,
            "label": r.label,
            "cli": r.cli,
            "available": bool(r.available),
            "status": r.status,               # pass|warn|refuse|na|error
            "exit_code": (r.verdict.exit_code if r.verdict else None),
        })
    # sort dims by key for a stable, canonical ordering independent of registry order
    dims.sort(key=lambda d: d["key"])
    return {
        "tool": "verify-suite",
        "schema": 1,
        "root": root,
        "level": scored.get("level"),
        "passed": int(scored.get("passed", 0)),
        "applicable": int(scored.get("applicable", 0)),
        "na": int(scored.get("na", 0)),
        "worst": scored.get("worst"),
        "dimensions": dims,
    }


def seal_rollup(root: str, results: list, scored: dict,
                chain_path: Path) -> dict:
    """Append the rollup to a verity AuditChain. Returns a receipt dict with the
    payload, the seal status, and (when sealed) the entry hash + chain head.

    Never raises on a missing verity: falls back to an unsealed receipt.
    """
    payload = _payload(root, results, scored)
    receipt = {
        "receipt_version": 1,
        "payload": payload,
    }
    try:
        from verity.audit import AuditChain  # the ONE shared sealing substrate
    except Exception as e:  # noqa: BLE001
        receipt["sealed"] = False
        receipt["seal_reason"] = (
            "verity-core not importable in this environment "
            f"({type(e).__name__}); receipt written unsealed (honest n/a, not a fake seal)."
        )
        return receipt

    chain = AuditChain(chain_path)
    entry = chain.append("verify_suite.rollup", payload, actor="verify-suite")
    receipt["sealed"] = True
    receipt["chain_path"] = str(chain_path)
    receipt["seq"] = entry["seq"]
    receipt["entry_hash"] = entry["entry_hash"]
    receipt["prev_hash"] = entry["prev_hash"]
    receipt["chain_head"] = chain.head()
    return receipt


def verity_available() -> bool:
    try:
        import verity.audit  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False
