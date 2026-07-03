"""verify-suite CLI.

``verify-suite check <repo>``  — run every family dimension over the project,
                                roll up a 1-5 level, write a report + a sealed
                                aggregate receipt. Exit code is CI-gateable:
                                0 = pass (or nothing applicable) · 1 = review
                                (warn/error) · 2 = refuse.
``verify-suite dimensions``    — list the registered family dimensions and which
                                gates resolve in this environment.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import gate_available, run_check, score
from .registry import DIMENSIONS
from .report import render_markdown
from .seal import seal_rollup, verity_available

_EXIT = {"pass": 0, "warn": 1, "error": 1, "refuse": 2, None: 0}


def _cmd_check(args) -> int:
    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"verify-suite: path not found: {root}", file=sys.stderr)
        return 3

    absent = sorted({d.cli for d in DIMENSIONS if not gate_available(d)})
    if absent:
        print(f"verify-suite: note — gates not installed: {', '.join(absent)} "
              f"(those dimensions report n/a)", file=sys.stderr)
    if not verity_available():
        print("verify-suite: note — verity-core not importable; the aggregate receipt "
              "will be written UNSEALED (honest n/a, not a fake seal).", file=sys.stderr)

    results = run_check(root, DIMENSIONS)
    scored = score(results)

    chain_path = (Path(args.chain).expanduser() if args.chain
                  else root / "verify-suite-audit.jsonl")
    receipt = seal_rollup(str(root), results, scored, chain_path)

    report = render_markdown(results, scored, str(root), receipt)
    out = Path(args.out).expanduser() if args.out else root / "verify-suite-report.md"
    out.write_text(report, encoding="utf-8")

    receipt_out = (Path(args.receipt_out).expanduser() if args.receipt_out
                   else root / "verify-suite-receipt.json")
    receipt_out.write_text(
        json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    lvl = scored.get("level")
    if lvl is None:
        print(f"Unified reliability level: n/a — {scored.get('note', '')}")
    else:
        print(f"Unified reliability level: {lvl}/5 · "
              f"{scored['passed']}/{scored['applicable']} applicable dimensions passed · "
              f"{scored.get('na', 0)} n/a · worst: {scored.get('worst')}")
    print(f"Report:  {out}")
    print(f"Receipt: {receipt_out} (sealed: {receipt.get('sealed')})")

    if args.json:
        print(json.dumps(receipt, sort_keys=True, ensure_ascii=False))

    return _EXIT.get(scored.get("worst"), 0)


def _cmd_dimensions(args) -> int:
    print("Registered verification-layer dimensions:\n")
    for d in DIMENSIONS:
        state = "installed" if gate_available(d) else "n/a (not installed)"
        print(f"  {d.key:20s} {d.label:28s} -> {d.cli:16s} [{state}]")
    print(f"\nverity-core (sealing substrate): "
          f"{'available' if verity_available() else 'n/a — receipts unsealed'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="verify-suite",
        description="One spine for the verification-layer family: dispatch to each "
                    "shipped checker as a dimension, roll up a 1-5 level, seal the "
                    "aggregate through verity.audit. Orchestrates existing tools; "
                    "re-implements none. Absent gates report n/a.")
    ap.add_argument("--version", action="version", version=f"verify-suite {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="run all family dimensions over a project path")
    c.add_argument("path", help="path to the project (read-only)")
    c.add_argument("--out", help="report output path (default: <path>/verify-suite-report.md)")
    c.add_argument("--receipt-out", dest="receipt_out",
                   help="receipt JSON path (default: <path>/verify-suite-receipt.json)")
    c.add_argument("--chain", help="audit chain path (default: <path>/verify-suite-audit.jsonl)")
    c.add_argument("--json", action="store_true", help="also print the receipt as JSON to stdout")
    c.set_defaults(fn=_cmd_check)

    d = sub.add_parser("dimensions", help="list registered dimensions + install state")
    d.set_defaults(fn=_cmd_dimensions)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
