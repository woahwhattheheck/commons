#!/usr/bin/env python3
"""Test-support helpers for proving denied operations leave JSON state unchanged."""
from __future__ import annotations

import json
import math
from typing import Any, Callable


class NoMutationStateError(ValueError):
    """Raised when state cannot be snapshotted as strict deterministic JSON."""


class NoMutationAssertionError(AssertionError):
    """Raised when a denied/invalid operation violates the no-mutation contract."""


def _strict_json(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise NoMutationStateError(f"non-finite number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _strict_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise NoMutationStateError(f"non-string object key at {path}")
            _strict_json(item, f"{path}.{key}")
        return
    raise NoMutationStateError(f"unsupported JSON value at {path}: {type(value).__name__}")


def snapshot_json_state(state: Any) -> bytes:
    """Return stable strict-JSON bytes suitable for before/after equality checks."""
    _strict_json(state)
    return json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _exception_label(expected: type[Exception] | tuple[type[Exception], ...]) -> str:
    classes = expected if isinstance(expected, tuple) else (expected,)
    if not classes or any(not isinstance(cls, type) or not issubclass(cls, Exception) for cls in classes):
        raise TypeError("expected_exception must be an exception type or non-empty tuple of exception types")
    return " or ".join(cls.__name__ for cls in classes)


def assert_raises_without_mutation(
    state: Any,
    operation: Callable[[], Any],
    expected_exception: type[Exception] | tuple[type[Exception], ...],
) -> Exception:
    """Require ``operation`` to raise as expected without changing ``state``.

    The state is snapshotted before the operation and again after the exception.
    Any mutation, unexpected exception class, failure to raise, or loss of strict
    JSON serializability raises ``NoMutationAssertionError``.
    """
    if not callable(operation):
        raise TypeError("operation must be callable")
    expected_label = _exception_label(expected_exception)
    before = snapshot_json_state(state)

    try:
        operation()
    except expected_exception as exc:
        try:
            after = snapshot_json_state(state)
        except NoMutationStateError as snapshot_exc:
            raise NoMutationAssertionError(
                f"state became invalid after expected {expected_label}: {snapshot_exc}"
            ) from exc
        if after != before:
            raise NoMutationAssertionError(
                f"state mutated before expected {type(exc).__name__} was raised"
            ) from exc
        return exc
    except Exception as exc:
        try:
            after = snapshot_json_state(state)
        except NoMutationStateError as snapshot_exc:
            raise NoMutationAssertionError(
                f"operation raised unexpected {type(exc).__name__} and state became invalid: {snapshot_exc}"
            ) from exc
        mutation = " and mutated state" if after != before else ""
        raise NoMutationAssertionError(
            f"expected {expected_label}, got unexpected {type(exc).__name__}{mutation}"
        ) from exc

    try:
        after = snapshot_json_state(state)
    except NoMutationStateError as snapshot_exc:
        raise NoMutationAssertionError(
            f"operation did not raise {expected_label} and state became invalid: {snapshot_exc}"
        ) from snapshot_exc
    mutation = " and mutated state" if after != before else ""
    raise NoMutationAssertionError(f"operation did not raise {expected_label}{mutation}")
