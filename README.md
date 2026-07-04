# verify-suite — a reference implementation for adjudicating AI-build claims

> **A reference implementation of how I mechanically adjudicate what an AI build
> *claims* against what it *ships*** — its result-claims, its benchmark scores, its
> docs and citations, and its **security** — sealing every verdict into one receipt
> anyone can re-derive. It is a working demonstration of the method and its limits,
> not a product with users: one CLI that composes existing checkers into a single
> pass over a repository.

> **Status / maturity.** Early reference implementation. It *composes* existing,
> individually-tested checkers behind a dispatch spine — it re-implements none of
> them — and its end-to-end demo runs over a deliberately-planted sample app, not a
> real-world catch. There are **no external users yet**, and validation against
> real-world third-party codebases is explicit future work. The point it makes today
> is about the *mechanism* — how claims get adjudicated and sealed — not a track
> record.

## The problem

When software is built by an AI, the artifacts that vouch for it are *also* written
by the AI: the README's "we measured 82% accuracy", the benchmark number in the
changelog, the citation behind a claim, the "no known vulnerabilities" note. In 2026
those self-reports are routinely wrong or gamed — benchmark scores swing 10–30 points
across harnesses and selective submission inflates them, doc claims drift from what
the code does, citations don't resolve, and **security review is the leg that most
often ships unchecked**. The checks that would catch each of these exist as separate
tools — but nothing runs them together and puts their verdicts on the record.

`verify-suite` is that spine. It **orchestrates existing checkers** — it
re-implements none of them — dispatching to each shipped checker as a pluggable
*dimension*, reporting every present gate's verdict (absent gates report `n/a`,
never a fake pass), rolling up a transparent **1–5 reliability level**, and sealing
the aggregate through one audit chain.

## The composition — spine + nine dimensions

```
                        ┌───────────────────────────────┐
                        │   verify-suite  (the spine)    │
                        │  registry → dispatch → 1–5     │
                        │  rollup → ONE sealed receipt   │
                        └───────────────┬───────────────┘
   shell-out to each checker's own CLI  │  (import only for the shared seal)
   ┌───────────┬───────────┬────────────┼───────────┬───────────┬───────────┐
   ▼           ▼           ▼            ▼           ▼           ▼           ▼
 firewall   verity     grounded    scorecheck  groundtruth  calibration  drift-watch
 doc-claims result-    citation    benchmark-  dataset-     -log         quality-
            claim      grounding   claim        commitment  prediction   drift
            hygiene                receipt                   calibration
                                    scope-gate ──► authorization scope
                                    aisec-check ─► AI-app SECURITY leads
                                          │
                                          ▼  (import, not re-implemented)
                                    verity.audit.AuditChain — the shared seal
```

| Dimension | Powered by (real tool) | What it adjudicates |
|---|---|---|
| Doc/output over-claims | **`firewall`** | README/doc claims vs a declared `truth.yaml` |
| Result-claim hygiene | **`verity`** | statistical soundness of result-claims in markdown |
| Citation grounding | **`grounded`** | citations resolve to the source they cite |
| Benchmark-claim receipt | **`scorecheck`** | a published benchmark number re-derives from raw logs |
| Dataset commitment | **`groundtruth`** | a committed dataset's root still matches |
| Prediction calibration | **`calibration-log`** | published predictions vs their source of truth |
| Quality drift | **`drift-watch`** | silent quality-signal erosion |
| Authorization scope | **`scope-gate`** | a target is inside declared authorized scope |
| AI-app security leads | **`aisec-check`** | lexical/AST leads for AI-app vuln classes (candidates, not proofs) |

## Run it

```sh
verify-suite dimensions          # list the 9 dimensions + which gates resolve here
verify-suite check <path>        # run every dimension, write report + ONE sealed receipt
```

`check` writes `verify-suite-report.md`, `verify-suite-receipt.json`, and appends
the rollup to `verify-suite-audit.jsonl`. Exit code is CI-gateable:
`0` = pass (or nothing applicable) · `1` = review · `2` = refuse.

## The unified sealed receipt

Every run folds all applicable dimensions — claims, docs, citations, **and
security** — into **one** canonical, float-free receipt sealed through
`verity.audit`. A committed, path-redacted sample is in
[`demo/sample-output/`](demo/sample-output/) and re-verifies offline. Its core:

