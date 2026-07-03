"""verify-suite — one spine for the verification-layer family.

A meta-CLI that dispatches to each shipped checker (firewall, verity, grounded,
scorecheck, groundtruth, calibration-log, drift-watch, scope-gate) as a pluggable
dimension, reports every present gate's verdict (absent gates = n/a), rolls up a
transparent 1-5 reliability level, and seals the aggregate through verity's audit
chain. It re-implements NONE of the checkers — it only orchestrates them.
"""
__version__ = "0.1.0"
