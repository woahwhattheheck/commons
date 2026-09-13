from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping

INPUT_SCHEMA = "commons-catalog-currentness-input/v1"
RECEIPT_SCHEMA = "commons-catalog-currentness-receipt/v1"
MAX_SNAPSHOT_AGE_SECONDS = 24 * 60 * 60

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+\-]{0,63}$")
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
SECRET_PATTERNS = tuple(re.compile(x) for x in (
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"(?i)\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9_-]{8,}\b",
    r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b",
    r"(?i)\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*\S{8,}",
))
FAMILIES = {"PRODUCT", "SERVICE", "EXPERTISE", "DATA"}
POLICIES = {"PINNED_RELEASE", "FOLLOW_DEFAULT_BRANCH"}

INPUT_KEYS = {"schema", "catalogs", "providerSnapshots"}
CATALOG_KEYS = {"catalogId", "family", "catalogDigestSha256", "entries"}
ENTRY_KEYS = {
    "entryId", "artifactId", "repository", "releaseCommitSha", "sourcePath",
    "sourceContentSha256", "sourceEvidenceSha256", "version", "currentnessPolicy",
}
SNAPSHOT_KEYS = {
    "snapshotId", "repository", "defaultBranch", "defaultBranchHeadSha",
    "capturedAt", "complete", "providerEvidenceSha256", "paths",
}
PATH_KEYS = {"sourcePath", "contentSha256"}


class CatalogCurrentnessError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _exact_keys(obj: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(obj))
    extra = sorted(set(obj) - expected)
    if missing or extra:
        raise CatalogCurrentnessError(f"{label} schema mismatch: missing={missing} extra={extra}")


def _string(value: Any, label: str, max_len: int = 512) -> str:
    if not isinstance(value, str) or not value or len(value) > max_len or "\x00" in value:
        raise CatalogCurrentnessError(f"{label} must be a non-empty safe string <= {max_len} chars")
    return value


def _identifier(value: Any, label: str) -> str:
    value = _string(value, label, 128)
    if not IDENT.fullmatch(value):
        raise CatalogCurrentnessError(f"{label} has invalid identifier syntax")
    return value


def _digest(value: Any, label: str, length: int = 64) -> str:
    value = _string(value, label, length)
    pattern = HEX40 if length == 40 else HEX64
    if not pattern.fullmatch(value):
        raise CatalogCurrentnessError(f"{label} must be lowercase {length}-hex")
    return value


def _path(value: Any, label: str) -> str:
    value = _string(value, label, 512)
    parts = value.split("/")
    if value.startswith(("/", "\\")) or "\\" in value or any(x in {"", ".", ".."} for x in parts):
        raise CatalogCurrentnessError(f"{label} must be a normalized repository-relative POSIX path")
    if any(x.lower().endswith((".lnk", ".url")) for x in parts):
        raise CatalogCurrentnessError(f"{label} contains a link-shaped segment")
    return value


