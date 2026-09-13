from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from revenue.streaming_rendition_release_gate.fixture import (
    REQUIRED_FAULT_CLASSES,
    build_fixture,
    canonical_fixture_bytes,
)
from revenue.streaming_rendition_release_gate.gate import HOLD, RELEASE_READY, validate_packets

PILOT_DIR = Path(__file__).resolve().parent
SOURCE_MANIFEST = ROOT / "revenue" / "streaming_rendition_release_gate" / "manifest.json"
PROSPECTS = PILOT_DIR / "prospects.json"
PROOF = PILOT_DIR / "proof.json"
OFFER = PILOT_DIR / "offer.md"
CHECKED_REPORT = PILOT_DIR / "synthetic_buyer_report.md"

OPERATION = "STREAMING-RENDITION-QA-PILOT-KIT-ZLCV7Q3-20260913"
OWNER = "Z-LorentzCinder-914020-V7Q3"
SOURCE_PR = 13885
SOURCE_HEAD_SHA = "4d36fb08bf3e106f59b32008fb2486013298dce6"
SOURCE_MERGE_SHA = "fed79e71c0c94c92568e5b555f50d2ad34ad0658"
FIXTURE_SHA256 = "27d34cc0574f3210e3e42c575f3615be9bd6d056f6f51576271bc7b6ecc79441"
PROJECTION_SHA256 = "e510ed89458a54d32a6cda0da425d92612ed40783fb311c2db86d3ad33f889c2"
DIAGNOSTIC_PRICE_USD = 2500
INTEGRATION_PRICE_USD = 7500
DIAGNOSTIC_ASSET_CAP = 250

PROSPECT_FIELDS = {
    "organization",
    "evidence_url",
    "evidence_summary",
    "fit_reason",
    "falsifier",
}
FORBIDDEN_PROSPECT_KEYS = {
    "email",
    "phone",
    "contact",
    "contact_name",
    "contact_email",
    "contact_phone",
    "api_key",
    "token",
    "credential",
}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


class PacketError(ValueError):
    """Fail-closed validation error for the commercialization packet."""


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_source_manifest(manifest: dict[str, Any]) -> None:
    fixture = manifest.get("fixture")
    if not isinstance(fixture, dict):
        raise PacketError("source fixture block missing")
    exact = {
        "canonical_sha256": FIXTURE_SHA256,
        "total": 168,
        "release_ready": 140,
        "hold": 28,
    }
    for key, expected in exact.items():
        if fixture.get(key) != expected:
            raise PacketError(f"source fixture drift: {key}")
    if manifest.get("projection_sha256") != PROJECTION_SHA256:
        raise PacketError("source projection drift")
    fault_counts = fixture.get("fault_counts")
    if not isinstance(fault_counts, dict):
        raise PacketError("source fault counts missing")
    if set(fault_counts) != set(REQUIRED_FAULT_CLASSES):
        raise PacketError("source fault-class set drift")
    if any(fault_counts[name] != 4 for name in REQUIRED_FAULT_CLASSES):
        raise PacketError("source fault-count drift")


def validate_proof(proof: dict[str, Any]) -> None:
    if set(proof) != {"schema", "operation", "owner", "source", "commercial", "authority"}:
        raise PacketError("proof schema keys drift")
    if proof["schema"] != "streaming-rendition-qa-pilot-proof/v1":
        raise PacketError("proof schema drift")
    if proof["operation"] != OPERATION or proof["owner"] != OWNER:
        raise PacketError("proof identity drift")

    source = proof["source"]
    expected_source = {
        "repository": "woahwhattheheck/commons",
        "source_pr": SOURCE_PR,
        "source_head_sha": SOURCE_HEAD_SHA,
        "source_merge_sha": SOURCE_MERGE_SHA,
        "fixture_sha256": FIXTURE_SHA256,
        "projection_sha256": PROJECTION_SHA256,
        "total": 168,
        "release_ready": 140,
        "hold": 28,
        "fault_classes": 7,
        "holds_per_fault_class": 4,
    }
    if source != expected_source:
        raise PacketError("proof source binding drift")

    commercial = proof["commercial"]
    expected_commercial = {
        "diagnostic_price_usd": DIAGNOSTIC_PRICE_USD,
        "integration_sprint_price_usd": INTEGRATION_PRICE_USD,
        "diagnostic_asset_cap": DIAGNOSTIC_ASSET_CAP,
        "pricing_status": "pilot-test-price-not-market-rate-claim",
        "recognized_revenue_usd": 0,
        "buyer_acceptance": False,
        "payment_received": False,
    }
    if commercial != expected_commercial:
        raise PacketError("proof commercial state drift")

    authority = proof["authority"]
    if not isinstance(authority, dict) or not authority:
        raise PacketError("proof authority block missing")
    if any(value is not False for value in authority.values()):
        raise PacketError("proof exceeds authority ceiling")


