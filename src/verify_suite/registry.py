"""verify_suite.registry — the verification-layer family as pluggable dimensions.

Each entry names a REAL shipped tool by its real CLI and wires that tool's own
sub-command + exit-code contract. verify-suite runs these as subprocesses and
re-implements none of them. A tool whose CLI does not resolve is reported ``n/a``.

Artifact conventions (kept deliberately simple + inspectable):

* ``docs_claims`` / ``result_claims`` / ``citations`` mirror shipwright — they run
  over the project's own README-style markdown.
* ``scorecheck`` / ``groundtruth`` / ``calibration`` / ``drift`` / ``scope`` only run
  when the project ships the input each expects (a receipt, a committed dataset,
  a reconcile pair, a drift store, a target-file). If the input is absent the
  dimension is n/a for THIS project — never a fake pass.
* ``security`` shells ``aisec-check scan <root>`` — a read-only lexical/AST source
  scan for AI-app vulnerability classes. Its findings are LEADS (candidate issues a
  human must confirm), not proofs; the exit-map folds worst-severity into the
  verify-suite ladder (0 clean=pass · low/medium=warn · high/critical=refuse). n/a
  when the project ships no Python to scan.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .core import (
    Dimension,
    map_aisec_severity,
    map_allow_deny,
    map_verity,
    map_zero_clean,
)

# ── artifact helpers (consent-first: only ever look under the given root) ─────
_SKIP = {".venv", "node_modules", ".git", "site-packages", "__pycache__"}


def _first_markdown(root: Path, *, prefer: Optional[str] = None) -> Optional[Path]:
    mds = [p for p in sorted(root.rglob("*.md"))
           if not any(seg in _SKIP for seg in p.parts)]
    if not mds:
        return None
    if prefer:
        for p in mds:
            if p.name.lower() == prefer.lower():
                return p
    # else the shallowest README, else the shallowest markdown
    for p in mds:
        if p.name.lower() == "readme.md":
            return p
    return mds[0]


def _find_one(root: Path, *globs: str) -> Optional[Path]:
    for g in globs:
        for p in sorted(root.rglob(g)):
            if not any(seg in _SKIP for seg in p.parts):
                return p
    return None


# ── command builders (each owns its tool's real sub-command) ──────────────────
def _cmd_firewall(_bin: str, root: Path) -> Optional[list]:
    doc = _first_markdown(root, prefer="README.md")
    if doc is None:
        return None
    truth = _find_one(root, "truth.yaml", "truth.yml")
    args = []
    if truth is not None:
        args += ["--truth", str(truth)]
    args += [str(doc)]
    return args


def _cmd_verity_markdown(_bin: str, root: Path) -> Optional[list]:
    doc = _first_markdown(root, prefer="README.md")
    if doc is None:
        return None
    return ["verify-markdown", str(doc)]


def _cmd_grounded(_bin: str, root: Path) -> Optional[list]:
    doc = _first_markdown(root, prefer="README.md")
    if doc is None:
        return None
    return ["--no-net", str(doc)]


def _cmd_scorecheck(_bin: str, root: Path) -> Optional[list]:
    receipt = _find_one(root, "*receipt*.json", "*.receipt.json")
    if receipt is None:
        return None
    return ["verify", "--receipt", str(receipt)]


def _cmd_groundtruth(_bin: str, root: Path) -> Optional[list]:
    commitment = _find_one(root, "COMMITMENT.txt")
    if commitment is None:
        return None
    return ["verify", "--commitment", str(commitment)]


def _cmd_calibration(_bin: str, root: Path) -> Optional[list]:
    # reconcile a published claim-set against its source-of-truth, if both ship.
    published = _find_one(root, "published.jsonl", "published.json")
    source = _find_one(root, "source.jsonl", "source.json")
    if published is None or source is None:
        return None
    return ["reconcile", "--published", str(published), "--source", str(source)]


def _cmd_drift(_bin: str, root: Path) -> Optional[list]:
    store = _find_one(root, "drift-store.jsonl", "drift_store.jsonl")
    if store is None:
        return None
    return ["--store", str(store), "report"]


def _cmd_security(_bin: str, root: Path) -> Optional[list]:
    # aisec-check scan <root>: a read-only lexical/AST source scan. Applicable to
    # any project that ships Python to scan; n/a otherwise (no fake pass).
    has_py = any(
        not any(seg in _SKIP for seg in p.parts)
        for p in root.rglob("*.py")
    )
    if not has_py:
        return None
    return ["scan", str(root)]


def _cmd_scope(_bin: str, root: Path) -> Optional[list]:
    # scope-gate <target>; only runs if the project declares a scope target file.
    target = _find_one(root, "scope-target.txt")
    if target is None:
        return None
    try:
        tgt = target.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    except Exception:
        return None
    if not tgt:
        return None
    return [tgt]


# ── the family registry (order = report order) ────────────────────────────────
DIMENSIONS: list = [
    Dimension("docs_claims", "Doc/output over-claims", "firewall",
              _cmd_firewall, map_zero_clean),
    Dimension("result_claims", "Result-claim hygiene", "verity",
              _cmd_verity_markdown, map_verity),
    Dimension("citations", "Citation grounding", "grounded",
              _cmd_grounded, map_zero_clean, module="grounded"),
    Dimension("benchmark_receipt", "Benchmark-claim receipt", "scorecheck",
              _cmd_scorecheck, map_zero_clean),
    Dimension("dataset_commitment", "Dataset commitment", "groundtruth",
              _cmd_groundtruth, map_zero_clean),
    Dimension("calibration", "Prediction calibration", "calibration-log",
              _cmd_calibration, map_zero_clean, module="calibration_log.cli"),
    Dimension("drift", "Quality drift", "drift-watch",
              _cmd_drift, map_zero_clean),
    Dimension("scope", "Authorization scope", "scope-gate",
              _cmd_scope, map_allow_deny, module="scope_gate"),
    Dimension("security", "AI-app security leads", "aisec-check",
              _cmd_security, map_aisec_severity),
]

DIMENSIONS_BY_KEY = {d.key: d for d in DIMENSIONS}
