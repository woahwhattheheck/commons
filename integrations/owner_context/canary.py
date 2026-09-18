#!/usr/bin/env python3
"""Offline canary for the owner-context display host pack.

No live public IP, no provider deploy, no secrets. Values that look like
addresses must never print.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "host") not in sys.path:
    sys.path.insert(0, str(ROOT / "host"))

import owner_context as oc
import owner_enroll
import owner_net

FIXTURE = "192.0.2.1"


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def run() -> dict:
    checks = []
    spec = {
        "claim": "BRYCE",
        "algo": "sha256",
        "pepper": "commons-owner-v1",
        "slots": {
            "pc": {"sha256": owner_enroll.digest_ip(FIXTURE)},
            "phone": {"sha256": owner_enroll.digest_ip("2001:db8::1")},
        },
        "hashes": [],
        "context_host": {"k": "owner-context", "public_url": "", "candidates": []},
    }
    owner_net.refresh_hashes(spec)
    payload = oc.simulate(FIXTURE, "pc", spec=spec)
    blob = json.dumps(payload)
    checks.append(_check("simulate_available", payload.get("available") is True))
    checks.append(_check("display_only", payload.get("display_only") is True and payload.get("authority") is False))
    checks.append(_check("no_raw_ip", FIXTURE not in blob and "2001:db8" not in blob))
    status, _headers, body = oc.handle_http("GET", "/owner-context", {}, b"", "", spec=spec)
    checks.append(_check("missing_peer_200", status == 200 and json.loads(body)["available"] is False))
    spoof = oc.handle_http(
        "POST",
        "/owner-context",
        {"X-Real-IP": FIXTURE},
        json.dumps({"sha256": owner_enroll.digest_ip("2001:db8::1"), "via": "phone"}).encode(),
        "",
        spec=spec,
    )
    spoofed = json.loads(spoof[2])
    checks.append(_check("spoof_digest_ignored", spoofed.get("slot") == "pc"))
    report = oc.doctor(spec=spec, probe=False, root=str(ROOT))
    checks.append(_check("doctor_not_live", report.get("live") is False))
    checks.append(_check("doctor_names_external", "EXTERNAL_HOST_ACTION" in report and bool(report["EXTERNAL_HOST_ACTION"])))
    failed = [row for row in checks if not row["ok"]]
    return {"ok": not failed, "checks": checks, "failed": failed}


def main() -> int:
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
