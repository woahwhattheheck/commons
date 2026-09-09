# SPDX-License-Identifier: Apache-2.0
"""Fail-closed one-factor overlay for TITAN's SELL planning objective.

The canonical optimizer returns a four-field score tuple whose first element is
``own_cash + carry - rival_cash``. Every existing admission/ranking rule reads
that first element. This overlay preserves the tuple's diagnostics and all
upstream receipt math, but changes only element zero to ``own_cash + carry``.

No repository source is rewritten. The overlay is installed in the isolated
candidate worker before the canonical entrypoint constructs its runtime.
"""
from __future__ import annotations

from functools import wraps
import hashlib
import importlib
import inspect
import math
from numbers import Real
from pathlib import Path
from typing import Any

VERSION = "titan-v3-own-value-objective-v1"
EXPECTED_SELECTED_SELL_CORE_BLOB = "f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3"
EXPECTED_SIGNATURE = "(self, plan, quantity, rival, alignment, terminal=False)"
EXPECTED_SOURCE_NEEDLES = (
    "def score(self, plan, quantity, rival, alignment, terminal=False):",
    "return own_cash+carry-other_cash, own_cash,other_cash,remaining",
)
_PATCH_TAG = "__titan_own_value_objective_version__"
_ORIGINAL_TAG = "__titan_own_value_objective_original__"


class ObjectiveBindingError(RuntimeError):
    """The overlay cannot prove it is attached to the intended source seam."""


class ObjectiveScoreError(RuntimeError):
    """The wrapped optimizer produced a score outside the pinned contract."""


