from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping

SCHEMA_INPUT = "commons-product-catalog-bridge-input/v1"
SCHEMA_RECEIPT = "commons-product-catalog-bridge-receipt/v1"
MAX_EVIDENCE_AGE_SECONDS = 30 * 24 * 60 * 60

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+\-]{0,63}$")
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*\S{8,}"),
)

_TRANSFER_BOUNDARIES = {
    "SOURCE_ARCHIVE",
    "BINARY_PACKAGE",
    "LOCAL_APPLICATION",
    "LICENSED_DATA_BUNDLE",
    "DOCUMENTED_SERVICE_BUNDLE",
}
_LISTING_STATUSES = {"DRAFT", "INTERNAL_READY", "PUBLISHED"}
_VERIFICATION_KINDS = {
    "SOURCE_TEST",
    "PACKAGE_TEST",
    "REPRODUCIBILITY_CHECK",
    "INSTALL_CHECK",
    "MANIFEST_CHECK",
}

_INPUT_KEYS = {"schema", "artifacts", "listings", "evidence"}
_ARTIFACT_KEYS = {
    "artifactId",
    "repository",
    "commitSha",
    "sourcePath",
    "contentSha256",
    "version",
    "licenseId",
    "licenseEvidenceSha256",
    "transferBoundary",
    "catalogListingId",
}
_LISTING_KEYS = {"listingId", "title", "family", "status", "version", "artifactIds"}
_EVIDENCE_KEYS = {
    "evidenceId",
    "artifactId",
    "contentSha256",
    "verificationKind",
    "outcome",
    "capturedAt",
    "sourceSha256",
}