def validate_offer_text(text: str) -> None:
    required = (
        "$2,500 metadata-only diagnostic",
        "$2,500 flat",
        "no more than 250 assets",
        "$7,500 integration sprint",
        "$7,500 flat",
        "Pilot-test price",
        "No media bytes are required",
        "No DRM keys or secrets",
        "media operations retain release authority",
        "Stop rule",
    )
    missing = [needle for needle in required if needle not in text]
    if missing:
        raise PacketError(f"offer drift: missing {missing}")
    forbidden = (
        "guaranteed savings",
        "guaranteed revenue",
        "buyer accepted",
        "payment received",
        "we will publish",
        "we will transcode",
    )
    lowered = text.lower()
    if any(needle in lowered for needle in forbidden):
        raise PacketError("offer makes an unauthorized outcome claim")


def _validate_https_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise PacketError("prospect evidence URL must be absolute HTTPS")
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        raise PacketError("prospect evidence URL must be public")
    if parsed.username or parsed.password:
        raise PacketError("prospect evidence URL may not contain credentials")


def validate_prospects(prospects: Any) -> list[dict[str, str]]:
    if not isinstance(prospects, list) or len(prospects) != 10:
        raise PacketError("prospect queue must contain exactly 10 rows")

    organizations: set[str] = set()
    evidence_urls: set[str] = set()
    clean: list[dict[str, str]] = []
    for row in prospects:
        if not isinstance(row, dict) or set(row) != PROSPECT_FIELDS:
            raise PacketError("prospect row schema drift")
        if set(row).intersection(FORBIDDEN_PROSPECT_KEYS):
            raise PacketError("contact/private field present")
        normalized: dict[str, str] = {}
        for key in sorted(PROSPECT_FIELDS):
            value = row[key]
            if not isinstance(value, str) or not value.strip():
                raise PacketError(f"prospect {key} must be non-empty text")
            if EMAIL_RE.search(value):
                raise PacketError("direct email/contact data is forbidden")
            normalized[key] = value.strip()
        _validate_https_public_url(normalized["evidence_url"])
        if len(normalized["evidence_summary"]) < 60:
            raise PacketError("public evidence summary is too thin")
        if len(normalized["fit_reason"]) < 60 or len(normalized["falsifier"]) < 60:
            raise PacketError("fit/falsifier evidence is too thin")
        org_key = normalized["organization"].casefold()
        url_key = normalized["evidence_url"].casefold()
        if org_key in organizations or url_key in evidence_urls:
            raise PacketError("duplicate prospect identity/evidence URL")
        organizations.add(org_key)
        evidence_urls.add(url_key)
        clean.append(normalized)
    return clean


def build_report(source_manifest: dict[str, Any]) -> dict[str, Any]:
    validate_source_manifest(source_manifest)
    packets, fault_assets = build_fixture()
    fixture_digest = sha256_bytes(canonical_fixture_bytes())
    if fixture_digest != FIXTURE_SHA256:
        raise PacketError("live fixture bytes do not match source proof")

    validated = validate_packets(packets)
    if validated["projection_sha256"] != PROJECTION_SHA256:
        raise PacketError("live validation projection does not match source proof")
    rows = validated["results"]

    ready = [row for row in rows if row["status"] == RELEASE_READY]
    holds = [row for row in rows if row["status"] == HOLD]
    if len(rows) != 168 or len(ready) != 140 or len(holds) != 28:
        raise PacketError("live result counts drift")

    fault_rows: list[dict[str, Any]] = []
    for reason in REQUIRED_FAULT_CLASSES:
        actual = sorted(row["asset_id"] for row in holds if row["reason"] == reason)
        expected = sorted(fault_assets[reason])
        if actual != expected or len(actual) != 4:
            raise PacketError(f"live fault mapping drift: {reason}")
        fault_rows.append(
            {"reason": reason, "hold_count": len(actual), "synthetic_asset_ids": actual}
        )

    clean = next((row for row in rows if row["asset_id"] == "asset-000"), None)
    if clean is None or clean["status"] != RELEASE_READY or clean["reason"] != "NONE":
        raise PacketError("clean control drift")

    return {
        "schema": "streaming-rendition-qa-synthetic-report/v1",
        "synthetic_only": True,
        "source": {
            "pr": SOURCE_PR,
            "head_sha": SOURCE_HEAD_SHA,
            "merge_sha": SOURCE_MERGE_SHA,
            "fixture_sha256": fixture_digest,
            "projection_sha256": validated["projection_sha256"],
        },
        "summary": {"total": 168, "release_ready": 140, "hold": 28},
        "fault_classes": fault_rows,
        "clean_control": {
            "asset_id": clean["asset_id"],
            "status": clean["status"],
            "reason": clean["reason"],
        },
        "authority": {
            "customer_data": False,
            "media_bytes": False,
            "drm_secrets": False,
            "provider_access": False,
            "release_authority": False,
        },
    }


