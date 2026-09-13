#!/usr/bin/env python3
"""Deterministic offline tracer-to-map provenance reconciliation core."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "wayne-glioma-tracer-provenance-rail/v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
BATCH_STATES = {"RELEASED", "REJECTED", "HOLD"}
SCAN_STATES = {"ACQUIRED", "FAILED"}
TIMING_STATES = {"ON_TIME", "DELAYED"}
HANDOFF_STATES = {"READY", "ACKED", "HOLD"}
PHI_KEYS = {
    "name", "first_name", "last_name", "patient_name", "patient_email", "patient_phone",
    "email", "phone", "address", "dob", "date_of_birth", "mrn", "medical_record_number",
    "ssn", "passport", "accession_patient_name", "birth_date", "sex", "gender",
}
COMMON = {"event_id", "type"}
FIELDS = {
    "subject": COMMON | {"subject_id", "protocol_version"},
    "batch": COMMON | {"batch_id", "synthesis_id", "tracer_code", "qc_hash", "release_state", "resynthesis_of"},
    "dose": COMMON | {"dose_id", "subject_id", "batch_id", "administered_at", "administered_activity_bq"},
    "scan": COMMON | {"accession_id", "subject_id", "dose_id", "acquired_at", "state", "timing_state", "retry_of"},
    "segmentation": COMMON | {"segmentation_id", "subject_id", "accession_id", "version", "artifact_hash", "parent_segmentation_id"},
    "map": COMMON | {"map_id", "subject_id", "accession_id", "segmentation_id", "version", "algorithm_version", "artifact_hash", "parent_map_id"},
    "handoff": COMMON | {"handoff_id", "subject_id", "map_id", "state", "destination_role", "observed_at"},
}


class RailError(ValueError):
    """Fail-closed validation error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise RailError(f"{label} must be a non-empty trimmed string")
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise RailError(f"{label} must be an integer >= {minimum}")
    return value


