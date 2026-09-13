from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from revenue.streaming_rendition_release_gate.fixture import (
    REQUIRED_FAULT_CLASSES,
    build_fixture,
    canonical_fixture_bytes,
)
from revenue.streaming_rendition_release_gate.gate import HOLD, RELEASE_READY, validate_packets

SCHEMA = "streaming-rendition-qa-pilot/v1"
PROOF_SCHEMA = "streaming-rendition-qa-pilot-proof/v1"
BUNDLE_SCHEMA = "streaming-rendition-qa-pilot-bundle/v1"
SOURCE_PR = 13885
SOURCE_MERGE_SHA = "fed79e71c0c94c92568e5b555f50d2ad34ad0658"
EXPECTED_FIXTURE_SHA256 = "27d34cc0574f3210e3e42c575f3615be9bd6d056f6f51576271bc7b6ecc79441"
EXPECTED_PROJECTION_SHA256 = "e510ed89458a54d32a6cda0da425d92612ed40783fb311c2db86d3ad33f889c2"
EXPECTED_TOTAL = 168
EXPECTED_RELEASE_READY = 140
EXPECTED_HOLD = 28
EXPECTED_PER_FAULT = 4
MAX_DIAGNOSTIC_ASSETS = 250
DIAGNOSTIC_PRICE_USD_CENTS = 250_000
INTEGRATION_PRICE_USD_CENTS = 750_000

EXTERNAL_AUTHORITY = {
    "buyer_acceptance": False,
    "cdn_mutation": False,
    "content_editing": False,
    "drm_secret_access": False,
    "media_release_authority": False,
    "payment_authentication": False,
    "production_access": False,
    "publishing": False,
    "revenue_recognition": False,
    "rights_determination": False,
    "transcoding": False,
}


class PilotProofError(RuntimeError):
    """Raised when the commercialization proof no longer matches landed source truth."""


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _terms() -> dict[str, Any]:
    return {
        "diagnostic": {
            "currency": "USD",
            "fixed_price_cents": DIAGNOSTIC_PRICE_USD_CENTS,
            "max_asset_packets": MAX_DIAGNOSTIC_ASSETS,
            "input": "one sanitized metadata export",
            "output": "deterministic RELEASE_READY/HOLD diagnostic with stable reason codes and proof receipt",
        },
        "integration_expansion": {
            "currency": "USD",
            "fixed_price_cents": INTEGRATION_PRICE_USD_CENTS,
            "gate": "only after a completed paid diagnostic proves value and adapter scope is known",
        },
    }


def _proof_body() -> dict[str, Any]:
    packets, declared_fault_assets = build_fixture()
    fixture_bytes = canonical_fixture_bytes()
    validated = validate_packets(packets)
    rows = validated["results"]

    observed_ready = sum(row["status"] == RELEASE_READY for row in rows)
    observed_hold = sum(row["status"] == HOLD for row in rows)
    observed_fault_counts = Counter(
        row["reason"] for row in rows if row["status"] == HOLD
    )
    observed_fault_assets = {
        reason: [row["asset_id"] for row in rows if row["status"] == HOLD and row["reason"] == reason]
        for reason in REQUIRED_FAULT_CLASSES
    }

    fixture_sha = _sha256(fixture_bytes)
    projection_sha = validated["projection_sha256"]
    expected_fault_counts = {reason: EXPECTED_PER_FAULT for reason in REQUIRED_FAULT_CLASSES}

    failures: list[str] = []
    if len(packets) != EXPECTED_TOTAL or len(rows) != EXPECTED_TOTAL:
        failures.append("canonical total drift")
    if observed_ready != EXPECTED_RELEASE_READY:
        failures.append("release-ready count drift")
    if observed_hold != EXPECTED_HOLD:
        failures.append("hold count drift")
    if dict(observed_fault_counts) != expected_fault_counts:
        failures.append("fault-class count drift")
    if observed_fault_assets != declared_fault_assets:
        failures.append("fault-asset declaration drift")
    if fixture_sha != EXPECTED_FIXTURE_SHA256:
        failures.append("canonical fixture digest drift")
    if projection_sha != EXPECTED_PROJECTION_SHA256:
        failures.append("canonical projection digest drift")
    if EXPECTED_TOTAL > MAX_DIAGNOSTIC_ASSETS:
        failures.append("canonical proof exceeds commercial diagnostic ceiling")
    if failures:
        raise PilotProofError("; ".join(failures))

    return {
        "schema": PROOF_SCHEMA,
        "source": {
            "repository": "woahwhattheheck/commons",
            "pull_request": SOURCE_PR,
            "merge_sha": SOURCE_MERGE_SHA,
            "gate_schema": "streaming-rendition-release-gate/v1",
        },
        "commercial_terms": _terms(),
        "canonical_proof": {
            "total": EXPECTED_TOTAL,
            "release_ready": EXPECTED_RELEASE_READY,
            "hold": EXPECTED_HOLD,
            "fixture_sha256": fixture_sha,
            "projection_sha256": projection_sha,
            "fault_counts": expected_fault_counts,
            "fault_assets": observed_fault_assets,
        },
        "external_authority": dict(EXTERNAL_AUTHORITY),
    }


