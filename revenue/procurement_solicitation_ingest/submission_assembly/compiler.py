"""Pure deterministic submission assembly compilation and verification."""
from __future__ import annotations

import copy
from pathlib import PurePosixPath
from typing import Any, Callable, Mapping

from .schema import (
    ArtifactCustodyError, AssemblyError, AUTHORITY, CONFLICT, DEADLINE, MANIFEST_SCHEMA,
    MAX_ARTIFACT_BYTES, MISSING, READY, RECEIPT_SCHEMA, TRUTH_BOUNDARY, canon,
    normalize_input, sha256,
)

def _public_generation(g: Mapping[str, Any]) -> dict[str, Any]:
    return {k: copy.deepcopy(v) for k, v in g.items() if not k.startswith("_")}


def _slot_map(slots: list[dict[str, Any]]):
    out = {}
    duplicates = []
    for slot in slots:
        if slot["slot_id"] in out:
            duplicates.append(slot["slot_id"])
        else:
            out[slot["slot_id"]] = slot
    return out, sorted(set(duplicates))


def _instruction_changes(prev: dict[str, Any] | None, latest: dict[str, Any]) -> list[dict[str, Any]]:
    if prev is None:
        return []
    before, _ = _slot_map(prev["slots"])
    after, _ = _slot_map(latest["slots"])
    changes = []
    all_ids = sorted(set(before) | set(after))
    fields = [
        "required", "order", "file_name", "formats", "max_pages", "max_bytes",
        "signature_requirement", "certification_requirement", "attachment_class",
        "portal_field", "section_id",
    ]
    for slot_id in all_ids:
        if slot_id not in before:
            changes.append({"slot_id": slot_id, "change": "ADDED", "fields": []})
            continue
        if slot_id not in after:
            changes.append({"slot_id": slot_id, "change": "REMOVED", "fields": []})
            continue
        changed_fields = [name for name in fields if before[slot_id][name] != after[slot_id][name]]
        if changed_fields:
            changes.append({"slot_id": slot_id, "change": "MODIFIED", "fields": changed_fields})
    if prev["deadline_at"] != latest["deadline_at"]:
        changes.append({"slot_id": "__deadline__", "change": "MODIFIED", "fields": ["deadline_at"]})
    return changes


def _artifact_index(artifacts: list[dict[str, Any]]):
    ids = set()
    by_slot: dict[str, list[dict[str, Any]]] = {}
    conflicts = []
    for artifact in artifacts:
        if artifact["artifact_id"] in ids:
            conflicts.append(f"duplicate artifact_id:{artifact['artifact_id']}")
        ids.add(artifact["artifact_id"])
        by_slot.setdefault(artifact["slot_id"], []).append(artifact)
    return by_slot, conflicts


def _attestation_present(artifact: dict[str, Any], kind: str) -> bool:
    return any(a["type"] == kind for a in artifact["attestations"])


def _check_artifact(slot: dict[str, Any], artifact: dict[str, Any], actual: bytes | ArtifactCustodyError | None):
    reasons: list[str] = []
    if isinstance(actual, ArtifactCustodyError):
        reasons.append(f"artifact custody:{actual}")
        actual_bytes = None
    else:
        actual_bytes = actual
    if actual_bytes is None:
        reasons.append("artifact bytes unavailable")
        actual_size = None
    else:
        actual_size = len(actual_bytes)
        if actual_size > MAX_ARTIFACT_BYTES:
            reasons.append("artifact exceeds global byte cap")
        if sha256(actual_bytes) != artifact["sha256"]:
            reasons.append("artifact digest does not match bytes read")
    if slot["file_name"] is not None and PurePosixPath(artifact["path"]).name != slot["file_name"]:
        reasons.append("buyer filename requirement mismatch")
    if slot["formats"] and artifact["format"] not in slot["formats"]:
        reasons.append("buyer format requirement mismatch")
    if slot["max_bytes"] is not None:
        if actual_size is None:
            reasons.append("cannot verify buyer byte limit")
        elif actual_size > slot["max_bytes"]:
            reasons.append("buyer byte limit exceeded")
    if slot["max_pages"] is not None:
        if artifact["pages"] is None:
            reasons.append("page count evidence missing")
        elif artifact["pages"] > slot["max_pages"]:
            reasons.append("buyer page limit exceeded")
    sig_req = slot["signature_requirement"]
    if sig_req in {"SIGNATURE_PRESENT_REQUIRED", "AUTHORIZED_SIGNATORY_REVIEW_REQUIRED"} and not _attestation_present(artifact, "SIGNATURE_PRESENT"):
        reasons.append("signature-present evidence missing")
    if sig_req == "NOTARIZATION_PRESENT_REQUIRED" and not _attestation_present(artifact, "NOTARIZATION_PRESENT"):
        reasons.append("notarization-present evidence missing")
    if slot["certification_requirement"] == "CERTIFICATION_PRESENT_REQUIRED" and not _attestation_present(artifact, "CERTIFICATION_PRESENT"):
        reasons.append("certification-present evidence missing")
    return reasons, actual_size


