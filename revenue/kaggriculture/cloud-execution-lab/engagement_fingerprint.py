# SPDX-License-Identifier: Apache-2.0
"""Deterministic matched-policy engagement fingerprints for TITAN experiments.

This module is deliberately outside the gameplay path. It lets official-engine
workers prove that a candidate actually changed a decision before spending a
large matched seed/seat grid on it.

JSONL rows accepted by the CLI look like::

    {"seed": 7, "seat": 0, "step": 12, "phase": "market",
     "control": [["SELL", "MILK", 1]],
     "candidate": [["SELL", "MILK", 2]]}

The default alignment key is ``seed,seat,step,phase``. Duplicate or incomplete
keys fail closed rather than manufacturing a comparison. ``NO_OP_OBSERVED``
means only that the configured matched prefix did not diverge; it is not a
claim that a policy can never engage later in a game.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class FingerprintError(ValueError):
    """Raised when a decision contains unsupported or non-finite data."""


class AlignmentError(ValueError):
    """Raised when matched comparison rows are not uniquely aligned."""


def _encode_tree(value: Any) -> str:
    """Encode an already-canonical tree without reinterpreting its type tags."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    )


def _canonical(value: Any) -> Any:
    """Return a typed deterministic tree for JSON-like decision data."""
    # Type tags prevent Python equality quirks (True == 1, -0.0 == 0.0) from
    # silently collapsing distinct engine decisions.
    if value is None:
        return ["none"]
    if type(value) is bool:
        return ["bool", value]
    if type(value) is int:
        return ["int", str(value)]
    if type(value) is float:
        if not math.isfinite(value):
            raise FingerprintError("non-finite float in decision")
        return ["float", value.hex()]
    if type(value) is str:
        return ["str", value]
    if type(value) is bytes:
        return ["bytes", value.hex()]
    if isinstance(value, Mapping):
        encoded = []
        for key, item in value.items():
            canonical_key = _canonical(key)
            canonical_item = _canonical(item)
            encoded.append((_encode_tree(canonical_key), canonical_key, canonical_item))
        encoded.sort(key=lambda row: row[0])
        return ["map", [[key, item] for _, key, item in encoded]]
    if type(value) is list:
        return ["list", [_canonical(item) for item in value]]
    if type(value) is tuple:
        return ["tuple", [_canonical(item) for item in value]]
    if type(value) is set or type(value) is frozenset:
        items = [_canonical(item) for item in value]
        items.sort(key=_encode_tree)
        return ["set", items]
    raise FingerprintError(f"unsupported decision type: {type(value).__name__}")


def fingerprint(value: Any) -> str:
    """Return a SHA-256 fingerprint of an exact typed decision structure."""
    payload = _encode_tree(_canonical(value)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _key_token(key: Mapping[str, Any], fields: Sequence[str]) -> tuple[str, dict[str, Any]]:
    missing = [field for field in fields if field not in key]
    if missing:
        raise AlignmentError(f"missing alignment fields: {', '.join(missing)}")
    selected = {field: key[field] for field in fields}
    token = fingerprint([selected[field] for field in fields])
    return token, selected


@dataclass(frozen=True)
class Divergence:
    observation: int
    key: dict[str, Any]
    control_fingerprint: str
    candidate_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation": self.observation,
            "key": self.key,
            "control_fingerprint": self.control_fingerprint,
            "candidate_fingerprint": self.candidate_fingerprint,
        }