def build_proof_receipt() -> dict[str, Any]:
    body = _proof_body()
    return {**body, "receipt_sha256": _sha256(_canonical_bytes(body))}


def verify_proof_receipt(receipt: Any) -> bool:
    if not isinstance(receipt, dict):
        return False
    try:
        expected = build_proof_receipt()
    except PilotProofError:
        return False
    return receipt == expected


def _money(cents: int) -> str:
    return f"${cents // 100:,}"


def render_synthetic_diagnostic(receipt: dict[str, Any]) -> str:
    if not verify_proof_receipt(receipt):
        raise PilotProofError("proof receipt is not exact-current-source verified")
    proof = receipt["canonical_proof"]
    lines = [
        "# Streaming Rendition QA — synthetic diagnostic",
        "",
        "**Sample only. No customer media, production credentials, DRM secrets, or buyer data were used.**",
        "",
        f"- Assets evaluated: **{proof['total']}**",
        f"- Metadata packets release-ready: **{proof['release_ready']}**",
        f"- Held for review: **{proof['hold']}**",
        f"- Canonical fixture SHA-256: `{proof['fixture_sha256']}`",
        f"- Canonical result projection SHA-256: `{proof['projection_sha256']}`",
        "",
        "## Hold inventory",
        "",
        "| Stable reason | Count | Synthetic examples |",
        "| --- | ---: | --- |",
    ]
    for reason in REQUIRED_FAULT_CLASSES:
        examples = ", ".join(proof["fault_assets"][reason])
        lines.append(f"| `{reason}` | {proof['fault_counts'][reason]} | {examples} |")
    lines += [
        "",
        "## What this demonstrates",
        "",
        "The landed gate deterministically checks rendition presence, codec/profile declarations, segment continuity, caption/audio alignment, DRM **reference IDs**, artifact checksum/orphan consistency, publication-window consistency, and CDN-region metadata. `RELEASE_READY` means only that supplied metadata is internally consistent; media operations retain release authority.",
        "",
        "## Paid pilot",
        "",
        f"The bounded diagnostic is **{_money(DIAGNOSTIC_PRICE_USD_CENTS)} fixed** for one sanitized metadata export containing at most {MAX_DIAGNOSTIC_ASSETS} asset packets. A separate **{_money(INTEGRATION_PRICE_USD_CENTS)} integration sprint** is offered only after the paid diagnostic proves value and the adapter scope is known.",
        "",
        "Not included: media bytes, DRM secrets, rights decisions, transcoding, CDN mutation, publishing, production credentials, payment authentication, or claims of buyer acceptance/revenue.",
        "",
    ]
    return "\n".join(lines)


