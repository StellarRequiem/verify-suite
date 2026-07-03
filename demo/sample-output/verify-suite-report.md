# Verification-layer report — sample_app

**Unified reliability level: 3 / 5**  ·  2 of 4 applicable dimensions passed  ·  5 n/a  ·  worst verdict: REFUSE

## Dimensions

| Dimension | Verdict | Powered by | Note |
|---|---|---|---|
| Doc/output over-claims | PASS | `firewall` |  |
| Result-claim hygiene | REVIEW | `verity` |  |
| Citation grounding | PASS | `grounded` |  |
| Benchmark-claim receipt | n/a | `scorecheck` | no matching artifact in this project |
| Dataset commitment | n/a | `groundtruth` | no matching artifact in this project |
| Prediction calibration | n/a | `calibration-log` | no matching artifact in this project |
| Quality drift | n/a | `drift-watch` | no matching artifact in this project |
| Authorization scope | n/a | `scope-gate` | no matching artifact in this project |
| AI-app security leads | REFUSE | `aisec-check` |  |

## What to look at next

- **Result-claim hygiene** → REVIEW — verity verify-markdown — 1 claim(s) in sample_app/README.md:
- **AI-app security leads** → REFUSE — [    high] unsafe-deserialization     model_loader.py:26  Unsafe deserialization via torch.load()

## Aggregate receipt (sealed through verity.audit)

- sealed: **yes** · chain `sample_app/verify-suite-audit.jsonl`
- seq 0 · entry_hash `599337be0c7735721781619c42ff4cbfa070fc2a5b267ab4fa787e558f23d15d`
- chain head `599337be0c7735721781619c42ff4cbfa070fc2a5b267ab4fa787e558f23d15d`

> Re-verify the chain with verity's own audit verifier. Unkeyed = integrity (catches corruption/reorder/truncation); add a key or anchor the head for tamper-evidence.

## How the level is computed (inspect it)
Level = round(1 + 4 × passed / applicable), over only the dimensions that *apply* (a gate that isn't installed, or one with no matching artifact in this project, is `n/a` and is never counted — there is no fake pass). 5/5 = every applicable dimension is green.

## Honest scope
verify-suite ORCHESTRATES existing checkers; it re-implements none of them. It reports what each present gate says and marks absent gates n/a. The underlying checkers (firewall / grounded) are lexical/deterministic — this is not semantic grounding. No track record is claimed.