def _finite_real(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ObjectiveScoreError(f"{field} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise ObjectiveScoreError(f"{field} must be a finite real number")
    return result


def git_blob_sha1_bytes(data: bytes) -> str:
    """Return the Git blob object id for exact file bytes."""
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def git_blob_sha1(path: Path) -> str:
    """Hash one regular source file exactly as ``git hash-object`` does."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ObjectiveBindingError(f"source is not one regular file: {path}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ObjectiveBindingError(f"cannot read bound source {path}: {exc}") from exc
    return git_blob_sha1_bytes(data)


def own_value_tuple(score: Any) -> tuple[Any, Any, Any, Any]:
    """Replace only score element zero with own receipts plus continuation value.

    The incumbent score satisfies::

        relative_value = own_cash + carry - rival_cash

    Therefore ``relative_value + rival_cash`` recovers ``own_cash + carry``
    without copying or altering receipt, carry, scenario, or feasibility logic.
    """
    if not isinstance(score, tuple) or len(score) != 4:
        raise ObjectiveScoreError("MarketPath.score must return an exact four-tuple")
    relative, own_cash, rival_cash, remaining = score
    relative_value = _finite_real(relative, "relative_value")
    own_value = _finite_real(own_cash, "own_cash")
    rival_value = _finite_real(rival_cash, "rival_cash")
    recovered = relative_value + rival_value
    tolerance = 1e-9 * max(1.0, abs(recovered), abs(own_value))
    if recovered + tolerance < own_value:
        raise ObjectiveScoreError(
            "recovered own value is below realized own cash; continuation value is invalid"
        )
    return recovered, own_cash, rival_cash, remaining


def _expected_source_path(expected_root: Path | None) -> Path | None:
    return (
        None
        if expected_root is None
        else Path(expected_root).resolve() / "selected_sell_core.py"
    )


def _validate_blob(source_path: Path, expected_blob: str) -> str:
    if not isinstance(expected_blob, str) or len(expected_blob) != 40:
        raise ObjectiveBindingError("expected selected_sell_core Git blob is invalid")
    actual_blob = git_blob_sha1(source_path)
    if actual_blob != expected_blob:
        raise ObjectiveBindingError(
            "selected_sell_core Git blob drift: "
            f"expected {expected_blob}, got {actual_blob}"
        )
    return actual_blob


def _validate_binding(
    module: Any,
    expected_root: Path | None,
    expected_blob: str,
) -> tuple[Any, Path, str, str]:
    raw_path = getattr(module, "__file__", "")
    if not raw_path:
        raise ObjectiveBindingError("selected_sell_core source path is missing")
    source_path = Path(raw_path).resolve()
    if source_path.name != "selected_sell_core.py":
        raise ObjectiveBindingError(
            f"expected selected_sell_core.py, got {source_path.name or '<missing>'}"
        )
    expected_path = _expected_source_path(expected_root)
    if expected_path is not None and source_path != expected_path:
        raise ObjectiveBindingError(
            f"selected_sell_core path mismatch: expected {expected_path}, got {source_path}"
        )
    source_blob = _validate_blob(source_path, expected_blob)
    market_path = getattr(module, "MarketPath", None)
    current = getattr(market_path, "score", None)
    if not callable(current):
        raise ObjectiveBindingError("selected_sell_core.MarketPath.score is not callable")
    signature = str(inspect.signature(current))
    if signature != EXPECTED_SIGNATURE:
        raise ObjectiveBindingError(
            f"MarketPath.score signature drift: expected {EXPECTED_SIGNATURE}, got {signature}"
        )
    try:
        source = inspect.getsource(current)
    except (OSError, TypeError) as exc:
        raise ObjectiveBindingError("cannot inspect MarketPath.score source") from exc
    missing = [needle for needle in EXPECTED_SOURCE_NEEDLES if needle not in source]
    if missing:
        raise ObjectiveBindingError(
            "MarketPath.score source drift at objective seam: " + repr(missing)
        )
    return current, source_path, signature, source_blob


def install(
    *,
    module: Any | None = None,
    expected_root: Path | None = None,
    expected_blob: str = EXPECTED_SELECTED_SELL_CORE_BLOB,
) -> dict[str, Any]:
    """Install the one-factor overlay once and return a machine-readable receipt."""
    if module is None:
        module = importlib.import_module("selected_sell_core")
    market_path = getattr(module, "MarketPath", None)
    current = getattr(market_path, "score", None)
    prior_version = getattr(current, _PATCH_TAG, None)
    if prior_version is not None:
        if prior_version != VERSION:
            raise ObjectiveBindingError(
                f"conflicting MarketPath.score overlay already installed: {prior_version}"
            )
        receipt = getattr(module, "__titan_own_value_objective_receipt__", None)
        if not isinstance(receipt, dict):
            raise ObjectiveBindingError("idempotent overlay is missing its install receipt")
        source_path = Path(str(receipt.get("source_path", ""))).resolve()
        expected_path = _expected_source_path(expected_root)
        if expected_path is not None and source_path != expected_path:
            raise ObjectiveBindingError(
                f"selected_sell_core path mismatch: expected {expected_path}, got {source_path}"
            )
        actual_blob = _validate_blob(source_path, expected_blob)
        if receipt.get("source_git_blob") != actual_blob:
            raise ObjectiveBindingError("idempotent overlay receipt is detached from source blob")
        if receipt.get("expected_git_blob") != expected_blob:
            raise ObjectiveBindingError("idempotent overlay receipt expected blob mismatch")
        return dict(receipt)

    original, source_path, signature, source_blob = _validate_binding(
        module, expected_root, expected_blob
    )

    @wraps(original)
    def patched(self: Any, *args: Any, **kwargs: Any) -> tuple[Any, Any, Any, Any]:
        return own_value_tuple(original(self, *args, **kwargs))

    setattr(patched, _PATCH_TAG, VERSION)
    setattr(patched, _ORIGINAL_TAG, original)
    market_path.score = patched
    receipt = {
        "version": VERSION,
        "source_path": str(source_path),
        "source_git_blob": source_blob,
        "expected_git_blob": expected_blob,
        "signature": signature,
        "changed_field": "MarketPath.score[0]",
        "incumbent_objective": "own_cash + carry - rival_cash",
        "candidate_objective": "own_cash + carry",
        "recovery_identity": "candidate_objective = incumbent_score[0] + incumbent_score[2]",
        "canonical_files_modified": False,
    }
    setattr(module, "__titan_own_value_objective_receipt__", dict(receipt))
    return receipt