```jsonc
// verify-suite-receipt.json  (abridged — see demo/sample-output/ for the full file)
{
  "payload": {
    "tool": "verify-suite", "root": "sample_app",
    "level": 3, "passed": 2, "applicable": 4, "na": 5, "worst": "refuse",
    "dimensions": [
      { "key": "docs_claims",  "cli": "firewall",    "status": "pass" },
      { "key": "citations",    "cli": "grounded",    "status": "pass" },
      { "key": "result_claims","cli": "verity",      "status": "warn" },
      { "key": "security",     "cli": "aisec-check", "status": "refuse", "exit_code": 3 },
      { "key": "benchmark_receipt", "cli": "scorecheck", "status": "na" }
      // …calibration / groundtruth / drift / scope also n/a — no matching artifact
    ]
  },
  "sealed": true,
  "entry_hash": "599337be0c7735721781619c42ff4cbfa070fc2a5b267ab4fa787e558f23d15d",
  "chain_head": "599337be0c7735721781619c42ff4cbfa070fc2a5b267ab4fa787e558f23d15d"
}
```

Re-derive it with `verity`'s own verifier — the receipt's `entry_hash` falls out of
the committed payload and the chain verifies `intact` (see
[`demo/sample-output/README.md`](demo/sample-output/README.md)). Nothing to trust.

---

**One spine for a family of verification checkers — a reference implementation, not
a product to adopt.** The rest of this document is the reference: what each dimension
composes, the seal, install, and — read it — the honest scope.

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
python3.12 -m venv .venv     # 3.12 — see the version note below
.venv/bin/python -m pip install -e ".[dev]"
```

The family checkers are separate packages. Install whichever you want active into
the **same venv** (so their console scripts co-locate with `verify-suite`); any you
skip will report `n/a`. `verity-core` supplies the seal.

> **Python version.** verify-suite itself runs on `>=3.9`, but two family checkers
> — `scorecheck` and `groundtruth` — pin `>=3.12,<3.13`. Build the venv on **3.12**
> so every dimension can resolve; on a newer interpreter those two simply report
> `n/a` (not installable), which is honest but drops two gates. The checkers pin
> their shared deps (`verity-core`, `grounded-check`, `calibration-log`) as direct
> git refs, so if you install from local editable clones, install `verity-core`
> first, then the leaves with `--no-deps` to avoid a redundant re-fetch.

## Use

```sh
verify-suite dimensions          # list dimensions + which gates resolve here
verify-suite check <repo>        # run all dimensions, write report + sealed receipt
```

`check` writes `verify-suite-report.md`, `verify-suite-receipt.json`, and appends
the rollup to `verify-suite-audit.jsonl`. Exit code is CI-gateable:
`0` = pass (or nothing applicable) · `1` = review · `2` = refuse.

## Honest scope — read this

Every line below is a limit, stated plainly so the pitch above can't be misread.

- **It orchestrates; it does not verify anything itself.** A `5/5` means *these
  specific deterministic gates that applied all passed* — not "provably reliable".
  The level is a rollup of gate verdicts, not a reliability guarantee.
- **The security dimension emits LEADS, not proofs.** `aisec-check` is a
  **lexical/AST** scanner: it matches syntactic shapes, not data flow or
  reachability. Every finding is a **candidate a human must confirm** — expect
  false positives *and* false negatives. A `refuse` means "a high/critical-severity
  lead was found here — look", **not** "proven exploitable".
- **The underlying claim/citation checkers are lexical/deterministic.** `firewall`
  and `grounded` match terms and resolve references syntactically. This is **not**
  semantic grounding.
- **The seal is unkeyed = integrity, not tamper-evidence.** The audit chain catches
  accidental corruption, reordering, and truncation. It does **not** stop a
  determined forger who controls the receipt file and recomputes the root — that
  needs a held key or an anchored/published chain head.
- **`n/a` when a project ships no matching artifact.** A dimension only runs when
  the project provides the input it checks (a receipt, a committed dataset, a
  reconcile pair, a drift store, a scope target, source to scan). A gate that isn't
  installed is `n/a` too. Both are **excluded from the score** — there is no fake
  pass to inflate the level.
- **No track record is claimed.** verify-suite ships no benchmark corpus and asserts
  no historical hit-rate. The calibration dimension only reconciles a
  published/source pair *if the project provides one*; it does not assert any
  standing accuracy of its own.

## Demo

`demo/run_demo.sh` builds a tiny sample "AI-built app" under `demo/sample_app/`,
runs `verify-suite check` over it end-to-end, and prints the report + the sealed
receipt. See [`demo/README.md`](demo/README.md).

> **The demo is a deliberately-planted reference sample, not a real-world catch.**
> `demo/sample_app/` is authored to contain exactly the artifacts the dimensions
> check — including a planted vulnerable source file — so the run *illustrates the
> mechanism* end-to-end. It is not evidence that the suite has found real-world bugs;
> real-world-code validation is future work (see the Status note at the top).

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
