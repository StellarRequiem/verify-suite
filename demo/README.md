# Demo — the spine, end-to-end

`run_demo.sh` runs `verify-suite check` over `sample_app/`, a tiny real
"AI-built app" (TaskSorter — a deterministic to-do ranker). The sample ships the
artifacts each text-level dimension needs, so the run exercises real gates:

- `README.md` + `truth.yaml` → the **Doc/output over-claims** dimension (`firewall`)
- a ```` ```json ```` result-claim block in the README → **Result-claim hygiene** (`verity`)
- a citation `[1]` → **Citation grounding** (`grounded`)
- a planted vulnerable source file `model_loader.py` (`torch.load` without
  `weights_only=True`) → the **AI-app security leads** dimension (`aisec-check`),
  which flags the unsafe-deserialization lead (high severity) as **REFUSE**

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

A representative run **on a Python 3.12 venv with all nine family checkers
installed** (so every gate resolves — see `verify-suite dimensions`): the sample
ships only doc/citation/result-claim/security-relevant artifacts, so **4
dimensions are applicable** and the other **5 report `n/a` — "no matching artifact
in this project"** (not "gate not installed"). Of the 4 applicable: 2 pass
(`firewall`, `grounded`) + 1 review (`verity`) + 1 refuse (the planted
`aisec-check` security lead) → **level 3/5**, worst verdict REFUSE, sealed, chain
`verify` returns `intact: … entries`. Security is a full member of the ONE sealed
rollup — not a separate scan.

> On a **newer interpreter** (≥3.13), two checkers — `scorecheck` and
> `groundtruth` — pin `<3.13` and will not install, so they instead report `n/a`
> as *gate-not-installed*. Either way they are `n/a` here (the sample ships no
> receipt/dataset for them), the applicable set is unchanged, and the level is the
> same — the point of `n/a` is that it never inflates the score.

The `verify-suite check` outputs (`verify-suite-report.md`,
`verify-suite-receipt.json`, `verify-suite-audit.jsonl`) are written into
`sample_app/` at run time and are **gitignored**. A **committed, path-redacted
sample** of exactly these three files lives in
[`sample-output/`](./sample-output/) — re-verifiable offline.
