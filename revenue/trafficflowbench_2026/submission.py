from __future__ import annotations

import csv
import hashlib
import io
import math
from collections.abc import Iterable, Mapping

from .contract import UPSTREAM, authority_ceiling, canonical_json_bytes, validate_authority_claims

OUT_COLUMNS = ("submission_id", "task", "speed_kmh", "flow_vph", "queue_pred", "path_flow")
KEYS = {
    "state": ("panel", "timestamp", "station_id", "link_id", "mask_regime"),
    "queue": ("window_id", "timestamp", "link_id"),
    "odme": ("panel", "departure_time", "path_id"),
}
VALUES = {"state": ("speed_kmh", "flow_vph"), "queue": ("queue_pred",), "odme": ("path_flow",)}


def _key(row: Mapping[str, object], task: str) -> tuple[str, ...]:
    values: list[str] = []
    try:
        for column in KEYS[task]:
            raw = row[column]
            if raw is None or not str(raw).strip():
                raise ValueError(f"blank {task} natural key field: {column}")
            values.append(str(raw))
    except KeyError as exc:
        raise ValueError(f"missing {task} key field: {exc.args[0]}") from exc
    return tuple(values)


def _number(value: object, name: str, *, nonnegative: bool = True) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not numeric") from exc
    if not math.isfinite(out) or (nonnegative and out < 0):
        raise ValueError(f"{name} must be finite" + (" and non-negative" if nonnegative else ""))
    return out


def _table(rows: Iterable[Mapping[str, object]], task: str) -> dict[tuple[str, ...], tuple[float, ...]]:
    table: dict[tuple[str, ...], tuple[float, ...]] = {}
    for row in rows:
        key = _key(row, task)
        if key in table:
            raise ValueError(f"duplicate {task} natural key: {key}")
        vals = tuple(_number(row.get(column), column) for column in VALUES[task])
        if task == "state" and key[-1] not in {"R1", "R2", "R3"}:
            raise ValueError("mask_regime must be R1, R2, or R3")
        if task == "queue" and vals[0] not in (0.0, 1.0):
            raise ValueError("queue_pred must be 0 or 1")
        if task == "odme":
            for zone in ("origin_zone", "destination_zone"):
                raw = row.get(zone)
                if raw is None or not str(raw).strip():
                    raise ValueError(f"{zone} is required for ODME rows")
        table[key] = vals
    return table


def compile_submission(
    submission_key_rows: Iterable[Mapping[str, object]],
    *,
    state_rows: Iterable[Mapping[str, object]],
    queue_rows: Iterable[Mapping[str, object]],
    odme_rows: Iterable[Mapping[str, object]],
    require_complete: bool = True,
) -> tuple[str, dict[str, object]]:
    """Compile the official six-column merged shape without contacting Kaggle."""
    tables = {
        "state": _table(state_rows, "state"),
        "queue": _table(queue_rows, "queue"),
        "odme": _table(odme_rows, "odme"),
    }
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(OUT_COLUMNS), lineterminator="\n")
    writer.writeheader()
    seen_ids: set[int] = set()
    gaps = {task: 0 for task in tables}
    row_count = 0
    for row in submission_key_rows:
        task = str(row.get("task", ""))
        if task not in tables:
            raise ValueError(f"unknown task in submission key: {task!r}")
        try:
            sid = int(str(row["submission_id"]))
        except (KeyError, ValueError) as exc:
            raise ValueError("submission_id must be an integer") from exc
        if sid in seen_ids:
            raise ValueError(f"duplicate submission_id: {sid}")
        seen_ids.add(sid)
        key = _key(row, task)
        values = tables[task].get(key)
        if values is None:
            gaps[task] += 1
            if require_complete:
                raise ValueError(f"missing {task} value for key {key}")
            values = tuple(0.0 for _ in VALUES[task])
        out = {
            "submission_id": sid,
            "task": task,
            "speed_kmh": 0.0,
            "flow_vph": 0.0,
            "queue_pred": 0.0,
            "path_flow": 0.0,
        }
        for column, value in zip(VALUES[task], values):
            out[column] = value
        writer.writerow(out)
        row_count += 1
    if row_count == 0:
        raise ValueError("submission key is empty")
    payload = buffer.getvalue()
    receipt = {
        "schema": "trafficflowbench-local-submission/v1",
        "upstreamCommit": UPSTREAM["commit"],
        "rows": row_count,
        "gaps": gaps,
        "requireComplete": bool(require_complete),
        "csvSha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "authority": authority_ceiling(),
    }
    receipt["receiptSha256"] = hashlib.sha256(canonical_json_bytes(receipt)).hexdigest()
    return payload, receipt


def _receipt_digest(receipt: Mapping[str, object]) -> str:
    body = dict(receipt)
    body.pop("receiptSha256", None)
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def verify_compiled_submission(payload: str, receipt: Mapping[str, object]) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    if receipt.get("schema") != "trafficflowbench-local-submission/v1":
        return False
    if receipt.get("upstreamCommit") != UPSTREAM["commit"]:
        return False
    if receipt.get("receiptSha256") != _receipt_digest(receipt):
        return False
    authority = receipt.get("authority")
    if not isinstance(authority, Mapping):
        return False
    try:
        validate_authority_claims(authority)
    except (AttributeError, TypeError, ValueError):
        return False
    if hashlib.sha256(payload.encode("utf-8")).hexdigest() != receipt.get("csvSha256"):
        return False
    try:
        rows = list(csv.DictReader(io.StringIO(payload)))
    except csv.Error:
        return False
    if not rows or tuple(rows[0].keys()) != OUT_COLUMNS:
        return False
    try:
        if int(receipt.get("rows", -1)) != len(rows):
            return False
    except (TypeError, ValueError):
        return False
    gaps = receipt.get("gaps")
    if not isinstance(gaps, Mapping) or set(gaps) != set(KEYS):
        return False
    if receipt.get("requireComplete") is True and any(gaps.get(task) != 0 for task in KEYS):
        return False
    seen: set[int] = set()
    for row in rows:
        if any(row.get(column, "") == "" for column in OUT_COLUMNS):
            return False
        if row["task"] not in KEYS:
            return False
        try:
            sid = int(row["submission_id"])
        except ValueError:
            return False
        if sid in seen:
            return False
        seen.add(sid)
        try:
            speed, flow, queue, path = [float(row[c]) for c in ("speed_kmh", "flow_vph", "queue_pred", "path_flow")]
        except ValueError:
            return False
        values = [speed, flow, queue, path]
        if any(not math.isfinite(v) or v < 0 for v in values):
            return False
        if row["task"] == "state" and (queue != 0.0 or path != 0.0):
            return False
        if row["task"] == "queue" and (speed != 0.0 or flow != 0.0 or path != 0.0 or queue not in (0.0, 1.0)):
            return False
        if row["task"] == "odme" and (speed != 0.0 or flow != 0.0 or queue != 0.0):
            return False
    return True
