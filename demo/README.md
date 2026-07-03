# Demo — the spine, end-to-end

`run_demo.sh` runs `verify-suite check` over `sample_app/`, a tiny real
"AI-built app" (TaskSorter — a deterministic to-do ranker). The sample ships the
artifacts each text-level dimension needs, so the run exercises real gates:

- `README.md` + `truth.yaml` → the **Doc/output over-claims** dimension (`firewall`)
- a ```` ```json ```` result-claim block in the README → **Result-claim hygiene** (`verity`)
- a citation `[1]` → **Citation grounding** (`grounded`)

Run it:

```sh
./demo/run_demo.sh
```

## What you'll see (honest, environment-dependent)

- The gates that are **installed in this venv** run and return a verdict; the
  rest report **`n/a`** — never a fake pass.
- Dimensions whose *input artifact* isn't present in the sample (a benchmark
  receipt, a committed dataset, a reconcile pair, a drift store, a scope target)
  also report **`n/a`** — "no matching artifact in this project", distinct from
  "gate not installed".
- The rollup is a **1–5 level over only the applicable dimensions**, sealed
  through `verity.audit`. The demo then re-verifies that chain with **verity's own
  audit verifier** to show the seal is real, not decorative.

A representative run on Python 3.14 (scorecheck / groundtruth pin `<3.13`, so they
are honestly `n/a` here): 3 applicable dimensions, 2 pass + 1 review →
**level 4/5**, sealed, chain `verify` returns `intact`.

The `verify-suite check` outputs (`verify-suite-report.md`,
`verify-suite-receipt.json`, `verify-suite-audit.jsonl`) are written into
`sample_app/` at run time and are gitignored.
