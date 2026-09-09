#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed paired observation/action/receipt trace gate for TITAN V3.

The gate consumes *external* traces emitted by ``benchmark.py``. It never asks
an agent for hidden state or free-form reasoning. It aligns exact game cells,
identifies the first observable divergence, attributes transaction/cash deltas,
and applies an explicit panel policy.
"""
from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import stat
from typing import Any, Mapping

SCHEMA_VERSION = 1
DEFAULT_MAX_COMPRESSED_BYTES = 128 * 1024 * 1024
DEFAULT_MAX_DECODED_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_LINE_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_ROWS = 10_000
_REQUIRED_ROW_FIELDS = {
    "step", "candidate_seat", "observation", "actions", "transactions",
    "post_cash", "post_shed", "post_market", "done",
}


class TraceGateError(ValueError):
    """Raised when contract or trace evidence is invalid."""


def _reject_constant(value: str) -> None:
    raise TraceGateError(f"non-finite JSON constant is forbidden: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TraceGateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json_loads(text: str, label: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_pairs,
                          parse_constant=_reject_constant)
    except TraceGateError:
        raise
    except json.JSONDecodeError as exc:
        raise TraceGateError(f"{label}: invalid JSON: {exc}") from exc


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TraceGateError(f"value is not canonical finite JSON: {exc}") from exc


def _json_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _as_int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if not _is_int(value):
        raise TraceGateError(f"{label} must be an integer (boolean is not accepted)")
    if minimum is not None and value < minimum:
        raise TraceGateError(f"{label} must be >= {minimum}")
    return value


def _as_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TraceGateError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise TraceGateError(f"{label} must be finite")
    return number


def _as_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TraceGateError(f"{label} must be a nonempty string")
    return value.strip()


def _as_sha256(value: Any, label: str) -> str:
    digest = _as_nonempty_string(value, label).lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise TraceGateError(f"{label} must be a lowercase or uppercase SHA-256 hex digest")
    return digest


def _as_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise TraceGateError(f"{label} must be boolean")
    return value


def _read_regular_file(path: Path, *, max_bytes: int, label: str) -> bytes:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise TraceGateError(f"{label}: missing file: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise TraceGateError(f"{label}: symlink inputs are forbidden: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise TraceGateError(f"{label}: input must be a regular file: {path}")
    if metadata.st_size > max_bytes:
        raise TraceGateError(
            f"{label}: compressed/input bytes {metadata.st_size} exceed limit {max_bytes}"
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise TraceGateError(f"{label}: failed to read {path}: {exc}") from exc
    if len(data) != metadata.st_size:
        raise TraceGateError(
            f"{label}: file size changed during acquisition ({metadata.st_size} -> {len(data)})"
        )
    return data


def _decode_trace_bytes(data: bytes, *, max_decoded_bytes: int, label: str) -> bytes:
    if data.startswith(b"\x1f\x8b"):
        source: io.BufferedIOBase | gzip.GzipFile = gzip.GzipFile(fileobj=io.BytesIO(data))
    else:
        source = io.BytesIO(data)
    decoded = bytearray()
    try:
        with source:
            while True:
                chunk = source.read(min(1024 * 1024, max_decoded_bytes + 1 - len(decoded)))
                if not chunk:
                    break
                decoded.extend(chunk)
                if len(decoded) > max_decoded_bytes:
                    raise TraceGateError(
                        f"{label}: decoded bytes exceed limit {max_decoded_bytes}"
                    )
    except TraceGateError:
        raise
    except (OSError, EOFError) as exc:
        raise TraceGateError(f"{label}: invalid compressed trace: {exc}") from exc
    return bytes(decoded)


def _validate_action(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TraceGateError(f"{label} must be an object")
    _canonical_bytes(value)
    market = value.get("market", [])
    if not isinstance(market, list):
        raise TraceGateError(f"{label}.market must be a list when present")
    return value


def _validate_transaction(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TraceGateError(f"{label} must be an object")
    seat = _as_int(value.get("seat"), f"{label}.seat")
    if seat not in (0, 1):
        raise TraceGateError(f"{label}.seat must be 0 or 1")
    _as_nonempty_string(value.get("op"), f"{label}.op")
    _as_nonempty_string(value.get("item"), f"{label}.item")
    _as_int(value.get("units"), f"{label}.units", minimum=0)
    _as_finite(value.get("cash"), f"{label}.cash")
    prices = value.get("unit_prices", [])
    if not isinstance(prices, list):
        raise TraceGateError(f"{label}.unit_prices must be a list")
    for index, price in enumerate(prices):
        _as_finite(price, f"{label}.unit_prices[{index}]")
    _canonical_bytes(value)
    return value


@dataclass(frozen=True)
class Trace:
    path_label: str
    sha256: str
    compressed_bytes: int
    decoded_bytes: int
    rows: tuple[Mapping[str, Any], ...]
    candidate_seat: int


def load_trace(
    path: Path,
    *,
    expected_sha256: str,
    path_label: str,
    expected_seat: int,
    expected_rows: int | None,
    max_compressed_bytes: int = DEFAULT_MAX_COMPRESSED_BYTES,
    max_decoded_bytes: int = DEFAULT_MAX_DECODED_BYTES,
    max_line_bytes: int = DEFAULT_MAX_LINE_BYTES,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> Trace:
    """Read one trace once, verify its compressed/raw digest, and validate rows."""
    data = _read_regular_file(path, max_bytes=max_compressed_bytes, label=path_label)
    digest = _sha256(data)
    if digest != expected_sha256:
        raise TraceGateError(
            f"{path_label}: SHA-256 mismatch: expected {expected_sha256}, got {digest}"
        )
    decoded = _decode_trace_bytes(data, max_decoded_bytes=max_decoded_bytes, label=path_label)
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TraceGateError(f"{path_label}: trace is not UTF-8: {exc}") from exc
    raw_lines = text.splitlines()
    if not raw_lines:
        raise TraceGateError(f"{path_label}: trace is empty")
    if len(raw_lines) > max_rows:
        raise TraceGateError(f"{path_label}: row count {len(raw_lines)} exceeds {max_rows}")
    if expected_rows is not None and len(raw_lines) != expected_rows:
        raise TraceGateError(
            f"{path_label}: expected {expected_rows} rows, observed {len(raw_lines)}"
        )

    rows: list[Mapping[str, Any]] = []
    previous_step: int | None = None
    seen_done = False
    observed_seat: int | None = None
    for line_number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            raise TraceGateError(f"{path_label}: blank line at {line_number}")
        if len(line.encode("utf-8")) > max_line_bytes:
            raise TraceGateError(f"{path_label}: line {line_number} exceeds {max_line_bytes} bytes")
        row = _strict_json_loads(line, f"{path_label}:line {line_number}")
        if not isinstance(row, Mapping):
            raise TraceGateError(f"{path_label}:line {line_number}: row must be an object")
        missing = sorted(_REQUIRED_ROW_FIELDS - set(row))
        if missing:
            raise TraceGateError(f"{path_label}:line {line_number}: missing fields {missing}")
        step = _as_int(row["step"], f"{path_label}:line {line_number}.step", minimum=0)
        if previous_step is not None and step != previous_step + 1:
            raise TraceGateError(f"{path_label}: non-contiguous steps: {previous_step} -> {step}")
        previous_step = step

        seat = _as_int(row["candidate_seat"], f"{path_label}:line {line_number}.candidate_seat")
        if seat not in (0, 1):
            raise TraceGateError(f"{path_label}: candidate_seat must be 0 or 1")
        if observed_seat is None:
            observed_seat = seat
        elif observed_seat != seat:
            raise TraceGateError(f"{path_label}: candidate_seat changes within trace")
        if seat != expected_seat:
            raise TraceGateError(f"{path_label}: contract seat {expected_seat}, trace seat {seat}")

        if not isinstance(row["observation"], Mapping):
            raise TraceGateError(f"{path_label}:line {line_number}.observation must be object")
        _canonical_bytes(row["observation"])
        actions = row["actions"]
        if not isinstance(actions, list) or len(actions) != 2:
            raise TraceGateError(f"{path_label}:line {line_number}.actions must have length 2")
        for action_index, action in enumerate(actions):
            _validate_action(action, f"{path_label}:line {line_number}.actions[{action_index}]")

        transactions = row["transactions"]
        if not isinstance(transactions, list):
            raise TraceGateError(f"{path_label}:line {line_number}.transactions must be list")
        for tx_index, transaction in enumerate(transactions):
            _validate_transaction(transaction,
                f"{path_label}:line {line_number}.transactions[{tx_index}]")

        post_cash = row["post_cash"]
        if not isinstance(post_cash, list) or len(post_cash) != 2:
            raise TraceGateError(f"{path_label}:line {line_number}.post_cash must have length 2")
        for cash_index, cash in enumerate(post_cash):
            _as_finite(cash, f"{path_label}:line {line_number}.post_cash[{cash_index}]")
        if not isinstance(row["post_shed"], Mapping):
            raise TraceGateError(f"{path_label}:line {line_number}.post_shed must be object")
        _canonical_bytes(row["post_shed"])
        _canonical_bytes(row["post_market"])

        done = _as_bool(row["done"], f"{path_label}:line {line_number}.done")
        if seen_done:
            raise TraceGateError(f"{path_label}: rows occur after terminal row")
        if done:
            seen_done = True
            if line_number != len(raw_lines):
                raise TraceGateError(f"{path_label}: done=true before final row")
        rows.append(row)

    if not seen_done:
        raise TraceGateError(f"{path_label}: final row must have done=true")
    assert observed_seat is not None
    return Trace(path_label=path_label, sha256=digest, compressed_bytes=len(data),
                 decoded_bytes=len(decoded), rows=tuple(rows), candidate_seat=observed_seat)