def render_scope_markdown(receipt: dict[str, Any]) -> str:
    if not verify_proof_receipt(receipt):
        raise PilotProofError("proof receipt is not exact-current-source verified")
    return "\n".join(
        [
            "# Streaming Rendition QA Pilot — scope / price / acceptance",
            "",
            f"**Diagnostic:** {_money(DIAGNOSTIC_PRICE_USD_CENTS)} fixed · one sanitized metadata export · <= {MAX_DIAGNOSTIC_ASSETS} asset packets.",
            "",
            "## Buyer supplies",
            "",
            "- One sanitized metadata export mapped to the documented packet schema.",
            "- No media bytes, DRM keys/secrets, production credentials, viewer PII, or rights-confidential material.",
            "- A human technical owner for questions about field meaning and export completeness.",
            "",
            "## We deliver",
            "",
            "- Deterministic per-asset `RELEASE_READY` / `HOLD` results with stable reason codes.",
            "- Defect inventory across rendition, codec/profile, continuity, caption/audio alignment, DRM-reference, checksum/orphan, publication-window, and CDN-region metadata consistency.",
            "- Content-addressed proof receipt and a concise owner-review diagnostic summary.",
            "- One readout of findings and adapter-fit observations; no production mutation.",
            "",
            "## Diagnostic acceptance",
            "",
            "The diagnostic deliverable is complete when the supplied export has been processed under the agreed schema, the deterministic result/proof receipt is delivered, every held row carries a stable reason, and the owner-review summary reconciles to that receipt. Acceptance of this artifact does not mean a media asset is safe or authorized to publish.",
            "",
            "## Expansion option",
            "",
            f"A {_money(INTEGRATION_PRICE_USD_CENTS)} fixed integration sprint may be scoped **only after the paid diagnostic is complete** and a concrete adapter boundary is known. No custom adapter is included in the diagnostic price and no free speculative adapter work is promised.",
            "",
            "## Authority ceiling",
            "",
            "This pilot is metadata-only pre-release QA. It does not determine rights, access DRM secrets, edit media, transcode, publish, mutate a CDN/provider, authenticate payment, establish buyer acceptance, or recognize revenue.",
            "",
        ]
    )


def build_bundle() -> dict[str, str]:
    receipt = build_proof_receipt()
    files = {
        "synthetic-diagnostic.md": render_synthetic_diagnostic(receipt),
        "scope-and-price.md": render_scope_markdown(receipt),
        "proof-receipt.json": json.dumps(receipt, sort_keys=True, indent=2) + "\n",
    }
    manifest_body = {
        "schema": BUNDLE_SCHEMA,
        "files": {name: _sha256(content.encode("utf-8")) for name, content in files.items()},
        "proof_receipt_sha256": receipt["receipt_sha256"],
        "external_authority": dict(EXTERNAL_AUTHORITY),
    }
    files["bundle-manifest.json"] = json.dumps(manifest_body, sort_keys=True, indent=2) + "\n"
    return files


def write_bundle(target: str | Path) -> dict[str, str]:
    target_path = Path(target)
    if target_path.exists() or target_path.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing output: {target_path}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    files = build_bundle()
    target_path.mkdir(mode=0o700)
    try:
        for name, content in files.items():
            destination = target_path / name
            with destination.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    except Exception:
        shutil.rmtree(target_path, ignore_errors=True)
        raise
    return {name: _sha256(content.encode("utf-8")) for name, content in files.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic Streaming Rendition QA paid-pilot packet")
    parser.add_argument("output", help="new output directory; existing paths are refused")
    args = parser.parse_args(argv)
    try:
        files = write_bundle(args.output)
    except Exception as exc:
        parser.exit(1, f"streaming-rendition-qa-pilot: {exc}\n")
    print(json.dumps({"ok": True, "schema": SCHEMA, "files": files}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