def _timestamp(value: Any, label: str) -> str:
    value = _text(value, label)
    if not TS.fullmatch(value):
        raise RailError(f"{label} must be UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise RailError(f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo is None:
        raise RailError(f"{label} must be timezone aware")
    return value


def _digest(value: Any, label: str) -> str:
    value = _text(value, label)
    if not HEX64.fullmatch(value):
        raise RailError(f"{label} must be lowercase SHA-256")
    return value


def _nullable_text(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _reject_phi(value: Any, path: str = "event") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise RailError(f"{path} contains non-string key")
            lowered = key.lower()
            if lowered in PHI_KEYS or lowered.startswith("patient_") or lowered.startswith("person_"):
                raise RailError(f"PHI field forbidden: {path}.{key}")
            _reject_phi(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            _reject_phi(child, f"{path}[{i}]")


def _normalize(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise RailError("each event must be an object")
    _reject_phi(raw)
    event = dict(raw)
    event_id = _text(event.get("event_id"), "event_id")
    kind = _text(event.get("type"), f"{event_id}.type")
    if kind not in FIELDS:
        raise RailError(f"{event_id}: unknown event type {kind}")
    missing = FIELDS[kind] - set(event)
    extra = set(event) - FIELDS[kind]
    if missing or extra:
        raise RailError(f"{event_id}: schema mismatch missing={sorted(missing)} extra={sorted(extra)}")

    if kind == "subject":
        _text(event["subject_id"], f"{event_id}.subject_id")
        _integer(event["protocol_version"], f"{event_id}.protocol_version", 1)
    elif kind == "batch":
        _text(event["batch_id"], f"{event_id}.batch_id")
        _text(event["synthesis_id"], f"{event_id}.synthesis_id")
        _text(event["tracer_code"], f"{event_id}.tracer_code")
        _digest(event["qc_hash"], f"{event_id}.qc_hash")
        if event["release_state"] not in BATCH_STATES:
            raise RailError(f"{event_id}: invalid release_state")
        event["resynthesis_of"] = _nullable_text(event["resynthesis_of"], f"{event_id}.resynthesis_of")
    elif kind == "dose":
        _text(event["dose_id"], f"{event_id}.dose_id")
        _text(event["subject_id"], f"{event_id}.subject_id")
        _text(event["batch_id"], f"{event_id}.batch_id")
        _timestamp(event["administered_at"], f"{event_id}.administered_at")
        _integer(event["administered_activity_bq"], f"{event_id}.administered_activity_bq", 1)
    elif kind == "scan":
        _text(event["accession_id"], f"{event_id}.accession_id")
        _text(event["subject_id"], f"{event_id}.subject_id")
        _text(event["dose_id"], f"{event_id}.dose_id")
        _timestamp(event["acquired_at"], f"{event_id}.acquired_at")
        if event["state"] not in SCAN_STATES or event["timing_state"] not in TIMING_STATES:
            raise RailError(f"{event_id}: invalid scan state/timing_state")
        event["retry_of"] = _nullable_text(event["retry_of"], f"{event_id}.retry_of")
    elif kind == "segmentation":
        _text(event["segmentation_id"], f"{event_id}.segmentation_id")
        _text(event["subject_id"], f"{event_id}.subject_id")
        _text(event["accession_id"], f"{event_id}.accession_id")
        _integer(event["version"], f"{event_id}.version", 1)
        _digest(event["artifact_hash"], f"{event_id}.artifact_hash")
        event["parent_segmentation_id"] = _nullable_text(event["parent_segmentation_id"], f"{event_id}.parent_segmentation_id")
    elif kind == "map":
        _text(event["map_id"], f"{event_id}.map_id")
        _text(event["subject_id"], f"{event_id}.subject_id")
        _text(event["accession_id"], f"{event_id}.accession_id")
        _text(event["segmentation_id"], f"{event_id}.segmentation_id")
        _integer(event["version"], f"{event_id}.version", 1)
        _text(event["algorithm_version"], f"{event_id}.algorithm_version")
        _digest(event["artifact_hash"], f"{event_id}.artifact_hash")
        event["parent_map_id"] = _nullable_text(event["parent_map_id"], f"{event_id}.parent_map_id")
    elif kind == "handoff":
        _text(event["handoff_id"], f"{event_id}.handoff_id")
        _text(event["subject_id"], f"{event_id}.subject_id")
        _text(event["map_id"], f"{event_id}.map_id")
        if event["state"] not in HANDOFF_STATES:
            raise RailError(f"{event_id}: invalid handoff state")
        _text(event["destination_role"], f"{event_id}.destination_role")
        _timestamp(event["observed_at"], f"{event_id}.observed_at")
    return event


def _unique_events(raw_events: Iterable[Any]) -> tuple[list[dict[str, Any]], int]:
    by_id: dict[str, dict[str, Any]] = {}
    encoded: dict[str, bytes] = {}
    retries = 0
    for raw in raw_events:
        event = _normalize(raw)
        eid = event["event_id"]
        blob = canonical_bytes(event)
        if eid in by_id:
            if encoded[eid] != blob:
                raise RailError(f"conflicting duplicate event_id: {eid}")
            retries += 1
            continue
        by_id[eid] = event
        encoded[eid] = blob
    return [by_id[k] for k in sorted(by_id)], retries


def _one_by_entity(events: Iterable[dict[str, Any]], kind: str, key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["type"] != kind:
            continue
        entity_id = event[key]
        if entity_id in out:
            raise RailError(f"duplicate {key}: {entity_id}")
        out[entity_id] = event
    return out


def _quarantine(reviewer: str, event: Mapping[str, Any], reason: str, **detail: Any) -> dict[str, Any]:
    row = {
        "event_id": event["event_id"],
        "event_type": event["type"],
        "reason": reason,
        "owner_role": reviewer,
    }
    row.update(detail)
    return row


def reconcile(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical custody manifest for approved/synthetic events."""
    if not isinstance(payload, Mapping):
        raise RailError("payload must be an object")
    allowed = {"review_owner_role", "events"}
    if set(payload) != allowed:
        raise RailError(f"payload schema mismatch missing={sorted(allowed-set(payload))} extra={sorted(set(payload)-allowed)}")
    reviewer = _text(payload["review_owner_role"], "review_owner_role")
    if not isinstance(payload["events"], list) or not payload["events"]:
        raise RailError("events must be a non-empty list")
    events, retry_count = _unique_events(payload["events"])

    subjects = _one_by_entity(events, "subject", "subject_id")
    batches = _one_by_entity(events, "batch", "batch_id")
    doses = _one_by_entity(events, "dose", "dose_id")
    scans = _one_by_entity(events, "scan", "accession_id")
    segmentations = _one_by_entity(events, "segmentation", "segmentation_id")
    maps = _one_by_entity(events, "map", "map_id")
    handoffs = _one_by_entity(events, "handoff", "handoff_id")
    if not subjects:
        raise RailError("at least one subject is required")

    # Batch resynthesis is structural provenance: unknown/cyclic/cross-tracer parents are invalid bytes.
    synthesis_ids: set[str] = set()
    for batch_id, row in batches.items():
        if row["synthesis_id"] in synthesis_ids:
            raise RailError(f"duplicate synthesis_id: {row['synthesis_id']}")
        synthesis_ids.add(row["synthesis_id"])
        parent = row["resynthesis_of"]
        if parent is not None:
            if parent not in batches:
                raise RailError(f"{batch_id}: unknown resynthesis parent")
            if batches[parent]["tracer_code"] != row["tracer_code"]:
                raise RailError(f"{batch_id}: resynthesis tracer mismatch")
            seen = {batch_id}
            current = parent
            while current is not None:
                if current in seen:
                    raise RailError(f"{batch_id}: resynthesis cycle")
                seen.add(current)
                current = batches[current]["resynthesis_of"]

    quarantine: list[dict[str, Any]] = []
    valid_doses: dict[str, dict[str, Any]] = {}
    for dose_id, row in sorted(doses.items()):
        subject = subjects.get(row["subject_id"])
        batch = batches.get(row["batch_id"])
        if subject is None:
            quarantine.append(_quarantine(reviewer, row, "UNKNOWN_SUBJECT", subject_id=row["subject_id"]))
        elif batch is None:
            quarantine.append(_quarantine(reviewer, row, "UNKNOWN_BATCH", batch_id=row["batch_id"], subject_id=row["subject_id"]))
        elif batch["release_state"] != "RELEASED":
            quarantine.append(_quarantine(reviewer, row, "BATCH_NOT_RELEASED", batch_id=row["batch_id"], subject_id=row["subject_id"]))
        else:
            valid_doses[dose_id] = row

    valid_scans: dict[str, dict[str, Any]] = {}
    for accession_id, row in sorted(scans.items()):
        subject = subjects.get(row["subject_id"])
        dose = valid_doses.get(row["dose_id"])
        if subject is None:
            quarantine.append(_quarantine(reviewer, row, "UNKNOWN_SUBJECT", subject_id=row["subject_id"]))
            continue
        if dose is None:
            quarantine.append(_quarantine(reviewer, row, "DOSE_NOT_ACCEPTED", dose_id=row["dose_id"], subject_id=row["subject_id"]))
            continue
        if dose["subject_id"] != row["subject_id"]:
            quarantine.append(_quarantine(reviewer, row, "CROSS_SUBJECT_DOSE_SCAN", dose_id=row["dose_id"], subject_id=row["subject_id"]))
            continue
        if row["retry_of"] is not None:
            parent = scans.get(row["retry_of"])
            if parent is None:
                quarantine.append(_quarantine(reviewer, row, "UNKNOWN_SCAN_RETRY_PARENT", retry_of=row["retry_of"], subject_id=row["subject_id"]))
                continue
            if parent["subject_id"] != row["subject_id"] or parent["dose_id"] != row["dose_id"]:
                quarantine.append(_quarantine(reviewer, row, "SCAN_RETRY_LINEAGE_MISMATCH", retry_of=row["retry_of"], subject_id=row["subject_id"]))
                continue
            if parent["state"] != "FAILED":
                quarantine.append(_quarantine(reviewer, row, "RETRY_PARENT_NOT_FAILED", retry_of=row["retry_of"], subject_id=row["subject_id"]))
                continue
        if row["state"] == "ACQUIRED":
            valid_scans[accession_id] = row

    # Segmentation/map structural versions are validated only within accepted same-subject lineage.
    candidate_seg: dict[str, dict[str, Any]] = {}
    for seg_id, row in sorted(segmentations.items()):
        subject = subjects.get(row["subject_id"])
        scan = valid_scans.get(row["accession_id"])
        if subject is None:
            quarantine.append(_quarantine(reviewer, row, "UNKNOWN_SUBJECT", subject_id=row["subject_id"]))
        elif scan is None:
            quarantine.append(_quarantine(reviewer, row, "SCAN_NOT_ACCEPTED", accession_id=row["accession_id"], subject_id=row["subject_id"]))
        elif scan["subject_id"] != row["subject_id"]:
            quarantine.append(_quarantine(reviewer, row, "CROSS_SUBJECT_SCAN_SEGMENTATION", accession_id=row["accession_id"], subject_id=row["subject_id"]))
        else:
            candidate_seg[seg_id] = row

    seg_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_seg.values():
        seg_groups[(row["subject_id"], row["accession_id"])].append(row)
    valid_seg: dict[str, dict[str, Any]] = {}
    latest_seg_by_scan: dict[tuple[str, str], str] = {}
    for key, rows in sorted(seg_groups.items()):
        rows.sort(key=lambda r: (r["version"], r["segmentation_id"]))
        if [r["version"] for r in rows] != list(range(1, len(rows) + 1)):
            raise RailError(f"{key[0]}/{key[1]}: segmentation versions must be contiguous from 1")
        previous = None
        for row in rows:
            if row["parent_segmentation_id"] != previous:
                raise RailError(f"{row['segmentation_id']}: segmentation parent mismatch")
            valid_seg[row["segmentation_id"]] = row
            previous = row["segmentation_id"]
        latest_seg_by_scan[key] = rows[-1]["segmentation_id"]

    candidate_maps: dict[str, dict[str, Any]] = {}
    for map_id, row in sorted(maps.items()):
        subject = subjects.get(row["subject_id"])
        scan = valid_scans.get(row["accession_id"])
        seg = valid_seg.get(row["segmentation_id"])
        if subject is None:
            quarantine.append(_quarantine(reviewer, row, "UNKNOWN_SUBJECT", subject_id=row["subject_id"]))
        elif scan is None:
            quarantine.append(_quarantine(reviewer, row, "SCAN_NOT_ACCEPTED", accession_id=row["accession_id"], subject_id=row["subject_id"]))
        elif scan["subject_id"] != row["subject_id"]:
            quarantine.append(_quarantine(reviewer, row, "CROSS_SUBJECT_SCAN_MAP", accession_id=row["accession_id"], subject_id=row["subject_id"]))
        elif seg is None:
            quarantine.append(_quarantine(reviewer, row, "SEGMENTATION_NOT_ACCEPTED", segmentation_id=row["segmentation_id"], subject_id=row["subject_id"]))
        elif seg["subject_id"] != row["subject_id"] or seg["accession_id"] != row["accession_id"]:
            quarantine.append(_quarantine(reviewer, row, "CROSS_SUBJECT_OR_SCAN_SEGMENTATION_MAP", segmentation_id=row["segmentation_id"], subject_id=row["subject_id"]))
        else:
            candidate_maps[map_id] = row

    map_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_maps.values():
        map_groups[(row["subject_id"], row["accession_id"])].append(row)
    valid_maps: dict[str, dict[str, Any]] = {}
    latest_map_by_scan: dict[tuple[str, str], str] = {}
    for key, rows in sorted(map_groups.items()):
        rows.sort(key=lambda r: (r["version"], r["map_id"]))
        if [r["version"] for r in rows] != list(range(1, len(rows) + 1)):
            raise RailError(f"{key[0]}/{key[1]}: map versions must be contiguous from 1")
        previous = None
        for row in rows:
            if row["parent_map_id"] != previous:
                raise RailError(f"{row['map_id']}: map parent mismatch")
            valid_maps[row["map_id"]] = row
            previous = row["map_id"]
        latest_map_by_scan[key] = rows[-1]["map_id"]

    # Accepted handoffs may point only to the latest accepted map for that subject/accession.
    valid_handoffs: dict[str, dict[str, Any]] = {}
    for handoff_id, row in sorted(handoffs.items()):
        subject = subjects.get(row["subject_id"])
        map_row = valid_maps.get(row["map_id"])
        if subject is None:
            quarantine.append(_quarantine(reviewer, row, "UNKNOWN_SUBJECT", subject_id=row["subject_id"]))
        elif map_row is None:
            quarantine.append(_quarantine(reviewer, row, "MAP_NOT_ACCEPTED", map_id=row["map_id"], subject_id=row["subject_id"]))
        elif map_row["subject_id"] != row["subject_id"]:
            quarantine.append(_quarantine(reviewer, row, "CROSS_SUBJECT_MAP_HANDOFF", map_id=row["map_id"], subject_id=row["subject_id"]))
        elif latest_map_by_scan[(map_row["subject_id"], map_row["accession_id"])] != row["map_id"]:
            quarantine.append(_quarantine(reviewer, row, "HANDOFF_NOT_LATEST_MAP", map_id=row["map_id"], subject_id=row["subject_id"]))
        else:
            valid_handoffs[handoff_id] = row

    # Accepted lineage is built only from internally consistent same-subject edges.
    dose_by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    scans_by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seg_by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    maps_by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    handoff_by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in valid_doses.values(): dose_by_subject[row["subject_id"]].append(row)
    for row in valid_scans.values(): scans_by_subject[row["subject_id"]].append(row)
    for row in valid_seg.values(): seg_by_subject[row["subject_id"]].append(row)
    for row in valid_maps.values(): maps_by_subject[row["subject_id"]].append(row)
    for row in valid_handoffs.values(): handoff_by_subject[row["subject_id"]].append(row)

    episode_rows: list[dict[str, Any]] = []
    complete_episode_count = 0
    for subject_id in sorted(subjects):
        accepted_doses = sorted(dose_by_subject[subject_id], key=lambda r: (r["administered_at"], r["dose_id"]))
        accepted_scans = sorted(scans_by_subject[subject_id], key=lambda r: (r["acquired_at"], r["accession_id"]))
        accepted_seg = sorted(seg_by_subject[subject_id], key=lambda r: (r["accession_id"], r["version"], r["segmentation_id"]))
        accepted_maps = sorted(maps_by_subject[subject_id], key=lambda r: (r["accession_id"], r["version"], r["map_id"]))
        accepted_handoffs = sorted(handoff_by_subject[subject_id], key=lambda r: (r["observed_at"], r["handoff_id"]))
        complete = bool(accepted_doses and accepted_scans and accepted_seg and accepted_maps and accepted_handoffs)
        if complete:
            complete_episode_count += 1
        episode_rows.append({
            "subject_id": subject_id,
            "protocol_version": subjects[subject_id]["protocol_version"],
            "complete_lineage": complete,
            "dose_ids": [r["dose_id"] for r in accepted_doses],
            "accession_ids": [r["accession_id"] for r in accepted_scans],
            "segmentation_ids": [r["segmentation_id"] for r in accepted_seg],
            "map_ids": [r["map_id"] for r in accepted_maps],
            "handoff_ids": [r["handoff_id"] for r in accepted_handoffs],
        })

    batch_rows = []
    for batch_id, row in sorted(batches.items()):
        chain = []
        current: str | None = batch_id
        while current is not None:
            chain.append(current)
            current = batches[current]["resynthesis_of"]
        batch_rows.append({
            "batch_id": batch_id,
            "synthesis_id": row["synthesis_id"],
            "tracer_code": row["tracer_code"],
            "qc_hash": row["qc_hash"],
            "release_state": row["release_state"],
            "resynthesis_chain": chain,
        })

    map_rows = []
    for map_id, row in sorted(valid_maps.items()):
        seg = valid_seg[row["segmentation_id"]]
        scan = valid_scans[row["accession_id"]]
        dose = valid_doses[scan["dose_id"]]
        batch = batches[dose["batch_id"]]
        map_rows.append({
            "map_id": map_id,
            "subject_id": row["subject_id"],
            "version": row["version"],
            "artifact_hash": row["artifact_hash"],
            "algorithm_version": row["algorithm_version"],
            "segmentation_id": row["segmentation_id"],
            "segmentation_hash": seg["artifact_hash"],
            "accession_id": row["accession_id"],
            "scan_timing_state": scan["timing_state"],
            "dose_id": scan["dose_id"],
            "batch_id": dose["batch_id"],
            "qc_hash": batch["qc_hash"],
        })

    # This remains zero by construction: inconsistent edges are quarantined before lineage materialization.
    cross_subject_association_count = 0
    quarantine.sort(key=canonical_bytes)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "authority": {
            "diagnose": False,
            "classify_recurrence": False,
            "recommend_treatment": False,
            "decide_dose": False,
            "release_tracer_batch": False,
            "approve_clinical_handoff": False,
        },
        "privacy": {"phi_allowed": False, "accepted_identity": "pseudonymous-study-id-only"},
        "source_event_count": len(events),
        "retry_event_count": retry_count,
        "subject_count": len(subjects),
        "complete_episode_count": complete_episode_count,
        "batch_count": len(batches),
        "accepted_dose_count": len(valid_doses),
        "accepted_scan_count": len(valid_scans),
        "accepted_segmentation_count": len(valid_seg),
        "accepted_map_count": len(valid_maps),
        "accepted_handoff_count": len(valid_handoffs),
        "cross_subject_association_count": cross_subject_association_count,
        "quarantine_count": len(quarantine),
        "quarantine": quarantine,
        "batches": batch_rows,
        "episodes": episode_rows,
        "maps": map_rows,
    }
    manifest["manifest_sha256"] = hash_value(manifest)
    return manifest


def receipt_for(manifest: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(manifest, Mapping) or "manifest_sha256" not in manifest:
        raise RailError("manifest missing manifest_sha256")
    unsigned = dict(manifest)
    claimed = unsigned.pop("manifest_sha256")
    if claimed != hash_value(unsigned):
        raise RailError("manifest hash mismatch")
    receipt = {"schema_version": SCHEMA_VERSION, "manifest_sha256": claimed}
    receipt["receipt_sha256"] = hash_value(receipt)
    return receipt


def verify_receipt(manifest: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    return dict(receipt) == receipt_for(manifest)


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("input")
    build.add_argument("--manifest", required=True)
    build.add_argument("--receipt", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("manifest")
    verify.add_argument("receipt")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            manifest = reconcile(_load(args.input))
            receipt = receipt_for(manifest)
            Path(args.manifest).write_bytes(canonical_bytes(manifest) + b"\n")
            Path(args.receipt).write_bytes(canonical_bytes(receipt) + b"\n")
            print(json.dumps({
                "ok": True,
                "subject_count": manifest["subject_count"],
                "complete_episode_count": manifest["complete_episode_count"],
                "quarantine_count": manifest["quarantine_count"],
                "manifest_sha256": manifest["manifest_sha256"],
            }, sort_keys=True))
            return 0
        ok = verify_receipt(_load(args.manifest), _load(args.receipt))
        print(json.dumps({"ok": ok}, sort_keys=True))
        return 0 if ok else 2
    except (OSError, json.JSONDecodeError, RailError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
