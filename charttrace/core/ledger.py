"""Deterministic append-only ledger primitives for ChartTrace evidence."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import io
import json
from typing import Any, Iterable

from charttrace.schema.evidence import SourceCitation, to_primitive


LEDGER_VERSION = "charttrace-ledger-v1"
GENESIS_DIGEST = "0" * 64


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        to_primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    sequence: int
    record_type: str
    record_id: str
    payload_json: str
    previous_digest: str
    digest: str


class EvidenceLedger:
    """Small deterministic hash chain; release policy belongs elsewhere."""

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []
        self._ids: set[tuple[str, str]] = set()

    @property
    def entries(self) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries)

    def append(self, record_type: str, record_id: str, payload: Any) -> LedgerEntry:
        if not record_type.strip() or not record_id.strip():
            raise ValueError("record_type and record_id are required")
        key = (record_type, record_id)
        if key in self._ids:
            raise ValueError(f"duplicate immutable record: {record_type}/{record_id}")
        primitive = to_primitive(payload)
        if not isinstance(primitive, dict):
            raise ValueError("ledger payload must be an object")
        payload_json = canonical_json_bytes(primitive).decode("utf-8")
        sequence = len(self._entries) + 1
        previous = self._entries[-1].digest if self._entries else GENESIS_DIGEST
        envelope = {
            "ledger_version": LEDGER_VERSION,
            "sequence": sequence,
            "record_type": record_type,
            "record_id": record_id,
            "payload": primitive,
            "previous_digest": previous,
        }
        digest = hashlib.sha256(canonical_json_bytes(envelope)).hexdigest()
        entry = LedgerEntry(sequence, record_type, record_id, payload_json, previous, digest)
        self._entries.append(entry)
        self._ids.add(key)
        return entry

    def verify(self) -> bool:
        previous = GENESIS_DIGEST
        for expected_sequence, entry in enumerate(self._entries, 1):
            if entry.sequence != expected_sequence or entry.previous_digest != previous:
                return False
            try:
                payload = json.loads(entry.payload_json)
            except (json.JSONDecodeError, TypeError):
                return False
            if canonical_json_bytes(payload).decode("utf-8") != entry.payload_json:
                return False
            envelope = {
                "ledger_version": LEDGER_VERSION,
                "sequence": entry.sequence,
                "record_type": entry.record_type,
                "record_id": entry.record_id,
                "payload": payload,
                "previous_digest": entry.previous_digest,
            }
            if hashlib.sha256(canonical_json_bytes(envelope)).hexdigest() != entry.digest:
                return False
            previous = entry.digest
        return True

    def to_json_bytes(self) -> bytes:
        entries = [
            {
                "sequence": entry.sequence,
                "record_type": entry.record_type,
                "record_id": entry.record_id,
                "payload": json.loads(entry.payload_json),
                "previous_digest": entry.previous_digest,
                "digest": entry.digest,
            }
            for entry in self._entries
        ]
        return canonical_json_bytes(
            {"ledger_version": LEDGER_VERSION, "entries": entries}
        ) + b"\n"


def validate_citation(
    citation: SourceCitation,
    source_pages: dict[str, tuple[str, int]],
) -> None:
    """Resolve a citation against document -> (sha256, page_count)."""

    source = source_pages.get(citation.document_id)
    if source is None:
        raise ValueError("citation document is outside the supplied source universe")
    expected_sha, page_count = source
    if citation.source_sha256 != expected_sha:
        raise ValueError("citation source hash mismatch")
    if citation.page > page_count:
        raise ValueError("citation page is outside the source")


def rows_to_csv_bytes(rows: Iterable[dict[str, Any]], columns: tuple[str, ...]) -> bytes:
    """Create stable UTF-8 CSV with an explicit column contract."""

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=list(columns),
        extrasaction="raise",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        missing = set(columns) - set(row)
        if missing:
            raise ValueError(f"CSV row missing columns: {sorted(missing)}")
        writer.writerow({column: row[column] for column in columns})
    return output.getvalue().encode("utf-8")