def render_buyer_report(report: dict[str, Any]) -> str:
    source = report["source"]
    summary = report["summary"]
    lines = [
        "# Synthetic Streaming Rendition QA report",
        "",
        "**Synthetic proof only — no customer data, media bytes, DRM secrets, provider access, or release authority.**",
        "",
        f"Source carrier: Commons PR #{SOURCE_PR}, merged as `{source['merge_sha']}`.",
        "",
        f"Canonical fixture: **{summary['total']}** synthetic asset packets → **{summary['release_ready']} RELEASE_READY / {summary['hold']} HOLD**. The 28 HOLD packets are evenly distributed: exactly four per modeled fault class.",
        "",
        "| Fault class | HOLD count | Synthetic asset IDs |",
        "| --- | ---: | --- |",
    ]
    for row in report["fault_classes"]:
        assets = row["synthetic_asset_ids"]
        first = assets[0]
        last = assets[-1]
        lines.append(
            f"| `{row['reason']}` | {row['hold_count']} | `{first}`–`{last}` |"
        )
    clean = report["clean_control"]
    lines += [
        "",
        f"Clean control: `{clean['asset_id']}` is expected to emit `{clean['status']}` / reason `{clean['reason']}`.",
        "",
        f"Fixture SHA-256: `{source['fixture_sha256']}`  ",
        f"Projection SHA-256: `{source['projection_sha256']}`",
        "",
        "This report demonstrates the diagnostic shape only. It does not claim a buyer has accepted the offer, supplied data, paid, or realized savings.",
        "",
    ]
    return "\n".join(lines)


def compile_packet() -> dict[str, Any]:
    source_manifest = load_json(SOURCE_MANIFEST)
    proof = load_json(PROOF)
    prospects = load_json(PROSPECTS)
    offer_text = OFFER.read_text(encoding="utf-8")

    validate_source_manifest(source_manifest)
    validate_proof(proof)
    validate_offer_text(offer_text)
    clean_prospects = validate_prospects(prospects)
    report = build_report(source_manifest)

    expected_report = render_buyer_report(report)
    checked_report = CHECKED_REPORT.read_text(encoding="utf-8")
    if checked_report != expected_report:
        raise PacketError("checked synthetic buyer report drift")

    return {
        "schema": "streaming-rendition-qa-pilot-packet/v1",
        "operation": OPERATION,
        "owner": OWNER,
        "offer_sha256": sha256_bytes(offer_text.encode("utf-8")),
        "prospects_sha256": sha256_bytes(canonical_json(clean_prospects)),
        "synthetic_report_sha256": sha256_bytes(checked_report.encode("utf-8")),
        "proof": proof,
        "prospects": clean_prospects,
        "synthetic_report": report,
    }


def write_packet(output: Path, packet: dict[str, Any]) -> str:
    payload = canonical_json(packet)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return sha256_bytes(payload)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile the fail-closed paid-pilot packet.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path for canonical packet JSON.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate source proof, offer, prospects, and checked synthetic report.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    packet = compile_packet()
    digest = sha256_bytes(canonical_json(packet))
    if args.output is not None:
        digest = write_packet(args.output, packet)
    print(
        json.dumps(
            {
                "operation": OPERATION,
                "prospects": len(packet["prospects"]),
                "release_ready": packet["synthetic_report"]["summary"]["release_ready"],
                "hold": packet["synthetic_report"]["summary"]["hold"],
                "packet_sha256": digest,
                "status": "PASS",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
