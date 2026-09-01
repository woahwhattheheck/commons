"""Immutable, hash-chained deterministic evidence ledger primitives."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Tuple

from charttrace.schema.v1 import to_primitive


LEDGER_VERSION = "charttrace.ledger.v1.1"
GENESIS_HASH = "0" * 64


class LedgerIntegrityError(ValueError):
    pass


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    sequence: int
    event_type: str
    payload: Mapping[str, Any]
    previous_hash: str
    entry_hash: str

    def hash_payload(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": to_primitive(self.payload),
            "previous_hash": self.previous_hash,
            "sequence": self.sequence,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {**self.hash_payload(), "entry_hash": self.entry_hash}


@dataclass(frozen=True, slots=True)
class EvidenceLedger:
    entries: Tuple[LedgerEntry, ...] = ()
    version: str = LEDGER_VERSION

    def append(self, event_type: str, payload: Any) -> "EvidenceLedger":
        if not event_type or not event_type.replace("_", "").isalnum():
            raise ValueError("event_type must be a stable token")
        primitive = to_primitive(payload)
        if not isinstance(primitive, Mapping):
            primitive = {"value": primitive}
        sequence = len(self.entries) + 1
        previous_hash = (
            self.entries[-1].entry_hash if self.entries else GENESIS_HASH
        )
        unsigned = {
            "event_type": event_type,
            "payload": primitive,
            "previous_hash": previous_hash,
            "sequence": sequence,
        }
        entry_hash = hashlib.sha256(_canonical_json(unsigned)).hexdigest()
        entry = LedgerEntry(
            sequence=sequence,
            event_type=event_type,
            payload=dict(primitive),
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        return EvidenceLedger(entries=self.entries + (entry,), version=self.version)

    def verify(self) -> None:
        previous_hash = GENESIS_HASH
        for expected_sequence, entry in enumerate(self.entries, 1):
            expected_hash = hashlib.sha256(
                _canonical_json(entry.hash_payload())
            ).hexdigest()
            if entry.sequence != expected_sequence:
                raise LedgerIntegrityError("ledger sequence is not contiguous")
            if entry.previous_hash != previous_hash:
                raise LedgerIntegrityError("ledger previous hash is invalid")
            if entry.entry_hash != expected_hash:
                raise LedgerIntegrityError("ledger entry hash is invalid")
            previous_hash = entry.entry_hash

    def to_ndjson(self) -> bytes:
        self.verify()
        return b"".join(
            _canonical_json(entry.to_dict()) + b"\n" for entry in self.entries
        )

    @classmethod
    def from_ndjson(cls, data: bytes) -> "EvidenceLedger":
        entries = []
        try:
            for line in data.splitlines():
                if not line:
                    continue
                raw = json.loads(line)
                entries.append(
                    LedgerEntry(
                        sequence=raw["sequence"],
                        event_type=raw["event_type"],
                        payload=raw["payload"],
                        previous_hash=raw["previous_hash"],
                        entry_hash=raw["entry_hash"],
                    )
                )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LedgerIntegrityError("ledger encoding is invalid") from exc
        ledger = cls(tuple(entries))
        ledger.verify()
        return ledger

    @classmethod
    def build(cls, events: Iterable[Tuple[str, Any]]) -> "EvidenceLedger":
        ledger = cls()
        for event_type, payload in events:
            ledger = ledger.append(event_type, payload)
        return ledger
