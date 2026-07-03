"""Unit tests for the dispatch / rollup / n-a logic.

These mock the sub-checkers (subprocess + resolution) so the suite is testable
without every family gate installed — exactly the property the meta-CLI needs.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verify_suite import core
from verify_suite.core import (
    Dimension,
    DimensionResult,
    Verdict,
    map_allow_deny,
    map_verity,
    map_zero_clean,
    run_check,
    run_dimension,
    score,
)


# ── exit-code maps ────────────────────────────────────────────────────────────
def test_map_verity():
    assert map_verity(0) == "pass"
    assert map_verity(1) == "warn"
    assert map_verity(2) == "refuse"
    assert map_verity(7) == "warn"      # unknown non-zero -> warn
    assert map_verity(-1) == "error"    # our run-failure sentinel


def test_map_zero_clean():
    assert map_zero_clean(0) == "pass"
    assert map_zero_clean(1) == "warn"
    assert map_zero_clean(-1) == "error"


def test_map_allow_deny():
    assert map_allow_deny(0) == "pass"
    assert map_allow_deny(1) == "refuse"   # a DENY is a hard refuse, not a warn
    assert map_allow_deny(-1) == "error"


# ── dimension helpers ─────────────────────────────────────────────────────────
def _dim(key="d", cli="faketool", build=None, exit_map=map_zero_clean, module=None):
    return Dimension(key, key.title(), cli,
                     build or (lambda b, r: ["run"]), exit_map, module=module)


def test_absent_gate_is_na(monkeypatch, tmp_path):
    # resolution fails => available False => status na, not counted
    monkeypatch.setattr(core, "resolve_dimension", lambda d: None)
    r = run_dimension(_dim(), tmp_path)
    assert r.available is False
    assert r.status == "na"
    assert r.applicable is False


def test_installed_but_no_artifact_is_na(monkeypatch, tmp_path):
    # gate resolves, but build_cmd returns None => nothing to run here => na
    monkeypatch.setattr(core, "resolve_dimension", lambda d: ["/bin/faketool"])
    r = run_dimension(_dim(build=lambda b, root: None), tmp_path)
    assert r.available is True
    assert r.applicable_here is False
    assert r.status == "na"
    assert r.applicable is False


def test_dispatch_maps_exit_to_verdict(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "resolve_dimension", lambda d: ["/bin/faketool"])
    monkeypatch.setattr(core, "_run", lambda cmd, timeout=120: (2, "REFUSE: boom"))
    r = run_dimension(_dim(exit_map=map_verity), tmp_path)
    assert r.available is True
    assert r.status == "refuse"
    assert r.verdict.exit_code == 2
    assert "boom" in r.verdict.detail


def test_dispatch_passes_leading_bin_plus_tail(monkeypatch, tmp_path):
    captured = {}

    def fake_run(cmd, timeout=120):
        captured["cmd"] = cmd
        return 0, "ok"

    monkeypatch.setattr(core, "resolve_dimension", lambda d: ["/bin/faketool"])
    monkeypatch.setattr(core, "_run", fake_run)
    r = run_dimension(_dim(build=lambda b, root: ["verify", "--x", "y"]), tmp_path)
    assert captured["cmd"] == ["/bin/faketool", "verify", "--x", "y"]
    assert r.status == "pass"


def test_cmd_builder_error_becomes_error_verdict(monkeypatch, tmp_path):
    def boom(b, root):
        raise RuntimeError("bad builder")

    monkeypatch.setattr(core, "resolve_dimension", lambda d: ["/bin/faketool"])
    r = run_dimension(_dim(build=boom), tmp_path)
    assert r.status == "error"
    assert "bad builder" in r.verdict.detail


def test_run_swallows_subprocess_failure(monkeypatch, tmp_path):
    # a raising subprocess must fold into rc=-1 (error), never crash the spine
    def raising(*a, **k):
        raise OSError("no such binary")

    monkeypatch.setattr(core.subprocess, "run", raising)
    monkeypatch.setattr(core, "resolve_dimension", lambda d: ["/bin/faketool"])
    r = run_dimension(_dim(), tmp_path)
    assert r.status == "error"


# ── the 1-5 rollup ────────────────────────────────────────────────────────────
def _result(status, available=True, applicable_here=True):
    v = None
    if available and applicable_here and status not in ("na",):
        v = Verdict("k", status, "", 0, "")
    return DimensionResult("k", "K", "cli", available=available,
                           verdict=v, applicable_here=applicable_here)


def test_score_all_pass_is_5():
    res = [_result("pass"), _result("pass"), _result("pass")]
    s = score(res)
    assert s["level"] == 5
    assert s["passed"] == 3
    assert s["applicable"] == 3
    assert s["worst"] == "pass"


def test_score_all_fail_is_1():
    res = [_result("refuse"), _result("warn")]
    s = score(res)
    assert s["level"] == 1
    assert s["passed"] == 0
    assert s["worst"] == "refuse"


def test_score_half_pass_is_3():
    res = [_result("pass"), _result("pass"), _result("warn"), _result("warn")]
    s = score(res)
    # 1 + 4*0.5 = 3
    assert s["level"] == 3


def test_na_dimensions_never_counted():
    # two absent gates + one no-artifact gate must NOT dilute or inflate the score
    res = [
        _result("pass"),
        _result("na", available=False),                 # gate not installed
        _result("na", available=True, applicable_here=False),  # no artifact
    ]
    s = score(res)
    assert s["applicable"] == 1     # only the real pass counts
    assert s["passed"] == 1
    assert s["na"] == 2
    assert s["level"] == 5          # 1 of 1 applicable passed => full marks, no fake pass


def test_score_nothing_applicable_is_none():
    res = [_result("na", available=False), _result("na", available=False)]
    s = score(res)
    assert s["level"] is None
    assert s["applicable"] == 0
    assert "note" in s


def test_run_check_runs_every_registered_dimension(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "resolve_dimension", lambda d: ["/bin/x"])
    monkeypatch.setattr(core, "_run", lambda cmd, timeout=120: (0, "ok"))
    dims = [_dim(key="a"), _dim(key="b"), _dim(key="c")]
    results = run_check(tmp_path, dims)
    assert [r.key for r in results] == ["a", "b", "c"]
    assert all(r.status == "pass" for r in results)


def test_module_fallback_used_when_no_console_script(monkeypatch):
    # console script missing, but module importable => module fallback invocation
    monkeypatch.setattr(core, "_resolve", lambda cli: None)
    import importlib.util
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    lead = core.resolve_dimension(_dim(cli="nope", module="os"))
    assert lead is not None
    assert lead[1:] == ["-m", "os"]


def test_module_fallback_skipped_when_module_absent(monkeypatch):
    monkeypatch.setattr(core, "_resolve", lambda cli: None)
    import importlib.util
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert core.resolve_dimension(_dim(cli="nope", module="totally_absent_mod")) is None
