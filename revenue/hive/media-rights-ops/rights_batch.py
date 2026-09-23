"""Batch placement review using the existing supplied-authority evaluator.

This module cannot import grants or record placements. Every row in a report
is evaluated on the same read-only SQLite snapshot.
"""
from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from rights_model import RightsError, canonical_bytes, normalize_intent, require
from rights_store import _evaluate

MAX_CSV_BYTES = 1024 * 1024
MAX_BATCH_ROWS = 1000
INTENT_COLUMNS = ("asset_id", "channel", "territory", "starts_at", "ends_at")
REPORT_COLUMNS = (
    "source_row", "request_id", *INTENT_COLUMNS, "status",
    "selected_grant_id", "reasons", "error",
)
READY = "READY_ON_SUPPLIED_AUTHORITY"


def parse_csv(text: str) -> list[dict]:
    require(isinstance(text, str), "csv must be UTF-8 text")
    require(0 < len(text.encode("utf-8")) <= MAX_CSV_BYTES, "CSV must contain 1 byte to 1 MiB")
    require("\x00" not in text, "CSV must not contain NUL characters")
    reader = csv.reader(io.StringIO(text.removeprefix("\ufeff"), newline=""), strict=True)
    rows = []
    try:
        header = next(reader, None)
        require(header is not None, "CSV is empty")
        header = [name.strip() for name in header]
        required = set(INTENT_COLUMNS)
        require(len(header) == len(set(header)), "CSV header contains duplicate columns")
        require(set(header) in (required, required | {"request_id"}),
                "CSV columns must be asset_id,channel,territory,starts_at,ends_at; request_id is optional")
        last_line = reader.line_num
        for values in reader:
            source_row = last_line + 1
            last_line = reader.line_num
            if not values:
                continue
            require(len(rows) < MAX_BATCH_ROWS, "CSV exceeds 1000 data rows; split the batch")
            item = {"source_row": source_row, "input": dict(zip(header, values)), "parse_error": ""}
            if len(values) != len(header):
                item["parse_error"] = f"expected {len(header)} cells, found {len(values)}"
            rows.append(item)
    except csv.Error as exc:
        raise RightsError(f"CSV syntax error near line {reader.line_num}: {exc}") from exc
    require(rows, "CSV contains a header but no placement rows")
    return rows


def evaluate_csv(path: Path | str, text: str) -> dict:
    parsed = parse_csv(text)
    # mode=ro also prevents an incorrect database pathname creating a new file.
    database = Path(path).resolve(strict=True)
    con = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=10.0, isolation_level=None)
    con.row_factory = sqlite3.Row
    results = []
    try:
        con.execute("PRAGMA query_only=ON")
        con.execute("BEGIN")
        # The first SELECT establishes the snapshot before any intent is evaluated.
        audit_seq = int(con.execute("SELECT COALESCE(MAX(seq),0) FROM audit").fetchone()[0])
        evaluated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        for parsed_row in parsed:
            original = parsed_row["input"]
            row = {
                "source_row": parsed_row["source_row"], "input": original,
                "status": "INVALID_INPUT", "selected_grant_id": None,
                "reasons": [], "error": "",
            }
            try:
                require(not parsed_row["parse_error"], parsed_row["parse_error"])
                normalized = normalize_intent(original, require_request_id="request_id" in original)
                row.update(_evaluate(con, {key: normalized[key] for key in INTENT_COLUMNS}))
                row["normalized_intent"] = normalized
            except RightsError as exc:
                row["reasons"] = ["INVALID_INPUT"]
                row["error"] = str(exc)
            results.append(row)
    finally:
        if con.in_transaction:
            con.execute("ROLLBACK")
        con.close()
    return {
        "mode": "READ_ONLY_BATCH_REVIEW",
        "evaluated_at": evaluated_at,
        "snapshot_audit_seq": audit_seq,
        "summary": {
            "total": len(results),
            "ready": sum(row["status"] == READY for row in results),
            "hold": sum(row["status"] == "HOLD" for row in results),
            "invalid": sum(row["status"] == "INVALID_INPUT" for row in results),
        },
        "rows": results,
    }


def _csv_cell(value) -> str:
    text = "" if value is None else str(value)
    # A CSV reader must see text, not a spreadsheet formula from an invalid input.
    if text.startswith(("\t", "\r", "\n")) or text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def report_csv(report: dict) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(REPORT_COLUMNS)
    for row in report["rows"]:
        fields = {**row["input"], **row, "reasons": "; ".join(row["reasons"])}
        writer.writerow([_csv_cell(fields.get(column, "")) for column in REPORT_COLUMNS])
    return output.getvalue()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Review a placement CSV without changing media-rights state")
    parser.add_argument("database", type=Path)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    args = parser.parse_args(argv)
    try:
        with args.csv_file.open("rb") as source:
            raw = source.read(MAX_CSV_BYTES + 1)
        require(len(raw) <= MAX_CSV_BYTES, "CSV exceeds 1 MiB")
        report = evaluate_csv(args.database, raw.decode("utf-8-sig"))
        encoded = (report_csv(report).encode("utf-8-sig") if args.format == "csv" else canonical_bytes(report))
        sys.stdout.buffer.write(encoded)
        return 0 if report["summary"]["ready"] == report["summary"]["total"] else 2
    except (RightsError, OSError, sqlite3.Error, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
