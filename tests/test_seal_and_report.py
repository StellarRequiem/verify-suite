"""Tests for the sealing seam and the report renderer.

Sealing is exercised both with a stubbed verity.audit (sealed path) and with it
forced-absent (honest unsealed fallback) — so the test does not require the
local-only verity-core to be installed.
"""
from __future__ import annotations

import builtins
import json
import sys
import types

from verify_suite import seal
from verify_suite.core import DimensionResult, Verdict
from verify_suite.report import render_markdown
from verify_suite.seal import _payload, seal_rollup


def _res(key, status, available=True, applicable_here=True, code=0):
    v = None
    if available and applicable_here and status != "na":
        v = Verdict(key, status, "detail line", code, "cmd")
    return DimensionResult(key, key.title(), key, available=available,
                           verdict=v, applicable_here=applicable_here)


def _sample():
    results = [
        _res("docs_claims", "pass"),
        _res("citations", "na", available=False),
        _res("scope", "refuse", code=1),
    ]
    scored = {"level": 3, "passed": 1, "applicable": 2, "na": 1, "worst": "refuse"}
    return results, scored


# ── payload is canonical + float-free ─────────────────────────────────────────
def test_payload_is_float_free_and_sorted():
    results, scored = _sample()
    p = _payload("/proj", results, scored)
    # no floats anywhere
    def _no_floats(o):
        if isinstance(o, float):
            raise AssertionError("float found in payload")
        if isinstance(o, dict):
            for v in o.values():
                _no_floats(v)
        if isinstance(o, list):
            for v in o:
                _no_floats(v)
    _no_floats(p)
    # dimensions sorted by key for canonical ordering
    keys = [d["key"] for d in p["dimensions"]]
    assert keys == sorted(keys)
    assert p["level"] == 3
    assert p["worst"] == "refuse"


# ── sealed path (stub verity.audit) ───────────────────────────────────────────
def test_seal_rollup_seals_when_verity_present(monkeypatch, tmp_path):
    appended = {}

    class FakeChain:
        def __init__(self, path):
            self.path = path

        def append(self, event_type, event_data, actor="agent"):
            appended["event_type"] = event_type
            appended["data"] = event_data
            return {"seq": 0, "prev_hash": "GENESIS", "entry_hash": "abc123"}

        def head(self):
            return "abc123"

    fake_mod = types.ModuleType("verity.audit")
    fake_mod.AuditChain = FakeChain
    fake_pkg = types.ModuleType("verity")
    monkeypatch.setitem(sys.modules, "verity", fake_pkg)
    monkeypatch.setitem(sys.modules, "verity.audit", fake_mod)

    results, scored = _sample()
    receipt = seal_rollup("/proj", results, scored, tmp_path / "chain.jsonl")
    assert receipt["sealed"] is True
    assert receipt["entry_hash"] == "abc123"
    assert receipt["chain_head"] == "abc123"
    assert appended["event_type"] == "verify_suite.rollup"


# ── unsealed fallback (verity absent) ─────────────────────────────────────────
def test_seal_rollup_falls_back_when_verity_absent(monkeypatch, tmp_path):
    # force the import to fail
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "verity.audit" or name.startswith("verity"):
            raise ImportError("no verity here")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    results, scored = _sample()
    receipt = seal_rollup("/proj", results, scored, tmp_path / "chain.jsonl")
    assert receipt["sealed"] is False
    assert "seal_reason" in receipt
    # payload is still present — honest unsealed, not dropped
    assert receipt["payload"]["level"] == 3


# ── report renders n/a + seal status honestly ─────────────────────────────────
def test_report_marks_absent_gate_na_and_shows_seal():
    results, scored = _sample()
    receipt = {"sealed": True, "chain_path": "/c", "seq": 0,
               "entry_hash": "abc", "chain_head": "abc"}
    md = render_markdown(results, scored, "/proj", receipt)
    assert "Unified reliability level: 3 / 5" in md
    assert "n/a" in md
    assert "gate not installed" in md
    assert "sealed through verity.audit" in md
    assert "sealed: **yes**" in md


def test_report_shows_unsealed_reason():
    results, scored = _sample()
    receipt = {"sealed": False, "seal_reason": "verity-core not importable"}
    md = render_markdown(results, scored, "/proj", receipt)
    assert "sealed: **no**" in md
    assert "verity-core not importable" in md