class CatalogBridgeError(ValueError):
    """Raised for malformed input where compilation cannot proceed safely."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _exact_keys(obj: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(obj)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise CatalogBridgeError(f"{label} schema mismatch: missing={missing} extra={extra}")


def _require_str(value: Any, label: str, *, max_len: int = 512) -> str:
    if not isinstance(value, str) or not value or len(value) > max_len:
        raise CatalogBridgeError(f"{label} must be a non-empty string <= {max_len} chars")
    if "\x00" in value:
        raise CatalogBridgeError(f"{label} contains NUL")
    return value


def _identifier(value: Any, label: str) -> str:
    text = _require_str(value, label, max_len=128)
    if not _ID.fullmatch(text):
        raise CatalogBridgeError(f"{label} has invalid identifier syntax")
    return text


def _digest(value: Any, label: str, *, length: int = 64) -> str:
    text = _require_str(value, label, max_len=length)
    matcher = _HEX64 if length == 64 else _HEX40
    if not matcher.fullmatch(text):
        raise CatalogBridgeError(f"{label} must be lowercase {length}-hex")
    return text


def _utc_instant(value: Any, label: str) -> datetime:
    text = _require_str(value, label, max_len=32)
    if not text.endswith("Z"):
        raise CatalogBridgeError(f"{label} must use explicit UTC Z suffix")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise CatalogBridgeError(f"{label} is not an ISO-8601 UTC instant") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise CatalogBridgeError(f"{label} must be UTC")
    return parsed


def _path(value: Any, label: str) -> str:
    text = _require_str(value, label, max_len=512)
    if text.startswith(("/", "\\")) or "\\" in text:
        raise CatalogBridgeError(f"{label} must be a normalized repository-relative POSIX path")
    parts = text.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise CatalogBridgeError(f"{label} contains empty/dot traversal segment")
    if any(part.endswith((".lnk", ".url")) for part in parts):
        raise CatalogBridgeError(f"{label} contains link-shaped segment")
    return text


def _has_sensitive_shape(value: Any) -> bool:
    if isinstance(value, str):
        if _EMAIL.search(value):
            return True
        return any(pattern.search(value) for pattern in _SECRET_PATTERNS)
    if isinstance(value, Mapping):
        return any(_has_sensitive_shape(k) or _has_sensitive_shape(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_has_sensitive_shape(item) for item in value)
    return False


def _normalize_artifact(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CatalogBridgeError("artifact must be an object")
    _exact_keys(raw, _ARTIFACT_KEYS, "artifact")
    artifact_id = _identifier(raw["artifactId"], "artifact.artifactId")
    repository = _require_str(raw["repository"], "artifact.repository", max_len=200)
    if not _REPO.fullmatch(repository):
        raise CatalogBridgeError("artifact.repository must be owner/name")
    commit_sha = _digest(raw["commitSha"], "artifact.commitSha", length=40)
    source_path = _path(raw["sourcePath"], "artifact.sourcePath")
    content_sha = _digest(raw["contentSha256"], "artifact.contentSha256")
    version = _require_str(raw["version"], "artifact.version", max_len=64)
    if not _VERSION.fullmatch(version):
        raise CatalogBridgeError("artifact.version has invalid syntax")
    license_id = _require_str(raw["licenseId"], "artifact.licenseId", max_len=96)
    if license_id.upper() in {"UNKNOWN", "NONE", "UNVERIFIED", "TBD"}:
        raise CatalogBridgeError("artifact.licenseId is not transfer-ready")
    license_evidence = _digest(raw["licenseEvidenceSha256"], "artifact.licenseEvidenceSha256")
    boundary = _require_str(raw["transferBoundary"], "artifact.transferBoundary", max_len=64)
    if boundary not in _TRANSFER_BOUNDARIES:
        raise CatalogBridgeError(f"artifact.transferBoundary unsupported: {boundary}")
    listing_id = _identifier(raw["catalogListingId"], "artifact.catalogListingId")
    normalized = {
        "artifactId": artifact_id,
        "repository": repository,
        "commitSha": commit_sha,
        "sourcePath": source_path,
        "contentSha256": content_sha,
        "version": version,
        "licenseId": license_id,
        "licenseEvidenceSha256": license_evidence,
        "transferBoundary": boundary,
        "catalogListingId": listing_id,
    }
    if _has_sensitive_shape(normalized):
        raise CatalogBridgeError(f"artifact {artifact_id} contains secret/PII-shaped metadata")
    return normalized


def _normalize_listing(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CatalogBridgeError("listing must be an object")
    _exact_keys(raw, _LISTING_KEYS, "listing")
    listing_id = _identifier(raw["listingId"], "listing.listingId")
    title = _require_str(raw["title"], "listing.title", max_len=160)
    family = _require_str(raw["family"], "listing.family", max_len=32)
    if family != "PRODUCT":
        raise CatalogBridgeError("listing.family must be PRODUCT")
    status = _require_str(raw["status"], "listing.status", max_len=32)
    if status not in _LISTING_STATUSES:
        raise CatalogBridgeError(f"listing.status unsupported: {status}")
    version = _require_str(raw["version"], "listing.version", max_len=64)
    if not _VERSION.fullmatch(version):
        raise CatalogBridgeError("listing.version has invalid syntax")
    artifact_ids = raw["artifactIds"]
    if not isinstance(artifact_ids, list) or not artifact_ids:
        raise CatalogBridgeError("listing.artifactIds must be a non-empty list")
    normalized_ids = [_identifier(item, "listing.artifactIds[]") for item in artifact_ids]
    if len(set(normalized_ids)) != len(normalized_ids):
        raise CatalogBridgeError(f"listing {listing_id} has duplicate artifactIds")
    normalized = {
        "listingId": listing_id,
        "title": title,
        "family": family,
        "status": status,
        "version": version,
        "artifactIds": sorted(normalized_ids),
    }
    if _has_sensitive_shape(normalized):
        raise CatalogBridgeError(f"listing {listing_id} contains secret/PII-shaped metadata")
    return normalized


def _normalize_evidence(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CatalogBridgeError("evidence must be an object")
    _exact_keys(raw, _EVIDENCE_KEYS, "evidence")
    evidence_id = _identifier(raw["evidenceId"], "evidence.evidenceId")
    artifact_id = _identifier(raw["artifactId"], "evidence.artifactId")
    content_sha = _digest(raw["contentSha256"], "evidence.contentSha256")
    kind = _require_str(raw["verificationKind"], "evidence.verificationKind", max_len=64)
    if kind not in _VERIFICATION_KINDS:
        raise CatalogBridgeError(f"evidence.verificationKind unsupported: {kind}")
    outcome = _require_str(raw["outcome"], "evidence.outcome", max_len=16)
    if outcome not in {"PASS", "FAIL"}:
        raise CatalogBridgeError("evidence.outcome must be PASS or FAIL")
    captured_at = _require_str(raw["capturedAt"], "evidence.capturedAt", max_len=32)
    _utc_instant(captured_at, "evidence.capturedAt")
    source_sha = _digest(raw["sourceSha256"], "evidence.sourceSha256")
    normalized = {
        "evidenceId": evidence_id,
        "artifactId": artifact_id,
        "contentSha256": content_sha,
        "verificationKind": kind,
        "outcome": outcome,
        "capturedAt": captured_at,
        "sourceSha256": source_sha,
    }
    if _has_sensitive_shape(normalized):
        raise CatalogBridgeError(f"evidence {evidence_id} contains secret/PII-shaped metadata")
    return normalized


def normalize_input(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CatalogBridgeError("input must be an object")
    _exact_keys(raw, _INPUT_KEYS, "input")
    if raw["schema"] != SCHEMA_INPUT:
        raise CatalogBridgeError(f"input.schema must equal {SCHEMA_INPUT}")
    artifacts_raw = raw["artifacts"]
    listings_raw = raw["listings"]
    evidence_raw = raw["evidence"]
    if not isinstance(artifacts_raw, list) or not artifacts_raw:
        raise CatalogBridgeError("input.artifacts must be a non-empty list")
    if not isinstance(listings_raw, list) or not listings_raw:
        raise CatalogBridgeError("input.listings must be a non-empty list")
    if not isinstance(evidence_raw, list) or not evidence_raw:
        raise CatalogBridgeError("input.evidence must be a non-empty list")
    artifacts = [_normalize_artifact(x) for x in artifacts_raw]
    listings = [_normalize_listing(x) for x in listings_raw]
    evidence = [_normalize_evidence(x) for x in evidence_raw]
    for label, rows, key in (
        ("artifact", artifacts, "artifactId"),
        ("listing", listings, "listingId"),
        ("evidence", evidence, "evidenceId"),
    ):
        ids = [row[key] for row in rows]
        if len(ids) != len(set(ids)):
            raise CatalogBridgeError(f"duplicate {label} identity")
    return {
        "schema": SCHEMA_INPUT,
        "artifacts": sorted(artifacts, key=lambda x: x["artifactId"]),
        "listings": sorted(listings, key=lambda x: x["listingId"]),
        "evidence": sorted(evidence, key=lambda x: x["evidenceId"]),
    }


def _hold(code: str, subject: str, detail: str) -> dict[str, str]:
    return {"code": code, "subject": subject, "detail": detail}


def compile_catalog_bridge(raw: Any, *, as_of: str) -> dict[str, Any]:
    normalized = normalize_input(raw)
    as_of_dt = _utc_instant(as_of, "as_of")
    artifacts = normalized["artifacts"]
    listings = normalized["listings"]
    evidence = normalized["evidence"]
    artifact_by_id = {x["artifactId"]: x for x in artifacts}
    listing_by_id = {x["listingId"]: x for x in listings}
    evidence_by_artifact: dict[str, list[dict[str, Any]]] = {}
    holds: list[dict[str, str]] = []

    for ev in evidence:
        evidence_by_artifact.setdefault(ev["artifactId"], []).append(ev)
        if ev["artifactId"] not in artifact_by_id:
            holds.append(_hold("ORPHAN_EVIDENCE", ev["evidenceId"], "evidence names an unknown artifact"))

    for artifact in artifacts:
        aid = artifact["artifactId"]
        listing = listing_by_id.get(artifact["catalogListingId"])
        if listing is None:
            holds.append(_hold("MISSING_LISTING", aid, "artifact catalogListingId is absent"))
        elif aid not in listing["artifactIds"]:
            holds.append(_hold("LISTING_BACKREF_MISMATCH", aid, "listing does not name the mapped artifact"))

        rows = evidence_by_artifact.get(aid, [])
        if not rows:
            holds.append(_hold("MISSING_VERIFICATION_EVIDENCE", aid, "artifact has no verification evidence"))
            continue
        passing = 0
        for ev in rows:
            if ev["contentSha256"] != artifact["contentSha256"]:
                holds.append(_hold("EVIDENCE_CONTENT_MISMATCH", ev["evidenceId"], "evidence content digest differs from artifact"))
                continue
            captured = _utc_instant(ev["capturedAt"], "evidence.capturedAt")
            age = (as_of_dt - captured).total_seconds()
            if age < 0:
                holds.append(_hold("EVIDENCE_FROM_FUTURE", ev["evidenceId"], "evidence captured after trusted evaluation time"))
                continue
            if age > MAX_EVIDENCE_AGE_SECONDS:
                holds.append(_hold("EVIDENCE_STALE", ev["evidenceId"], "verification evidence exceeds 30-day freshness window"))
                continue
            if ev["outcome"] != "PASS":
                holds.append(_hold("VERIFICATION_FAILED", ev["evidenceId"], "verification evidence outcome is not PASS"))
                continue
            passing += 1
        if passing == 0:
            holds.append(_hold("NO_CURRENT_PASSING_EVIDENCE", aid, "artifact lacks current digest-bound PASS evidence"))

    mapped_from_artifacts: dict[str, set[str]] = {}
    for artifact in artifacts:
        mapped_from_artifacts.setdefault(artifact["catalogListingId"], set()).add(artifact["artifactId"])
    for listing in listings:
        lid = listing["listingId"]
        listed = set(listing["artifactIds"])
        mapped = mapped_from_artifacts.get(lid, set())
        unknown = sorted(listed - set(artifact_by_id))
        if unknown:
            holds.append(_hold("LISTING_NAMES_UNKNOWN_ARTIFACT", lid, ",".join(unknown)))
        if listed != mapped:
            holds.append(_hold("LISTING_COVERAGE_MISMATCH", lid, f"listed={sorted(listed)} mapped={sorted(mapped)}"))

    semantic_keys: dict[tuple[str, str], str] = {}
    for artifact in artifacts:
        key = (artifact["repository"], artifact["sourcePath"])
        prior = semantic_keys.get(key)
        if prior is not None and prior != artifact["artifactId"]:
            holds.append(_hold("CONFLICTING_ARTIFACT_IDENTITY", artifact["artifactId"], f"same repository/path also claimed by {prior}"))
        semantic_keys[key] = artifact["artifactId"]

    holds = sorted(holds, key=lambda h: (h["code"], h["subject"], h["detail"]))
    inventory_payload = {"artifacts": artifacts, "listings": listings, "evidence": evidence}
    input_digest = sha256_text(canonical_json(normalized))
    inventory_digest = sha256_text(canonical_json(inventory_payload))
    state = "READY_FOR_HUMAN_CATALOG_PUBLICATION" if not holds else "HOLD"
    receipt_without_hash = {
        "schema": SCHEMA_RECEIPT,
        "asOf": as_of,
        "state": state,
        "inputDigest": input_digest,
        "inventoryDigest": inventory_digest,
        "counts": {"artifacts": len(artifacts), "listings": len(listings), "evidence": len(evidence), "holds": len(holds)},
        "holds": holds,
        "authority": {
            "catalogPublicationAuthorized": False,
            "checkoutCreationAuthorized": False,
            "buyerContactAuthorized": False,
            "contractAuthorized": False,
            "paymentAuthorized": False,
            "transferAuthorized": False,
            "deploymentAuthorized": False,
            "acceptanceEstablished": False,
            "revenueRecognized": False,
        },
        "artifacts": [
            {
                "artifactId": a["artifactId"],
                "catalogListingId": a["catalogListingId"],
                "repository": a["repository"],
                "commitSha": a["commitSha"],
                "sourcePath": a["sourcePath"],
                "contentSha256": a["contentSha256"],
                "version": a["version"],
                "licenseId": a["licenseId"],
                "transferBoundary": a["transferBoundary"],
            }
            for a in artifacts
        ],
        "listings": [
            {
                "listingId": l["listingId"],
                "title": l["title"],
                "status": l["status"],
                "version": l["version"],
                "artifactIds": l["artifactIds"],
            }
            for l in listings
        ],
    }
    receipt = dict(receipt_without_hash)
    receipt["receiptSha256"] = sha256_text(canonical_json(receipt_without_hash))
    return receipt


def verify_receipt(raw: Any, *, as_of: str, receipt: Any) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    try:
        expected = compile_catalog_bridge(raw, as_of=as_of)
    except CatalogBridgeError:
        return False
    return canonical_json(expected) == canonical_json(receipt)


def render_csv(receipt: Mapping[str, Any]) -> str:
    output = io.StringIO(newline="")
    fieldnames = ["artifactId", "catalogListingId", "repository", "commitSha", "sourcePath", "contentSha256", "version", "licenseId", "transferBoundary", "state"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for artifact in receipt.get("artifacts", []):
        row = dict(artifact)
        row["state"] = receipt.get("state", "HOLD")
        writer.writerow(row)
    return output.getvalue()


def render_markdown(receipt: Mapping[str, Any]) -> str:
    state = str(receipt.get("state", "HOLD"))
    counts = receipt.get("counts", {})
    lines = [
        "# Product catalog bridge receipt",
        "",
        f"**State:** `{state}`",
        f"**Trusted evaluation time:** `{receipt.get('asOf', '')}`",
        f"**Artifacts:** {counts.get('artifacts', 0)} · **Listings:** {counts.get('listings', 0)} · **Holds:** {counts.get('holds', 0)}",
        "",
        "## Artifact coverage",
        "",
        "| Artifact | Listing | Repository | Commit | Version | Transfer boundary |",
        "|---|---|---|---|---|---|",
    ]
    for artifact in receipt.get("artifacts", []):
        lines.append("| {artifactId} | {catalogListingId} | {repository} | `{commitSha}` | {version} | {transferBoundary} |".format(**artifact))
    holds = receipt.get("holds", [])
    lines.extend(["", "## Holds", ""])
    if not holds:
        lines.append("None. The evidence packet is ready for **human catalog publication review** only.")
    else:
        for hold in holds:
            lines.append(f"- `{hold['code']}` · `{hold['subject']}` · {hold['detail']}")
    lines.extend([
        "",
        "## Authority boundary",
        "",
        "This receipt never publishes a catalog listing, creates checkout, contacts a buyer, signs a contract, accepts payment, transfers artifacts, deploys software, establishes acceptance, or recognizes revenue.",
        "",
        f"Receipt SHA-256: `{receipt.get('receiptSha256', '')}`",
        "",
    ])
    return "\n".join(lines)
