# Architecture & naming — the verification layer

`verify-suite` is the **spine** of a family of independently-shipped checkers.
This document fixes (a) the plain-language product naming and (b) how the spine
composes the members without owning any of their logic.

## Naming — internal tool → plain product surface

External/product materials use plain, capability-first names. The internal tool
name keeps its package identity (so its `project.scripts` entry-point and CI
don't churn); the product name is the external label only.

| Internal package (CLI) | Product-surface name | Capability (true, limited) |
|---|---|---|
| `verify-suite` | **Verification Layer** | the meta-CLI that unifies the family |
| `verity-core` (`verity`) | Claim Verification Gate | statistical soundness of result-claims; the audit-chain seal |
| `firewall` | AI-Output Claim Checker | flags over-claims in AI output vs a declared truth (lexical) |
| `grounded` | Citation Grounding Checker | citations resolve to their cited source (lexical, deterministic) |
| `scorecheck` | Benchmark-Claim Adjudicator | a published benchmark number re-derives from raw logs |
| `groundtruth-bench` | Dataset-Commitment Verifier | a committed dataset's Merkle-style root still matches |
| `calibration-log` | Prediction Calibration Log | published predictions reconciled against source of truth |
| `drift-watch` | Quality-Drift Monitor | early-warning on silent work-quality erosion |
| `scope-gate` | Authorization Scope Gate | a target is inside declared authorized scope |
| `aisec-check` | AI-App Security Linter | lexical/AST leads for AI-app vuln classes (candidate findings, not proofs) |

Naming discipline: no mythology or codenames in external materials; state the real
capability and its limits. The packages themselves are **not renamed** — this is a
documentation layer, not a refactor.

## The composition model

Two composition styles exist in this family:

1. **Import-the-primitive** — tight coupling for sealed verdict logic
   (`scorecheck`, `groundtruth-bench`, `calibration-log` all import `verity.audit`).
2. **Shell-out-to-CLI** — zero-dependency orchestration of independent gate CLIs.

`verify-suite` uses **shell-out** for the gates (so it needs none of them
installed to run, and reports absent ones `n/a`) and **import** for exactly one
thing: the shared seal, `verity.audit`. That is the single cross-repo edge, kept
identical to how the rest of the family seals — one `verity-core` pin, canonical
JSON, float-free, so every receipt in the family cross-verifies.

```
          ┌─────────────────────────── verify-suite (this repo) ───────────────────────────┐
          │  registry.py: family members as Dimensions (real CLI + real subcommand)         │
          │  core.py:  resolve → run(subprocess) → exit-map → score(1–5)                     │
          │  seal.py:  import verity.audit.AuditChain → append rollup (canonical, float-free)│
          └───────────────┬──────────────────────────────────────────────┬──────────────────┘
       shell-out (per gate)│                                              │ import (seal only)
        ┌──────────────────┼───────────────┬──────────┬────────┬───────┐  │
        ▼                  ▼               ▼          ▼        ▼       ▼  ▼
     firewall   verity verify-markdown  grounded  scorecheck …  scope-gate  verity.audit
     (CLI)          (CLI)               (CLI)      (CLI)          (CLI)      (import; the seal)
```

### The dispatch spine (generalized from `shipwright.core`)

`shipwright` proved the subprocess pattern for three gates with a hard-coded
`DIMENSIONS` table and one `run_<dim>` per gate. `verify-suite` generalizes that
into a **registry**: a `Dimension` is data — `(key, label, cli, build_cmd,
exit_map, module?)` — so adding a gate is one registry row, not new dispatch code.

- **`_resolve(cli)`** — co-located venv `bin/` first, then `PATH`. A `module`
  fallback (`python -m <mod>`) covers tools that ship no console script.
- **`build_cmd(bin, root)`** — owns the tool's real sub-command + flags, and
  returns `None` when the project has no artifact of that kind (→ `n/a` for *this*
  project, distinct from the gate being absent).
- **`exit_map(code)`** — the tool's documented exit-code→verdict contract
  (`map_verity` 0/1/2 = pass/warn/refuse · `map_zero_clean` · `map_allow_deny`
  where scope-gate's DENY is a hard refuse · `map_aisec_severity` folds
  aisec-check's worst-severity exit — 0 clean=pass · 1/2 low-medium=warn ·
  3/4 high-critical=refuse).
- **`score(results)`** — `round(1 + 4 × passed/applicable)` over only the
  dimensions that *applied*. Absent gates and no-artifact gates are `n/a` and are
  never counted, so the level can never be inflated by a fake pass.

### The seal

`seal.py` imports `verity.audit.AuditChain` and appends the rollup as one entry.
The payload is built canonical (sorted keys) and **float-free** — the reliability
level is an int and the fraction is stored as the integer pair `passed` /
`applicable` — so two runs on the same inputs seal to byte-identical payloads.
Unkeyed sealing gives **integrity** (corruption / reorder / truncation), not
tamper-evidence; key or anchor the head for the stronger property. If
`verity-core` is not importable, the receipt is written **unsealed and flagged**.

## What the spine deliberately does NOT do

- It does not re-implement, wrap-and-modify, or vendor any checker's logic.
- It does not fork the hash chain — one `verity-core`, imported.
- It does not claim semantic grounding (the lexical checkers do not do that) and
  it does not claim any historical track record.
- It does not claim the **security** dimension proves exploitability. `aisec-check`
  is a lexical/AST scanner: every finding is a **lead** a human must confirm (false
  positives and negatives expected), not a data-flow proof. A `refuse` here means
  "a high/critical-severity lead was found — look here", not "proven vulnerable".
