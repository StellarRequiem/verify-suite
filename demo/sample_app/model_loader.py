"""model_loader — deliberately vulnerable, so the demo's security dimension fires.

This file is a PLANTED LEAD for the demo. It carries two distinct, on-purpose
findings so the demo shows aisec-check's breadth (the original unsafe-deser rule
AND one of the deepened lexical/AST rule classes):

  * ``torch.load`` without ``weights_only=True`` — an unsafe-deserialization sink
    (a malicious checkpoint can execute arbitrary code on load). High severity.
  * ``requests.get`` on a NON-LITERAL url — an SSRF lead (if the url is
    externally controlled, a caller can pivot the fetch at internal hosts /
    metadata endpoints). High severity.

Both fold into verify-suite's security dimension, showing the composed spine
catching real vuln classes end-to-end. Do NOT "fix" these — they are the demo's
on-purpose findings. This module is never imported or run by the sample app; it
exists only to be scanned.
"""
from __future__ import annotations


def load_checkpoint(path):
    import torch  # local import: this module is scan-bait, never executed

    # LEAD: torch.load without weights_only=True — untrusted checkpoints can
    # execute arbitrary code during unpickling.
    return torch.load(path)


def fetch_remote_checkpoint(model_url):
    import requests  # local import: scan-bait, never executed

    # LEAD (SSRF): the URL is a non-literal (a parameter), so aisec-check cannot
    # prove it is not attacker-controlled — a fetch that could be pivoted at an
    # internal host or a cloud metadata endpoint.
    return requests.get(model_url).content
