"""model_loader — deliberately vulnerable, so the demo's security dimension fires.

This file is a PLANTED LEAD for the demo: ``torch.load`` without
``weights_only=True`` is an unsafe-deserialization sink (a malicious checkpoint
can execute arbitrary code on load). aisec-check flags it as a high-severity
lead, which folds to a REFUSE verdict in verify-suite's security dimension —
showing the composed spine actually catching a real vuln class end-to-end.

Do NOT "fix" this — it is the demo's on-purpose finding. It is never imported or
run by the sample app; it exists only to be scanned.
"""
from __future__ import annotations


def load_checkpoint(path):
    import torch  # local import: this module is scan-bait, never executed

    # LEAD: torch.load without weights_only=True — untrusted checkpoints can
    # execute arbitrary code during unpickling.
    return torch.load(path)
