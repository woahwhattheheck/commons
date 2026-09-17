from __future__ import annotations

import csv
import hashlib
import io
import math
from collections.abc import Iterable, Mapping

from .contract import UPSTREAM, canonical_json_bytes

OUT_COLUMNS = ("submission_id", "task", "speed_kmh", "flow_vph", "queue_pred", "path_flow")
KEYS = {
    "state": ("panel", "timestamp", "station_id", "link_id", "mask_regime"),
    "queue": ("window_id", "timestamp", "link_id"),
    "odme": ("panel", "departure_time", "path_id"),
}
VALUES = {"state": ("speed_kmh", "flow_vph"), "queue": ("queue_pred",), "odme": ("path_flow",)}
_RECEIPT_SCHEMA = "trafficflowbench-local-submission/v2"
_BINDING_SCHEMA = "trafficflowbench-local-submission-input/v1"
_AUTHORITY = {
    "submissionSent": False,
    "officialScoreEstablished": False,
    "leaderboardRankEstablished": False,
    "prizeAwarded": False,
    "paymentReceived": False,
}
_RECEIPT_KEYS = {
    "schema",
    "upstreamCommit",
    "rows",
    "gaps",
    "requireComplete",
    "csvSha256",
    "compileInputSha256",
    "compilerContractSha256",
    "authority",
    "receiptSha256",
}


def _key(row: Mapping[str, object], task: str) -> tuple[str, ...]:
    try:
        values = tuple(str(row[column]) for column in KEYS[task])
    except KeyError as exc:
        raise ValueError(f"missing {task} key field: {exc.args[0]}") from exc
    if any(not value for value in values):
        raise ValueError(f"blank {task} natural key")
    return values


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
        if task == "queue" and vals[0] not in (0.0, 1.0):
            raise ValueError("queue_pred must be 0 or 1")
        table[key] = vals
    return table


def _sha256_hex(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _compiler_contract_sha256() -> str:
    contract = {
        "schema": _RECEIPT_SCHEMA,
        "upstreamCommit": UPSTREAM["commit"],
        "outColumns": OUT_COLUMNS,
        "keys": KEYS,
        "values": VALUES,
        "authority": _AUTHORITY,
        "completeDefault": True,
    }
    return hashlib.sha256(canonical_json_bytes(contract)).hexdigest()


def _semantic_input_binding(
    key_rows: list[Mapping[str, object]],
    tables: Mapping[str, Mapping[tuple[str, ...], tuple[float, ...]]],
    *,
    require_complete: bool,
) -> tuple[list[tuple[int, str, tuple[str, ...]]], str]:
    ordered_keys: list[tuple[int, str, tuple[str, ...]]] = []
    seen_ids: set[int] = set()
    for row in key_rows:
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
        ordered_keys.append((sid, task, _key(row, task)))
    if not ordered_keys:
        raise ValueError("submission key is empty")
    binding = {
        "schema": _BINDING_SCHEMA,
        "upstreamCommit": UPSTREAM["commit"],
        "requireComplete": require_complete,
        "submissionKey": [
            {"submission_id": sid, "task": task, "naturalKey": key}
            for sid, task, key in ordered_keys
        ],
        "taskValues": {
            task: [
                {"naturalKey": key, "values": values}
                for key, values in sorted(tables[task].items())
            ]
            for task in sorted(tables)
        },
    }
    digest = hashlib.sha256(canonical_json_bytes(binding)).hexdigest()
    return ordered_keys, digest


def compile_submission(
    submission_key_rows: Iterable[Mapping[str, object]],
    *,
    state_rows: Iterable[Mapping[str, object]],
    queue_rows: Iterable[Mapping[str, object]],
    odme_rows: Iterable[Mapping[str, object]],
    require_complete: bool = True,
) -> tuple[str, dict[str, object]]:
    """Compile the official six-column merged shape without contacting Kaggle."""
    if type(require_complete) is not bool:
        raise ValueError("require_complete must be a bool")
    key_rows = list(submission_key_rows)
    tables = {
        "state": _table(list(state_rows), "state"),
        "queue": _table(list(queue_rows), "queue"),
        "odme": _table(list(odme_rows), "odme"),
    }
    ordered_keys, input_digest = _semantic_input_binding(
        key_rows, tables, require_complete=require_complete
    )

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(OUT_COLUMNS), lineterminator="\n")
    writer.writeheader()
    gaps = {task: 0 for task in tables}
    for sid, task, key in ordered_keys:
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

    payload = buffer.getvalue()
    receipt = {
        "schema": _RECEIPT_SCHEMA,
        "upstreamCommit": UPSTREAM["commit"],
        "rows": len(ordered_keys),
        "gaps": gaps,
        "requireComplete": require_complete,
        "csvSha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "compileInputSha256": input_digest,
        "compilerContractSha256": _compiler_contract_sha256(),
        "authority": dict(_AUTHORITY),
    }
    receipt["receiptSha256"] = hashlib.sha256(canonical_json_bytes(receipt)).hexdigest()
    return payload, receipt


