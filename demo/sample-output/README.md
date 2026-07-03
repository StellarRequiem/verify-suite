# Sample sealed output — one unified, re-verifiable receipt

These three files are a **committed sample** of what `verify-suite check` writes.
They were produced by the real pipeline over [`../sample_app/`](../sample_app) — a
tiny "AI-built app" that ships doc claims, a result-claim, a citation, and a
planted vulnerable source file — so a single run exercises the **doc-claim**,
**result-claim**, **citation**, and **security** dimensions and folds all of them
into **one sealed rollup**.

| File | What it is |
|---|---|
| `verify-suite-report.md` | the human-readable rollup (per-dimension verdicts + the 1–5 level) |
| `verify-suite-receipt.json` | the machine receipt: the canonical, float-free payload + the seal (`entry_hash`, `chain_head`) |
| `verify-suite-audit.jsonl` | the append-only `verity.audit` chain the rollup was sealed into |

The paths inside these samples are redacted to the relative label `sample_app`
(the live run embeds the absolute project path, which is why the live outputs are
gitignored). The redaction is applied to the sealed payload itself, so the receipt
below still re-derives byte-for-byte.

## This run at a glance

**Level 3 / 5** · 2 of **4 applicable** dimensions passed · **5 n/a** · worst verdict **REFUSE**.

- `firewall` (doc over-claims) → **PASS**
- `grounded` (citation grounding) → **PASS**
- `verity` (result-claim hygiene) → **REVIEW**
- `aisec-check` (AI-app security leads) → **REFUSE** — the planted `torch.load`
  unsafe-deserialization **lead** (high severity). This is a *lead a human must
  confirm*, not a proof of exploitability.
- `scorecheck` · `groundtruth` · `calibration-log` · `drift-watch` · `scope-gate`
  → **n/a** — the sample ships no matching artifact for these, so they are
  excluded from the score (never a fake pass).

## Re-verify it yourself (nothing to trust)

The seal is `verity.audit`'s unkeyed hash chain. Anyone can re-derive it:

```sh
# 1) the chain is internally intact (corruption / reorder / truncation would fail)
python - <<'PY'
from verity.audit import AuditChain
ok, msg = AuditChain("verify-suite-audit.jsonl").verify()
print("chain verify:", ok, "-", msg)          # -> True - intact: 1 entries
PY

# 2) the receipt's entry_hash matches the committed chain entry, and the
#    receipt payload IS the sealed event_data — byte-for-byte
python - <<'PY'
import json
line    = json.loads(open("verify-suite-audit.jsonl").read().strip())
receipt = json.load(open("verify-suite-receipt.json"))
print("hash match   :", line["entry_hash"] == receipt["entry_hash"])
print("payload match:", line["event_data"] == receipt["payload"])
PY
```

## Honest scope (same as the top-level README)

- The level is a rollup of **deterministic gate verdicts**, not a proof of
  reliability. `3/5` means "these applicable gates said this", not "provably 60%
  reliable".
- The **security** verdict is a **lexical/AST lead**, not a data-flow proof of
  exploitability. Expect false positives and negatives.
- The seal is **unkeyed** = integrity (catches accidental corruption), **not**
  tamper-evidence against a forger who rewrites the file and recomputes the root.
- **No track record is claimed.** `n/a` dimensions are honestly excluded.
