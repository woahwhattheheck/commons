#!/usr/bin/env python3
"""Fail-closed Shipaton readiness compiler.

Source completeness alone can never produce READY. External provider/store/submission
observations must be supplied in a separate witness JSON via --witness.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

EXTERNAL_FIELDS = (
    "revenuecat_account_verified",
    "revenuecat_product_offering_verified",
    "store_developer_account_verified",
    "store_publication_verified",
    "public_store_url",
    "demo_video_url",
    "screenshot_evidence",
    "devpost_submission_verified",
)

def parse_utc(s: str) -> datetime:
    value = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if value.tzinfo is None: raise ValueError("timestamp missing timezone")
    return value.astimezone(timezone.utc)

def compile_readiness(manifest: dict, witness: dict | None) -> dict:
    reasons: list[str] = []
    if manifest.get("submission_ready") is True:
        reasons.append("manifest may not self-assert submission_ready")
    app = manifest.get("app", {})
    if app.get("platform") != "android": reasons.append("carrier is not Android")
    if not app.get("first_public_release_required"): reasons.append("new-first-release requirement not bound")
    source = manifest.get("source", {})
    if source.get("status") != "implemented": reasons.append("source not implemented")
    if source.get("entitlement") != "pro": reasons.append("RevenueCat entitlement mismatch")
    try: deadline = parse_utc(manifest["deadline_utc"])
    except Exception: reasons.append("invalid deadline"); deadline = datetime.min.replace(tzinfo=timezone.utc)

    if witness is None:
        reasons.append("external witness absent; source cannot mint competition readiness")
    else:
        if witness.get("authority") != "external-provider-observation": reasons.append("external witness authority mismatch")
        if witness.get("package") != app.get("package"): reasons.append("witness package identity drift")
        if witness.get("version_code") != app.get("version_code"): reasons.append("witness version identity drift")
        try:
            observed_at = parse_utc(witness["observed_at_utc"])
            if observed_at > deadline: reasons.append("external witness was observed after competition deadline")
        except Exception: reasons.append("invalid external witness timestamp")
        for key in EXTERNAL_FIELDS:
            value = witness.get(key)
            if key.endswith("_url"):
                if not isinstance(value, str) or not value.startswith("https://"): reasons.append(f"missing/invalid {key}")
            elif key == "screenshot_evidence":
                if not isinstance(value, str) or not value.strip(): reasons.append("missing screenshot_evidence")
            elif value is not True:
                reasons.append(f"external gate not verified: {key}")

    identity = json.dumps({"app": app, "source": source}, sort_keys=True, separators=(",", ":")).encode()
    return {
        "status": "READY" if not reasons else "HOLD",
        "identity_sha256": hashlib.sha256(identity).hexdigest(),
        "reasons": reasons,
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--witness", type=Path)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text())
    witness = json.loads(args.witness.read_text()) if args.witness else None
    result = compile_readiness(manifest, witness)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"{result['status']} {result['identity_sha256']}\n" + "\n".join(f"- {x}" for x in result["reasons"]))
    return 0 if result["status"] == "READY" else 2

if __name__ == "__main__": raise SystemExit(main())
