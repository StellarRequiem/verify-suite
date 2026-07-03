# verify-suite

**One spine for a family of verification checkers.** `verify-suite` is a meta-CLI
that dispatches to each shipped checker as a pluggable *dimension*, reports every
present gate's verdict (absent gates report `n/a`), rolls up a transparent **1–5
reliability level**, and seals the aggregate through an audit chain.

It **orchestrates existing tools and re-implements none of them.** Every dimension
shells out to that tool's own CLI. If a tool is not installed, its dimension is
reported `n/a` — never a fake pass.

## What it composes

| Dimension | Powered by (CLI) | What it checks |
|---|---|---|
| Doc/output over-claims | `firewall` | claims in your README/docs vs a declared `truth.yaml` |
| Result-claim hygiene | `verity verify-markdown` | statistical soundness of result-claims in markdown |
| Citation grounding | `grounded --no-net` | citations resolve to the source they cite (lexical) |
| Benchmark-claim receipt | `scorecheck verify` | a benchmark-claim receipt re-derives |
| Dataset commitment | `groundtruth verify` | a committed dataset's root still matches |
| Prediction calibration | `calibration-log reconcile` | published predictions vs their source of truth |
| Quality drift | `drift-watch report` | quality-signal drift store |
| Authorization scope | `scope-gate <target>` | a declared target is in authorized scope |
| AI-app security leads | `aisec-check scan <root>` | lexical/AST leads for AI-app vuln classes (candidate findings, not proofs) |

Each of these is a separate, independently-shipped checker. `verify-suite` adds
only the **dispatch spine**: a dimension registry, the subprocess dispatcher, the
1–5 rollup, and the aggregate seal. The dispatcher pattern (`_resolve` →
`run_dimension` → exit-code→verdict → `score`) is generalized from the proven
subprocess-composition in `shipwright.core`.

## The aggregate seal

The rollup is sealed through **`verity.audit.AuditChain`** — the shared sealing
substrate used across this family. `verify-suite` does **not** re-implement the
hash chain; it imports the one pinned `verity-core` and appends the rollup as a
single audit entry. The payload is **canonical JSON** (sorted keys) and
**float-free** (levels are ints; the fraction is recorded as integer
`passed`/`applicable`) so receipts cross-verify byte-for-byte.

`verity-core` is a local package. **If it is not importable, the receipt is still
written but flagged `"sealed": false` with the reason** — reported honestly as
unsealed, never as a passing seal.

> **Threat model (inherited from `verity.audit`).** Unkeyed = *integrity*
> (catches accidental corruption, reordering, truncation). It is **not**
> tamper-evidence on its own; add a key or anchor the chain head for that.

## Install

```sh
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

The family checkers are separate packages. Install whichever you want active into
the **same venv** (so their console scripts co-locate with `verify-suite`); any you
skip will report `n/a`. `verity-core` supplies the seal.

## Use

```sh
verify-suite dimensions          # list dimensions + which gates resolve here
verify-suite check <repo>        # run all dimensions, write report + sealed receipt
```

`check` writes `verify-suite-report.md`, `verify-suite-receipt.json`, and appends
the rollup to `verify-suite-audit.jsonl`. Exit code is CI-gateable:
`0` = pass (or nothing applicable) · `1` = review · `2` = refuse.

## Honest scope

- It **orchestrates**; it does not verify anything itself. A `5/5` means *these
  specific deterministic gates that applied all passed* — not "provably reliable".
- The underlying `firewall` / `grounded` checkers are **lexical/deterministic**.
  This is **not** semantic grounding.
- The **security** dimension (`aisec-check`) is a **lexical/AST** scanner: its
  findings are **leads** a human must confirm (expect false positives and
  negatives), **not** data-flow proofs of exploitability. A `refuse` means "a
  high/critical-severity lead was found here", not "proven vulnerable".
- **No track record is claimed.** The calibration dimension only runs if the
  project ships a published/source pair to reconcile; it does not assert any
  historical hit-rate.
- Absent gates are `n/a` and are **excluded from the score** — there is no fake
  pass to inflate the level.

## Demo

`demo/run_demo.sh` builds a tiny sample "AI-built app" under `demo/sample_app/`,
runs `verify-suite check` over it end-to-end, and prints the report + the sealed
receipt. See [`demo/README.md`](demo/README.md).

## Layout

```
src/verify_suite/
  core.py       # the dispatch spine (resolve → run → exit-map → score)
  registry.py   # the family as pluggable Dimensions (real CLIs, real subcommands)
  seal.py       # seal the rollup through verity.audit (honest unsealed fallback)
  report.py     # markdown report renderer
  cli.py        # `verify-suite check | dimensions`
tests/          # dispatch / rollup / n-a / seal unit tests (sub-checkers mocked)
demo/           # one end-to-end demo over a sample project
ARCHITECTURE.md # naming + architecture of the verification-layer family
```