def compile_manifest(raw_input: bytes, artifact_loader: Callable[[dict[str, Any]], bytes] | None = None):
    normalized = normalize_input(raw_input)
    evaluated = normalized["_evaluated_utc"]
    generations = normalized["source_generations"]
    artifacts = normalized["artifacts"]

    conflicts: list[str] = []
    missing: list[str] = []

    prior_seq = None
    prior_observed = None
    source_ids = set()
    source_shas = set()
    for generation in generations:
        if generation["source_id"] in source_ids:
            conflicts.append(f"duplicate source_id:{generation['source_id']}")
        source_ids.add(generation["source_id"])
        if generation["source_sha256"] in source_shas:
            conflicts.append(f"duplicate source_sha256:{generation['source_sha256']}")
        source_shas.add(generation["source_sha256"])
        if generation["_future_source"]:
            conflicts.append(f"future source generation:{generation['source_id']}")
        if prior_seq is not None and generation["sequence"] <= prior_seq:
            conflicts.append("source generation sequence is not strictly increasing")
        if prior_observed is not None and generation["_observed_utc"] <= prior_observed:
            conflicts.append("source generation observed_at is not strictly increasing")
        prior_seq = generation["sequence"]
        prior_observed = generation["_observed_utc"]
        _, dup_slots = _slot_map(generation["slots"])
        for slot_id in dup_slots:
            conflicts.append(f"duplicate slot_id in source generation {generation['source_id']}:{slot_id}")

    latest = generations[-1]
    previous = generations[-2] if len(generations) > 1 else None
    latest_slot_map, latest_dups = _slot_map(latest["slots"])
    for slot_id in latest_dups:
        conflicts.append(f"latest generation duplicate slot:{slot_id}")

    by_slot, artifact_index_conflicts = _artifact_index(artifacts)
    conflicts.extend(artifact_index_conflicts)
    for slot_id, rows in by_slot.items():
        if slot_id not in latest_slot_map:
            conflicts.append(f"artifact targets non-current slot:{slot_id}")
        if len(rows) > 1:
            conflicts.append(f"multiple candidate artifacts for slot:{slot_id}")

    slot_rows = []
    worklist = []
    for slot_id in sorted(latest_slot_map, key=lambda key: ((latest_slot_map[key]["order"] is None), latest_slot_map[key]["order"] or 10**9, key)):
        slot = latest_slot_map[slot_id]
        candidates = by_slot.get(slot_id, [])
        artifact = candidates[0] if len(candidates) == 1 else None
        compliance_reasons: list[str] = []
        actual_size = None
        if artifact is not None:
            actual: bytes | ArtifactCustodyError | None
            if artifact_loader is None:
                actual = None
            else:
                try:
                    actual = artifact_loader(artifact)
                except ArtifactCustodyError as exc:
                    actual = exc
                except (OSError, AssemblyError) as exc:
                    actual = ArtifactCustodyError(str(exc))
            compliance_reasons, actual_size = _check_artifact(slot, artifact, actual)
            if compliance_reasons:
                conflicts.extend(f"slot {slot_id}: {reason}" for reason in compliance_reasons)
        elif slot["required"]:
            missing.append(slot_id)
            worklist.append({"slot_id": slot_id, "action": "PROVIDE_REQUIRED_ARTIFACT"})

        row = {
            "slot_id": slot_id,
            "required": slot["required"],
            "source_id": latest["source_id"],
            "source_sha256": latest["source_sha256"],
            "section_id": slot["section_id"],
            "constraints": {
                "order": slot["order"], "file_name": slot["file_name"], "formats": slot["formats"],
                "max_pages": slot["max_pages"], "max_bytes": slot["max_bytes"],
                "signature_requirement": slot["signature_requirement"],
                "certification_requirement": slot["certification_requirement"],
                "attachment_class": slot["attachment_class"], "portal_field": slot["portal_field"],
            },
            "candidate_artifact": None if artifact is None else {
                "artifact_id": artifact["artifact_id"], "path": artifact["path"], "sha256": artifact["sha256"],
                "format": artifact["format"], "pages": artifact["pages"], "bytes_read": actual_size,
                "attestations": artifact["attestations"],
            },
            "candidate_safe_for_owner_review": artifact is not None and not compliance_reasons,
            "owner_review_still_required": True,
        }
        slot_rows.append(row)

    if conflicts:
        status = CONFLICT
    elif latest["_deadline_utc"] <= evaluated:
        status = DEADLINE
    elif missing:
        status = MISSING
    else:
        status = READY

    public_generations = [_public_generation(g) for g in generations]
    source_history_digest = sha256(canon(public_generations))
    input_digest = sha256(canon({
        "schema": normalized["schema"], "truth_boundary": normalized["truth_boundary"],
        "evaluated_at": normalized["evaluated_at"], "opportunity_id": normalized["opportunity_id"],
        "source_generations": public_generations, "artifacts": artifacts,
    }))
    manifest = {
        "schema": MANIFEST_SCHEMA, "truth_boundary": TRUTH_BOUNDARY,
        "opportunity_id": normalized["opportunity_id"], "evaluated_at": normalized["evaluated_at"],
        "active_source": {
            "source_id": latest["source_id"], "source_sha256": latest["source_sha256"],
            "sequence": latest["sequence"], "observed_at": latest["observed_at"], "deadline_at": latest["deadline_at"],
        },
        "source_history_sha256": source_history_digest, "input_sha256": input_digest,
        "instruction_changes_from_prior_generation": _instruction_changes(previous, latest),
        "status": status, "conflicts": sorted(set(conflicts)), "missing_required_slots": sorted(set(missing)),
        "missing_artifact_worklist": sorted(worklist, key=lambda row: row["slot_id"]),
        "slots": slot_rows, "authority": dict(AUTHORITY),
    }
    checklist_lines = [
        "# Procurement submission assembly — owner review", "",
        f"- Opportunity: `{normalized['opportunity_id']}`", f"- Status: **{status}**",
        f"- Active source: `{latest['source_id']}` / `{latest['source_sha256']}`",
        f"- Deadline: `{latest['deadline_at']}`",
        "- Authority: owner review only; no portal upload, buyer contact, signature/certification action, price commitment, submission, award, payment, or revenue authority.",
        "", "## Required assembly slots",
    ]
    for row in slot_rows:
        mark = "[x]" if row["candidate_safe_for_owner_review"] else "[ ]"
        required = "required" if row["required"] else "optional"
        artifact_name = row["candidate_artifact"]["path"] if row["candidate_artifact"] else "MISSING"
        checklist_lines.append(f"- {mark} `{row['slot_id']}` ({required}) — `{artifact_name}` — source section `{row['section_id']}`")
    if conflicts:
        checklist_lines += ["", "## Source / custody conflicts"] + [f"- {item}" for item in sorted(set(conflicts))]
    if missing:
        checklist_lines += ["", "## Missing required artifacts"] + [f"- `{item}`" for item in sorted(set(missing))]
    changes = manifest["instruction_changes_from_prior_generation"]
    if changes:
        checklist_lines += ["", "## Latest amendment deltas"]
        for change in changes:
            detail = ", ".join(change["fields"]) if change["fields"] else change["change"].lower()
            checklist_lines.append(f"- `{change['slot_id']}`: {change['change']} — {detail}")
    checklist_lines += ["", "Owner must still verify signatory/certification authority and perform any later submission through a separately authorized, freshly collision-fenced workflow.", ""]
    checklist = "\n".join(checklist_lines).encode("utf-8")
    manifest_bytes = canon(manifest)
    receipt = {
        "schema": RECEIPT_SCHEMA, "truth_boundary": TRUTH_BOUNDARY,
        "opportunity_id": normalized["opportunity_id"], "status": status,
        "input_sha256": input_digest, "source_history_sha256": source_history_digest,
        "active_source_sha256": latest["source_sha256"], "manifest_sha256": sha256(manifest_bytes),
        "checklist_sha256": sha256(checklist), "authority": dict(AUTHORITY),
    }
    return manifest_bytes, checklist, canon(receipt)


def verify(raw_input: bytes, manifest_bytes: bytes, checklist_bytes: bytes, receipt_bytes: bytes, artifact_loader: Callable[[dict[str, Any]], bytes] | None = None) -> bool:
    expected = compile_manifest(raw_input, artifact_loader)
    supplied = (manifest_bytes, checklist_bytes, receipt_bytes)
    return all(a == b for a, b in zip(expected, supplied))
