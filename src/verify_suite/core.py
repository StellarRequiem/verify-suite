"""verify_suite.core — the dispatch spine.

This generalizes the subprocess-composition pattern proven in ``shipwright.core``
(``_resolve`` -> ``_run`` -> ``_status_from_exit``, plus ``run_check`` / ``score``)
into a *registry-driven* meta-dispatcher: each member of the verification-layer
family is registered as a pluggable ``Dimension`` that shells out to that tool's
existing CLI. verify-suite re-implements NONE of the checkers' logic — it only
resolves, runs, maps the exit code to a verdict, and rolls the verdicts up.

Design invariants (inherited from shipwright, kept honest):

* **Subprocess, never re-vendor.** Every dimension shells the shipped CLI.
* **Absent gate => n/a, never a fake pass.** A tool that does not resolve on the
  PATH / co-located venv is reported ``na`` and is excluded from the score.
* **Exit code is the verdict.** Each family CLI already documents an
  exit-code-as-verdict contract; the registry records how to map it.
* **A gate failure never crashes the spine.** ``_run`` swallows every error into
  an ``error`` verdict.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# worst-wins ordering over the verdict ladder; na/error sit outside it.
_RANK = {"pass": 0, "warn": 1, "refuse": 2}


@dataclass(frozen=True)
class Dimension:
    """One pluggable member of the verification family.

    ``key``       stable id (used in receipts + the registry).
    ``label``     plain-language name for reports.
    ``cli``       the console-script name to resolve (e.g. ``"verity"``).
    ``build_cmd`` (resolved_bin, project_root) -> argv list. Owns the tool's
                  own sub-command + flags. If it returns ``None`` the dimension
                  has nothing applicable to run on this project (=> n/a).
    ``exit_map``  maps a process return code to a verdict string.
    ``module``    optional ``python -m <module>`` fallback when the console
                  script is not on the PATH (some tools ship no venv bin).
    """
    key: str
    label: str
    cli: str
    build_cmd: Callable[[str, Path], Optional[list]]
    exit_map: Callable[[int], str]
    module: Optional[str] = None


@dataclass
class Verdict:
    dimension: str
    status: str                 # pass | warn | refuse | na | error
    detail: str = ""
    exit_code: Optional[int] = None
    cmd: str = ""


@dataclass
class DimensionResult:
    key: str
    label: str
    cli: str
    available: bool
    verdict: Optional[Verdict] = None
    # dimensions that resolved but had nothing to run on this project
    applicable_here: bool = True

    @property
    def applicable(self) -> bool:
        """A dimension counts toward the score only if its gate is installed AND
        it actually produced a runnable verdict on this project."""
        return self.available and self.applicable_here and self.verdict is not None \
            and self.verdict.status not in ("na",)

    @property
    def status(self) -> str:
        if not self.available:
            return "na"
        if not self.applicable_here or self.verdict is None:
            return "na"
        return self.verdict.status


# ── resolution: co-located venv bin first, then PATH (shipwright's rule) ───────
def _resolve(cli: str) -> Optional[str]:
    cand = Path(sys.executable).parent / cli
    if cand.exists():
        return str(cand)
    return shutil.which(cli)


def resolve_dimension(dim: Dimension) -> Optional[list]:
    """Return the leading argv (the resolved invocation) for this dimension, or
    ``None`` if the tool cannot be found at all. Prefers the console script;
    falls back to ``python -m <module>`` when the registry declares one."""
    binp = _resolve(dim.cli)
    if binp is not None:
        return [binp]
    if dim.module:
        # only use the module fallback if that module is importable in THIS venv
        import importlib.util
        if importlib.util.find_spec(dim.module.split(".")[0]) is not None:
            return [sys.executable, "-m", dim.module]
    return None


def gate_available(dim: Dimension) -> bool:
    return resolve_dimension(dim) is not None


class _null:
    def __enter__(self):
        return subprocess.DEVNULL

    def __exit__(self, *a):
        return False


def _run(cmd: list, timeout: int = 120) -> tuple[int, str]:
    """Run a gate CLI. Any failure is folded into rc=-1 so the spine never
    crashes on a misbehaving gate (mirrors shipwright.core._run)."""
    try:
        with _null() as fh:
            p = subprocess.run(cmd, stdin=fh, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return -1, "gate CLI not found"
    except subprocess.TimeoutExpired:
        return -1, "gate timed out"
    except Exception as e:  # noqa: BLE001 — a gate failure must never crash the orchestrator
        return -1, f"gate error: {str(e)[:160]}"


# ── standard exit-code -> verdict maps (each family CLI's documented contract) ─
def map_verity(code: int) -> str:
    """verity: 0 PASS · 1 WARN · 2 REFUSE (exit code = worst verdict)."""
    if code == -1:
        return "error"
    return {0: "pass", 1: "warn", 2: "refuse"}.get(code, "warn")


def map_zero_clean(code: int) -> str:
    """Generic gate: 0 = clean/allow/verified, non-zero = needs review."""
    if code == -1:
        return "error"
    return "pass" if code == 0 else "warn"


def map_allow_deny(code: int) -> str:
    """scope-gate: exit 0 = ALLOW, 1 = DENY. A DENY is a hard refuse, not a warn."""
    if code == -1:
        return "error"
    return "pass" if code == 0 else "refuse"


def map_aisec_severity(code: int) -> str:
    """aisec-check ``scan``: exit = worst severity (0 none · 1 low · 2 medium ·
    3 high · 4 critical). Fold into the verify-suite ladder: clean = pass,
    low/medium leads = warn (a human must confirm), high/critical = refuse."""
    if code == -1:
        return "error"
    if code == 0:
        return "pass"
    if code in (1, 2):
        return "warn"
    return "refuse"  # 3 (high), 4 (critical), or any higher unknown severity


# ── run one dimension ─────────────────────────────────────────────────────────
def run_dimension(dim: Dimension, root: Path) -> DimensionResult:
    lead = resolve_dimension(dim)
    if lead is None:
        return DimensionResult(dim.key, dim.label, dim.cli, available=False)

    try:
        tail = dim.build_cmd(lead[0], root)
    except Exception as e:  # noqa: BLE001 — a bad cmd-builder must not crash the spine
        v = Verdict(dim.key, "error", f"cmd-builder error: {str(e)[:160]}", None, "")
        return DimensionResult(dim.key, dim.label, dim.cli, available=True, verdict=v)

    if tail is None:
        # gate is installed but there is nothing of this kind to check here
        return DimensionResult(dim.key, dim.label, dim.cli, available=True,
                               applicable_here=False)

    cmd = lead + tail
    code, out = _run(cmd)
    status = dim.exit_map(code)
    v = Verdict(dim.key, status, out[:600], code, " ".join(cmd))
    return DimensionResult(dim.key, dim.label, dim.cli, available=True, verdict=v)


def run_check(root: Path, dimensions: list) -> list:
    """Run every registered dimension over the project root. Returns
    DimensionResults (one per dimension, in registry order)."""
    return [run_dimension(dim, root) for dim in dimensions]


# ── the unified 1-5 rollup (shipwright.core.score, generalized) ───────────────
def score(results: list) -> dict:
    """Level = round(1 + 4 * passed / applicable) over APPLICABLE dimensions only.

    A dimension that is absent (gate not installed) or has nothing to run on this
    project is ``n/a`` and is never counted — there is no fake pass. Returns the
    level plus the inspectable fractions and the worst verdict seen.
    """
    applicable = [r for r in results if r.applicable]
    passed = [r for r in applicable if r.status == "pass"]
    if not applicable:
        return {
            "level": None,
            "passed": 0,
            "applicable": 0,
            "na": len([r for r in results if not r.applicable]),
            "note": "No applicable gate produced a verdict — install family checkers "
                    "or point at a project with checkable artifacts to get a level.",
        }
    level = round(1 + 4 * (len(passed) / len(applicable)))
    worst = max((r.status for r in applicable), key=lambda s: _RANK.get(s, 0))
    return {
        "level": max(1, min(5, level)),
        "passed": len(passed),
        "applicable": len(applicable),
        "na": len(results) - len(applicable),
        "worst": worst,
    }