def _receipt_semantics_valid(receipt: Mapping[str, object]) -> bool:
    if set(receipt) != _RECEIPT_KEYS:
        return False
    if receipt.get("schema") != _RECEIPT_SCHEMA or receipt.get("upstreamCommit") != UPSTREAM["commit"]:
        return False
    if type(receipt.get("rows")) is not int or receipt["rows"] <= 0:
        return False
    if type(receipt.get("requireComplete")) is not bool:
        return False
    if not all(
        _sha256_hex(receipt.get(name))
        for name in ("csvSha256", "compileInputSha256", "compilerContractSha256", "receiptSha256")
    ):
        return False
    if receipt.get("compilerContractSha256") != _compiler_contract_sha256():
        return False
    gaps = receipt.get("gaps")
    if type(gaps) is not dict or set(gaps) != set(KEYS):
        return False
    if any(type(gaps[task]) is not int or gaps[task] < 0 for task in KEYS):
        return False
    if receipt["requireComplete"] and any(gaps.values()):
        return False
    authority = receipt.get("authority")
    if type(authority) is not dict or set(authority) != set(_AUTHORITY):
        return False
    if any(type(authority[key]) is not bool or authority[key] is not False for key in _AUTHORITY):
        return False
    body = dict(receipt)
    claimed = body.pop("receiptSha256")
    if hashlib.sha256(canonical_json_bytes(body)).hexdigest() != claimed:
        return False
    return True


def _payload_semantics_valid(payload: str, receipt: Mapping[str, object]) -> bool:
    if hashlib.sha256(payload.encode("utf-8")).hexdigest() != receipt["csvSha256"]:
        return False
    try:
        reader = csv.DictReader(io.StringIO(payload))
        if tuple(reader.fieldnames or ()) != OUT_COLUMNS:
            return False
        rows = list(reader)
    except (csv.Error, TypeError):
        return False
    if len(rows) != receipt["rows"]:
        return False
    seen: set[int] = set()
    for row in rows:
        if set(row) != set(OUT_COLUMNS):
            return False
        if any(type(row.get(column)) is not str or row[column] == "" for column in OUT_COLUMNS):
            return False
        try:
            sid = int(row["submission_id"])
        except ValueError:
            return False
        if str(sid) != row["submission_id"] or sid in seen:
            return False
        seen.add(sid)
        task = row["task"]
        if task not in KEYS:
            return False
        try:
            values = {
                c: float(row[c])
                for c in ("speed_kmh", "flow_vph", "queue_pred", "path_flow")
            }
        except ValueError:
            return False
        if any(not math.isfinite(v) or v < 0 for v in values.values()):
            return False
        if task == "state":
            if values["queue_pred"] != 0.0 or values["path_flow"] != 0.0:
                return False
        elif task == "queue":
            if (
                values["speed_kmh"] != 0.0
                or values["flow_vph"] != 0.0
                or values["path_flow"] != 0.0
                or values["queue_pred"] not in (0.0, 1.0)
            ):
                return False
        else:
            if (
                values["speed_kmh"] != 0.0
                or values["flow_vph"] != 0.0
                or values["queue_pred"] != 0.0
            ):
                return False
    return True


def verify_compiled_submission(
    payload: str,
    receipt: Mapping[str, object],
    *,
    submission_key_rows: Iterable[Mapping[str, object]] | None = None,
    state_rows: Iterable[Mapping[str, object]] | None = None,
    queue_rows: Iterable[Mapping[str, object]] | None = None,
    odme_rows: Iterable[Mapping[str, object]] | None = None,
) -> bool:
    """Verify receipt/payload semantics and exact-recompile from trusted compile inputs.

    The four compile-input arguments are mandatory evidence. A payload plus its
    self-authored receipt is insufficient to establish provenance.
    """
    if type(payload) is not str or not isinstance(receipt, Mapping):
        return False
    if not _receipt_semantics_valid(receipt) or not _payload_semantics_valid(payload, receipt):
        return False
    if any(
        item is None
        for item in (submission_key_rows, state_rows, queue_rows, odme_rows)
    ):
        return False
    try:
        expected_payload, expected_receipt = compile_submission(
            submission_key_rows,
            state_rows=state_rows,
            queue_rows=queue_rows,
            odme_rows=odme_rows,
            require_complete=receipt["requireComplete"],
        )
    except (TypeError, ValueError):
        return False
    return payload == expected_payload and dict(receipt) == expected_receipt
