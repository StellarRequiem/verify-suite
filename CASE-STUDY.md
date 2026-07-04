# Adjudicating what an AI build claims — a reference implementation

*A case study in the method: how I mechanically adjudicate what an AI build claims
against what it ships. This documents an early reference implementation and its
stated limits — not a product with users.*

## The problem

AI now writes a large share of the software that reaches production, and it is
fluent in a specific failure mode: it ships **claims**, not always the thing the
claim describes. A README asserts a feature is "fully tested." A benchmark score
appears in a table with no receipt behind it. A citation is offered for a fact
that the cited source never states. A security-sensitive call is left untested
because the model asserted it was safe. Each of these reads as done. None of them
is self-evidently true, and a human reviewer has no cheap way to tell the sound
claims from the confident ones. The gap between *what a build says* and *what a
build actually did* is where AI-built software quietly breaks — and it is exactly
the seam that ordinary CI (which runs the tests the model chose to write) does not
cover.

## The thesis

Treat verification as its own layer. Not "run the tests," but: **mechanically
adjudicate what the build claims against what it shipped**, across the dimensions
where AI output tends to drift — doc/output over-claims, result-claim hygiene,
citation grounding, benchmark receipts, dataset commitment, calibration, quality
drift, authorization scope, and security. Each dimension renders a verdict from
the artifacts actually present in the repository, and every verdict is **sealed**
so a third party can re-derive it rather than take it on faith. The operating rule
is deliberately blunt: *verified, or it does not ship.*

Crucially, this is a **composition, not a rewrite**. Each dimension delegates to a
tool that already exists and does one job — the suite is the spine that runs them
together and folds their verdicts into a single sealed rollup. It re-implements
none of them.

## The mechanism, demonstrated

One command runs the full battery over a project and produces one re-derivable,
sealed receipt. What follows is **not** a real-world catch — it is the mechanism run
against a deliberately-planted reference sample. The bundled sample app is a small
project authored to ship exactly what the dimensions check: a README, a ground-truth
file, a JSON result-claim, a citation, and a planted vulnerable source file. So the
run below shows *how* adjudication and sealing work end-to-end, not that the suite has
found bugs in the wild (that validation is future work — see the honest scope):

```
Unified reliability level: 3/5 · 2/4 applicable dimensions passed · 5 n/a · worst: refuse
Receipt: .../verify-suite-receipt.json (sealed: True)
(exit code: 2  — 0 pass · 1 review · 2 refuse)
```

Five dimensions report **n/a** because the sample ships no matching artifact — no
fake passes are manufactured to pad the score. The security dimension flags two
leads and returns a **refuse** verdict, which drives the aggregate. And the sealed
rollup re-verifies through the sealing tool's *own* independent audit verifier:

```
verity chain verify: True - intact
```

(The audit chain is append-only, so its entry count grows with each demo run;
what is stable and reproducible is the verdict — `True`, `intact`.) That line is
the point: the verdict is not something you trust because the suite said so; it is
something anyone can re-derive from the receipt.

### What's actually behind it (composed, not re-built)

| Piece | Role |
|---|---|
| **verify-suite** | The spine — runs the dimensions and folds verdicts into one rollup. 9 dimensions installed; 30 tests passing. |
| **aisec-check** | The security dimension — a read-only lexical/AST **lead-generator** for vulnerability classes recurring in AI-built apps (leads, not proofs; ~3–4% measured precision on real code — a human confirms each). 56 tests passing. |
| **scorecheck** | The benchmark-receipt dimension — checks that a reported benchmark score has a receipt behind it. 21 tests passing. |
| **verity** | The sealing substrate — one pinned audit chain the rollup seals through, and the independent verifier that re-derives it. |

## Honest scope — where this is early

This is a first-cut composition of existing, individually tested tools. It runs
**locally** and is not a hosted product. Three limits are load-bearing and stated
up front, not buried:

- **Security findings are leads, not proofs — it is a lead-generator, not a
  precision gate.** aisec-check is a lexical/AST first pass. It tells a reviewer
  *where to look* — expect false positives and false negatives. On a real
  benchmark (59 public AI repos, 2026-07-04) its adjudicated precision measured
  **~3–4%** (6 true positives in 140 sampled leads); only `unsafe-deserialization`
  and `path-traversal` carried reliable signal, the rest was shape-only noise. A
  `refuse` here means "high/critical-severity leads were found — a human should
  look", **not** "proven exploitable". It is a triage aid within the layer, not a
  standalone precision gate.
- **The seal is unkeyed = integrity, not tamper-evidence.** The audit chain
  catches corruption, reordering, and truncation of the receipt. It is *not*
  tamper-evidence on its own; that requires a key or an anchored chain head. (This
  is the one place the word "tamper" appears, and it appears to disclaim it.)
- **n/a is a real verdict.** A dimension with no matching artifact reports n/a and
  is excluded from the applicable count — the suite never invents a pass.

Within those limits, the claim is modest and checkable: given a project's actual
artifacts, this layer renders a verdict per dimension and seals the rollup so the
verdict can be re-derived. That is the unit of trust it is built to produce.

---

*All figures above were produced by running the tools this session; the receipt
and its re-verification are reproducible from the commands in the repository's
demo.*