class EngagementTracker:
    """Streaming matched A/B decision comparison with fail-closed alignment."""

    def __init__(
        self,
        *,
        key_fields: Sequence[str] = ("seed", "seat", "step", "phase"),
        noop_threshold: int = 8,
    ) -> None:
        if not key_fields:
            raise ValueError("at least one alignment key field is required")
        if noop_threshold < 1:
            raise ValueError("noop_threshold must be positive")
        self.key_fields = tuple(key_fields)
        self.noop_threshold = int(noop_threshold)
        self.observations = 0
        self.divergence_count = 0
        self.first_divergence: Divergence | None = None
        self._seen_keys: set[str] = set()
        self._control_sequence = hashlib.sha256()
        self._candidate_sequence = hashlib.sha256()

    def observe(self, key: Mapping[str, Any], control: Any, candidate: Any) -> None:
        """Add one already-matched decision pair.

        ``key`` must contain every configured key field and each resulting key
        may appear only once. A bad trace therefore cannot look like a no-op.
        """
        token, selected = _key_token(key, self.key_fields)
        if token in self._seen_keys:
            raise AlignmentError(f"duplicate matched key: {selected!r}")
        self._seen_keys.add(token)

        control_fp = fingerprint(control)
        candidate_fp = fingerprint(candidate)
        self.observations += 1

        # Bind sequence summaries to the alignment key as well as the action.
        encoded_key = token.encode("ascii")
        self._control_sequence.update(encoded_key + b":" + control_fp.encode("ascii") + b"\n")
        self._candidate_sequence.update(encoded_key + b":" + candidate_fp.encode("ascii") + b"\n")

        if control_fp != candidate_fp:
            self.divergence_count += 1
            if self.first_divergence is None:
                self.first_divergence = Divergence(
                    observation=self.observations,
                    key=selected,
                    control_fingerprint=control_fp,
                    candidate_fingerprint=candidate_fp,
                )

    @property
    def engagement_rate(self) -> float:
        if not self.observations:
            return 0.0
        return self.divergence_count / self.observations

    @property
    def observed_noop(self) -> bool:
        """Whether the configured matched prefix is long enough and unchanged."""
        return self.observations >= self.noop_threshold and self.divergence_count == 0

    def summary(self) -> dict[str, Any]:
        """Return a stable machine-readable engagement report."""
        if self.divergence_count:
            classification = "ENGAGED"
        elif self.observations >= self.noop_threshold:
            classification = "NO_OP_OBSERVED"
        else:
            classification = "INSUFFICIENT"
        return {
            "classification": classification,
            "observations": self.observations,
            "noop_threshold": self.noop_threshold,
            "divergence_count": self.divergence_count,
            "engagement_rate": self.engagement_rate,
            "first_divergence": (
                self.first_divergence.as_dict() if self.first_divergence else None
            ),
            "control_sequence_fingerprint": self._control_sequence.hexdigest(),
            "candidate_sequence_fingerprint": self._candidate_sequence.hexdigest(),
            "key_fields": list(self.key_fields),
        }


def compare_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    key_fields: Sequence[str] = ("seed", "seat", "step", "phase"),
    control_field: str = "control",
    candidate_field: str = "candidate",
    noop_threshold: int = 8,
) -> dict[str, Any]:
    """Compare a matched iterable and return its engagement summary."""
    tracker = EngagementTracker(key_fields=key_fields, noop_threshold=noop_threshold)
    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise AlignmentError(f"row {row_number} is not an object")
        if control_field not in row or candidate_field not in row:
            raise AlignmentError(
                f"row {row_number} must contain {control_field!r} and {candidate_field!r}"
            )
        tracker.observe(row, row[control_field], row[candidate_field])
    return tracker.summary()


def _read_jsonl(path: Path) -> Iterable[Mapping[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AlignmentError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, Mapping):
                raise AlignmentError(f"{path}:{line_number}: row is not a JSON object")
            yield row


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report whether matched TITAN control/candidate decisions actually diverge."
    )
    parser.add_argument("jsonl", type=Path, help="paired JSONL decision trace")
    parser.add_argument(
        "--key",
        action="append",
        dest="keys",
        help="alignment field (repeatable; defaults to seed,seat,step,phase)",
    )
    parser.add_argument("--control-field", default="control")
    parser.add_argument("--candidate-field", default="candidate")
    parser.add_argument("--noop-threshold", type=int, default=8)
    args = parser.parse_args(argv)

    try:
        report = compare_rows(
            _read_jsonl(args.jsonl),
            key_fields=tuple(args.keys) if args.keys else ("seed", "seat", "step", "phase"),
            control_field=args.control_field,
            candidate_field=args.candidate_field,
            noop_threshold=args.noop_threshold,
        )
    except (ValueError, OSError) as exc:
        print(f"engagement_fingerprint: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
