#!/usr/bin/env bash
# End-to-end demo: run the verification-layer spine over the sample AI-built app.
#
# It runs `verify-suite check` over demo/sample_app/ — a tiny real project that
# ships a README (doc claims), a truth.yaml (ground truth), a ```json result-claim,
# a citation, AND a planted vulnerable source file (model_loader.py: torch.load
# without weights_only=True, PLUS a requests.get on a non-literal URL) — so the
# firewall / verity / grounded dimensions AND the aisec-check security dimension all
# actually run. The security dimension flags two leads — unsafe-deserialization and
# the deepened ssrf-url-fetch rule (both high) → a REFUSE verdict, all folded into
# the ONE sealed rollup. Gates that are not installed, and dimensions with no
# matching artifact, report n/a. The aggregate rollup is sealed through verity.audit;
# the demo then re-verifies that chain with verity's OWN verifier.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
APP="$HERE/sample_app"

# prefer the repo venv's console script; fall back to `python -m`.
if [ -x "$ROOT/.venv/bin/verify-suite" ]; then
  VS=("$ROOT/.venv/bin/verify-suite")
  PY="$ROOT/.venv/bin/python"
else
  VS=(python -m verify_suite.cli)
  PY=python
fi

echo "== registered dimensions (and which gates resolve here) =="
"${VS[@]}" dimensions
echo
echo "== check the sample app end-to-end =="
set +e
"${VS[@]}" check "$APP"
CODE=$?
set -e
echo "(exit code: $CODE  — 0 pass · 1 review · 2 refuse)"
echo
echo "== the sealed rollup, re-verified with verity's own audit verifier =="
"$PY" - "$APP/verify-suite-audit.jsonl" <<'PY'
import sys
try:
    from verity.audit import AuditChain
except Exception as e:
    print("verity-core not importable — chain was written unsealed:", e)
    sys.exit(0)
ok, msg = AuditChain(sys.argv[1]).verify()
print("verity chain verify:", ok, "-", msg)
PY
echo
echo "Report:  $APP/verify-suite-report.md"
echo "Receipt: $APP/verify-suite-receipt.json"
