"""verify_suite.report — render the unified reliability report (markdown).

No data leaves the machine. The report shows every registered dimension, its
verdict (or n/a with the reason), the unified 1-5 level, and the seal status of
the aggregate receipt.
"""
from __future__ import annotations

_ICON = {"pass": "PASS", "warn": "REVIEW", "refuse": "REFUSE", "na": "n/a", "error": "ERROR"}


def _na_reason(r) -> str:
    if not r.available:
        return "gate not installed"
    if not r.applicable_here or r.verdict is None:
        return "no matching artifact in this project"
    return ""


def render_markdown(results: list, scored: dict, root: str, receipt: dict) -> str:
    lvl = scored.get("level")
    lines = ["# Verification-layer report — " + str(root), ""]
    if lvl is None:
        lines += ["**Unified reliability level: n/a** — " + scored.get("note", ""), ""]
    else:
        lines += [f"**Unified reliability level: {lvl} / 5**  ·  "
                  f"{scored['passed']} of {scored['applicable']} applicable dimensions passed"
                  f"  ·  {scored.get('na', 0)} n/a"
                  f"  ·  worst verdict: {_ICON.get(scored.get('worst'), '?')}", ""]

    lines += ["## Dimensions", "",
              "| Dimension | Verdict | Powered by | Note |", "|---|---|---|---|"]
    for r in results:
        note = _na_reason(r)
        powered = f"`{r.cli}`" + ("" if r.available else " — not installed")
        lines.append(f"| {r.label} | {_ICON.get(r.status, '?')} | {powered} | {note} |")
    lines.append("")

    # detail for any non-clean, runnable verdict
    flagged = [r for r in results if r.status in ("warn", "refuse", "error")]
    if flagged:
        lines += ["## What to look at next", ""]
        for r in flagged:
            first = (r.verdict.detail.splitlines()[0][:160]
                     if (r.verdict and r.verdict.detail) else "")
            lines.append(f"- **{r.label}** → {_ICON.get(r.status)}"
                         + (f" — {first}" if first else ""))
        lines.append("")

    # the seal
    lines += ["## Aggregate receipt (sealed through verity.audit)", ""]
    if receipt.get("sealed"):
        lines += [
            f"- sealed: **yes** · chain `{receipt.get('chain_path')}`",
            f"- seq {receipt.get('seq')} · entry_hash `{receipt.get('entry_hash')}`",
            f"- chain head `{receipt.get('chain_head')}`",
            "",
            "> Re-verify the chain with verity's own audit verifier. Unkeyed = integrity "
            "(catches corruption/reorder/truncation); add a key or anchor the head for "
            "tamper-evidence.",
            "",
        ]
    else:
        lines += [
            f"- sealed: **no** — {receipt.get('seal_reason', 'verity-core unavailable')}",
            "> The receipt payload is still written; it is simply not hash-sealed here. "
            "This is reported honestly as unsealed, not as a passing seal.",
            "",
        ]

    lines += [
        "## How the level is computed (inspect it)",
        "Level = round(1 + 4 × passed / applicable), over only the dimensions that *apply* "
        "(a gate that isn't installed, or one with no matching artifact in this project, is "
        "`n/a` and is never counted — there is no fake pass). 5/5 = every applicable "
        "dimension is green.",
        "",
        "## Honest scope",
        "verify-suite ORCHESTRATES existing checkers; it re-implements none of them. It "
        "reports what each present gate says and marks absent gates n/a. The underlying "
        "checkers (firewall / grounded) are lexical/deterministic — this is not semantic "
        "grounding. No track record is claimed.",
        "",
    ]
    return "\n".join(lines)