def _instant(value: Any, label: str) -> datetime:
    value = _string(value, label, 32)
    if not value.endswith("Z"):
        raise CatalogCurrentnessError(f"{label} must use explicit UTC Z suffix")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CatalogCurrentnessError(f"{label} is not ISO-8601 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise CatalogCurrentnessError(f"{label} must be UTC")
    return parsed


def _sensitive(value: Any) -> bool:
    if isinstance(value, str):
        return bool(EMAIL.search(value) or any(p.search(value) for p in SECRET_PATTERNS))
    if isinstance(value, Mapping):
        return any(_sensitive(k) or _sensitive(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_sensitive(x) for x in value)
    return False


def _normalize_entry(raw: Any, catalog_id: str, family: str, catalog_digest: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CatalogCurrentnessError("catalog entry must be an object")
    _exact_keys(raw, ENTRY_KEYS, "catalog entry")
    repository = _string(raw["repository"], "entry.repository", 200)
    if not REPO.fullmatch(repository):
        raise CatalogCurrentnessError("entry.repository must be owner/name")
    version = _string(raw["version"], "entry.version", 64)
    if not VERSION.fullmatch(version):
        raise CatalogCurrentnessError("entry.version has invalid syntax")
    policy = _string(raw["currentnessPolicy"], "entry.currentnessPolicy", 64)
    if policy not in POLICIES:
        raise CatalogCurrentnessError(f"unsupported currentnessPolicy: {policy}")
    out = {
        "catalogId": catalog_id,
        "catalogFamily": family,
        "catalogDigestSha256": catalog_digest,
        "entryId": _identifier(raw["entryId"], "entry.entryId"),
        "artifactId": _identifier(raw["artifactId"], "entry.artifactId"),
        "repository": repository,
        "releaseCommitSha": _digest(raw["releaseCommitSha"], "entry.releaseCommitSha", 40),
        "sourcePath": _path(raw["sourcePath"], "entry.sourcePath"),
        "sourceContentSha256": _digest(raw["sourceContentSha256"], "entry.sourceContentSha256"),
        "sourceEvidenceSha256": _digest(raw["sourceEvidenceSha256"], "entry.sourceEvidenceSha256"),
        "version": version,
        "currentnessPolicy": policy,
    }
    if _sensitive(out):
        raise CatalogCurrentnessError(f"entry {out['entryId']} contains secret/PII-shaped metadata")
    return out


def _normalize_catalog(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CatalogCurrentnessError("catalog must be an object")
    _exact_keys(raw, CATALOG_KEYS, "catalog")
    catalog_id = _identifier(raw["catalogId"], "catalog.catalogId")
    family = _string(raw["family"], "catalog.family", 32)
    if family not in FAMILIES:
        raise CatalogCurrentnessError(f"unsupported catalog family: {family}")
    digest = _digest(raw["catalogDigestSha256"], "catalog.catalogDigestSha256")
    entries = raw["entries"]
    if not isinstance(entries, list) or not entries:
        raise CatalogCurrentnessError("catalog.entries must be a non-empty list")
    normalized = [_normalize_entry(x, catalog_id, family, digest) for x in entries]
    ids = [x["entryId"] for x in normalized]
    if len(ids) != len(set(ids)):
        raise CatalogCurrentnessError(f"catalog {catalog_id} has duplicate entryId")
    normalized.sort(key=lambda x: x["entryId"])
    out = {"catalogId": catalog_id, "family": family, "catalogDigestSha256": digest, "entries": normalized}
    if _sensitive(out):
        raise CatalogCurrentnessError(f"catalog {catalog_id} contains secret/PII-shaped metadata")
    return out


def _normalize_snapshot_path(raw: Any) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise CatalogCurrentnessError("snapshot path must be an object")
    _exact_keys(raw, PATH_KEYS, "snapshot path")
    return {
        "sourcePath": _path(raw["sourcePath"], "snapshot path.sourcePath"),
        "contentSha256": _digest(raw["contentSha256"], "snapshot path.contentSha256"),
    }


def _normalize_snapshot(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CatalogCurrentnessError("provider snapshot must be an object")
    _exact_keys(raw, SNAPSHOT_KEYS, "provider snapshot")
    repository = _string(raw["repository"], "snapshot.repository", 200)
    if not REPO.fullmatch(repository):
        raise CatalogCurrentnessError("snapshot.repository must be owner/name")
    complete = raw["complete"]
    if type(complete) is not bool:
        raise CatalogCurrentnessError("snapshot.complete must be a JSON boolean")
    captured = _string(raw["capturedAt"], "snapshot.capturedAt", 32)
    _instant(captured, "snapshot.capturedAt")
    paths = raw["paths"]
    if not isinstance(paths, list):
        raise CatalogCurrentnessError("snapshot.paths must be a list")
    normalized_paths = [_normalize_snapshot_path(x) for x in paths]
    names = [x["sourcePath"] for x in normalized_paths]
    if len(names) != len(set(names)):
        raise CatalogCurrentnessError("provider snapshot has duplicate sourcePath")
    normalized_paths.sort(key=lambda x: x["sourcePath"])
    out = {
        "snapshotId": _identifier(raw["snapshotId"], "snapshot.snapshotId"),
        "repository": repository,
        "defaultBranch": _identifier(raw["defaultBranch"], "snapshot.defaultBranch"),
        "defaultBranchHeadSha": _digest(raw["defaultBranchHeadSha"], "snapshot.defaultBranchHeadSha", 40),
        "capturedAt": captured,
        "complete": complete,
        "providerEvidenceSha256": _digest(raw["providerEvidenceSha256"], "snapshot.providerEvidenceSha256"),
        "paths": normalized_paths,
    }
    if _sensitive(out):
        raise CatalogCurrentnessError(f"snapshot {out['snapshotId']} contains secret/PII-shaped metadata")
    return out


def normalize_input(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CatalogCurrentnessError("input must be an object")
    _exact_keys(raw, INPUT_KEYS, "input")
    if raw["schema"] != INPUT_SCHEMA:
        raise CatalogCurrentnessError(f"input.schema must equal {INPUT_SCHEMA}")
    catalogs, snapshots = raw["catalogs"], raw["providerSnapshots"]
    if not isinstance(catalogs, list) or not catalogs:
        raise CatalogCurrentnessError("input.catalogs must be a non-empty list")
    if not isinstance(snapshots, list) or not snapshots:
        raise CatalogCurrentnessError("input.providerSnapshots must be a non-empty list")
    catalogs_n = [_normalize_catalog(x) for x in catalogs]
    snapshots_n = [_normalize_snapshot(x) for x in snapshots]
    for rows, key, label in ((catalogs_n, "catalogId", "catalog"), (snapshots_n, "snapshotId", "snapshot")):
        ids = [x[key] for x in rows]
        if len(ids) != len(set(ids)):
            raise CatalogCurrentnessError(f"duplicate {label} identity")
    all_entries = [entry for catalog in catalogs_n for entry in catalog["entries"]]
    entry_ids = [x["entryId"] for x in all_entries]
    if len(entry_ids) != len(set(entry_ids)):
        raise CatalogCurrentnessError("entryId must be globally unique across catalogs")
    artifact_keys: dict[tuple[str, str], str] = {}
    artifact_bindings: dict[str, tuple[str, str, str, str, str, str]] = {}
    for entry in all_entries:
        key = (entry["repository"], entry["sourcePath"])
        previous = artifact_keys.get(key)
        if previous is not None and previous != entry["artifactId"]:
            raise CatalogCurrentnessError(f"conflicting artifact identity for {key[0]}:{key[1]}")
        artifact_keys[key] = entry["artifactId"]
        binding = (
            entry["repository"], entry["sourcePath"], entry["releaseCommitSha"],
            entry["sourceContentSha256"], entry["sourceEvidenceSha256"], entry["version"],
        )
        previous_binding = artifact_bindings.get(entry["artifactId"])
        if previous_binding is not None and previous_binding != binding:
            raise CatalogCurrentnessError(f"conflicting immutable binding for artifact {entry['artifactId']}")
        artifact_bindings[entry["artifactId"]] = binding
    catalogs_n.sort(key=lambda x: x["catalogId"])
    snapshots_n.sort(key=lambda x: x["snapshotId"])
    return {"schema": INPUT_SCHEMA, "catalogs": catalogs_n, "providerSnapshots": snapshots_n}


def _finding(code: str, subject: str, detail: str, severity: str) -> dict[str, str]:
    return {"code": code, "subject": subject, "detail": detail, "severity": severity}


def compile_currentness(raw: Any, *, as_of: str) -> dict[str, Any]:
    data = normalize_input(raw)
    now = _instant(as_of, "as_of")
    snapshots = data["providerSnapshots"]
    by_repo: dict[str, list[dict[str, Any]]] = {}
    findings: list[dict[str, str]] = []
    for snapshot in snapshots:
        by_repo.setdefault(snapshot["repository"], []).append(snapshot)
        captured = _instant(snapshot["capturedAt"], "snapshot.capturedAt")
        age = (now - captured).total_seconds()
        if age < 0:
            findings.append(_finding("SNAPSHOT_FROM_FUTURE", snapshot["snapshotId"], "provider snapshot captured after trusted evaluation time", "HOLD"))
        elif age > MAX_SNAPSHOT_AGE_SECONDS:
            findings.append(_finding("SNAPSHOT_STALE", snapshot["snapshotId"], "provider snapshot exceeds 24-hour freshness window", "HOLD"))
        if not snapshot["complete"]:
            findings.append(_finding("SNAPSHOT_INCOMPLETE", snapshot["snapshotId"], "provider snapshot is not complete", "HOLD"))
    for repository, rows in by_repo.items():
        if len(rows) != 1:
            findings.append(_finding("AMBIGUOUS_REPOSITORY_SNAPSHOT", repository, f"expected exactly one snapshot; found {len(rows)}", "HOLD"))

    entry_results: list[dict[str, Any]] = []
    all_entries = [entry for catalog in data["catalogs"] for entry in catalog["entries"]]
    for entry in all_entries:
        rows = by_repo.get(entry["repository"], [])
        state = "HOLD"
        reason = "MISSING_REPOSITORY_SNAPSHOT"
        current_head = None
        current_digest = None
        if len(rows) == 0:
            findings.append(_finding("MISSING_REPOSITORY_SNAPSHOT", entry["entryId"], "no provider snapshot for entry repository", "HOLD"))
        elif len(rows) == 1:
            snapshot = rows[0]
            current_head = snapshot["defaultBranchHeadSha"]
            if snapshot["complete"]:
                path_rows = {x["sourcePath"]: x for x in snapshot["paths"]}
                current = path_rows.get(entry["sourcePath"])
                if current is None:
                    reason = "SOURCE_PATH_MISSING"
                    findings.append(_finding("SOURCE_PATH_MISSING", entry["entryId"], "catalog source path is absent from complete provider snapshot", "HOLD"))
                else:
                    current_digest = current["contentSha256"]
                    if current_digest == entry["sourceContentSha256"]:
                        state, reason = "CURRENT", "SOURCE_CONTENT_MATCH"
                    elif entry["currentnessPolicy"] == "PINNED_RELEASE":
                        state, reason = "REVIEW_REQUIRED", "PINNED_RELEASE_SOURCE_DRIFT"
                        findings.append(_finding("PINNED_RELEASE_SOURCE_DRIFT", entry["entryId"], "default-branch source changed after immutable catalog release; human review required", "REVIEW_REQUIRED"))
                    else:
                        state, reason = "HOLD", "FOLLOW_DEFAULT_BRANCH_SOURCE_DRIFT"
                        findings.append(_finding("FOLLOW_DEFAULT_BRANCH_SOURCE_DRIFT", entry["entryId"], "default-branch source differs from catalog-bound source", "HOLD"))
        entry_results.append({
            "entryId": entry["entryId"], "catalogId": entry["catalogId"], "family": entry["catalogFamily"],
            "artifactId": entry["artifactId"], "repository": entry["repository"], "sourcePath": entry["sourcePath"],
            "version": entry["version"], "currentnessPolicy": entry["currentnessPolicy"], "releaseCommitSha": entry["releaseCommitSha"],
            "sourceContentSha256": entry["sourceContentSha256"], "sourceEvidenceSha256": entry["sourceEvidenceSha256"],
            "providerDefaultBranchHeadSha": current_head, "providerSourceContentSha256": current_digest,
            "entryState": state, "reason": reason,
        })

    findings.sort(key=lambda x: (x["severity"], x["code"], x["subject"], x["detail"]))
    entry_results.sort(key=lambda x: x["entryId"])
    has_hold = any(x["severity"] == "HOLD" for x in findings) or any(x["entryState"] == "HOLD" for x in entry_results)
    has_review = any(x["severity"] == "REVIEW_REQUIRED" for x in findings) or any(x["entryState"] == "REVIEW_REQUIRED" for x in entry_results)
    if has_hold:
        state = "HOLD"
    elif has_review:
        state = "REVIEW_REQUIRED"
    else:
        state = "READY_FOR_HUMAN_CATALOG_CURRENTNESS_REVIEW"
    body = {
        "schema": RECEIPT_SCHEMA,
        "asOf": as_of,
        "state": state,
        "inputDigest": sha256_text(canonical_json(data)),
        "catalogSetDigest": sha256_text(canonical_json([{"catalogId": x["catalogId"], "catalogDigestSha256": x["catalogDigestSha256"]} for x in data["catalogs"]])),
        "providerSnapshotSetDigest": sha256_text(canonical_json(snapshots)),
        "counts": {
            "catalogs": len(data["catalogs"]), "entries": len(entry_results), "providerSnapshots": len(snapshots),
            "current": sum(x["entryState"] == "CURRENT" for x in entry_results),
            "reviewRequired": sum(x["entryState"] == "REVIEW_REQUIRED" for x in entry_results),
            "hold": sum(x["entryState"] == "HOLD" for x in entry_results),
            "findings": len(findings),
        },
        "findings": findings,
        "entries": entry_results,
        "authority": {key: False for key in (
            "catalogPublicationAuthorized", "catalogUpdateAuthorized", "catalogWithdrawalAuthorized", "buyerContactAuthorized",
            "pricingAuthorized", "checkoutAuthorized", "paymentAuthorized", "transferAuthorized", "acceptanceEstablished", "revenueRecognized",
        )},
    }
    return {**body, "receiptSha256": sha256_text(canonical_json(body))}


def verify_receipt(raw: Any, *, as_of: str, receipt: Any) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    try:
        expected = compile_currentness(raw, as_of=as_of)
    except CatalogCurrentnessError:
        return False
    return canonical_json(expected) == canonical_json(receipt)


def render_csv(receipt: Mapping[str, Any]) -> str:
    output = io.StringIO(newline="")
    fields = [
        "entryId", "catalogId", "family", "artifactId", "repository", "sourcePath", "version", "currentnessPolicy",
        "releaseCommitSha", "sourceContentSha256", "sourceEvidenceSha256", "providerDefaultBranchHeadSha",
        "providerSourceContentSha256", "entryState", "reason",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in receipt.get("entries", []):
        writer.writerow({key: row.get(key) for key in fields})
    return output.getvalue()


def render_markdown(receipt: Mapping[str, Any]) -> str:
    counts = receipt.get("counts", {})
    lines = [
        "# Catalog currentness receipt", "", f"**State:** `{receipt.get('state', 'HOLD')}`",
        f"**Trusted evaluation time:** `{receipt.get('asOf', '')}`",
        f"**Entries:** {counts.get('entries', 0)} · **Current:** {counts.get('current', 0)} · **Review required:** {counts.get('reviewRequired', 0)} · **Hold:** {counts.get('hold', 0)}",
        "", "## Entries", "", "| Entry | Family | Repository | Version | Policy | State | Reason |", "|---|---|---|---|---|---|---|",
    ]
    for row in receipt.get("entries", []):
        lines.append("| {entryId} | {family} | {repository} | {version} | {currentnessPolicy} | {entryState} | {reason} |".format(**row))
    lines += ["", "## Findings", ""]
    findings = receipt.get("findings", [])
    lines += [f"- `{x['severity']}` · `{x['code']}` · `{x['subject']}` · {x['detail']}" for x in findings] if findings else ["None."]
    lines += [
        "", "## Authority boundary", "",
        "This receipt is evidence for human catalog-currentness review only. It never publishes, updates, withdraws, reprices, contacts buyers, creates checkout, accepts payment, transfers an artifact, establishes acceptance, or recognizes revenue.",
        "", f"Receipt SHA-256: `{receipt.get('receiptSha256', '')}`", "",
    ]
    return "\n".join(lines)
