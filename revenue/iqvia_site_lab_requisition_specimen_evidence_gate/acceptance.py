"""Executable acceptance contract for the frozen 180-packet fixture."""
from __future__ import annotations

import hashlib

from .fixtures import (
    expected_holds,
    frozen_packets,
    frozen_reference_set,
    frozen_reference_sha256,
)
from .gate import (
    CODES,
    STATUS_HOLD,
    STATUS_READY,
    evaluate_batch,
    output_manifest,
    render_csv,
    render_json,
    verify_batch,
)


def run_acceptance() -> dict[str, object]:
    reference = frozen_reference_set()
    trusted_digest = frozen_reference_sha256()
    packets = frozen_packets()
    report_a = evaluate_batch(packets, reference, trusted_digest)
    report_b = evaluate_batch(frozen_packets(), frozen_reference_set(), trusted_digest)
    json_a, json_b = render_json(report_a), render_json(report_b)
    csv_a, csv_b = render_csv(report_a), render_csv(report_b)

    if report_a["packet_count"] != 180:
        raise AssertionError("acceptance requires exactly 180 packets")
    if report_a["status_counts"] != {STATUS_READY: 150, STATUS_HOLD: 30}:
        raise AssertionError("acceptance requires 150 ready / 30 hold")
    if report_a["reason_counts"] != {code: 5 for code in CODES}:
        raise AssertionError("acceptance requires exactly five holds per reason family")
    if json_a != json_b or csv_a != csv_b:
        raise AssertionError("acceptance outputs must be byte-identical on rerun")
    if not verify_batch(report_a, frozen_packets(), frozen_reference_set(), trusted_digest):
        raise AssertionError("acceptance report must recompile under the pinned reference")

    rows = {row["packet_id"]: row for row in report_a["results"]}
    expected = expected_holds()
    held_ids = set()
    for code, packet_ids in expected.items():
        for packet_id in packet_ids:
            held_ids.add(packet_id)
            if rows[packet_id]["status"] != STATUS_HOLD:
                raise AssertionError(f"{packet_id} must hold")
            if rows[packet_id]["reason_codes"] != [code]:
                raise AssertionError(f"{packet_id} must emit only {code}")

    for i in range(1, 151):
        row = rows[f"SLR-{i:04d}"]
        if row["status"] != STATUS_READY or row["reason_codes"]:
            raise AssertionError(f"SLR-{i:04d} must be ready with no reason code")
        if row["reference_sha256"] != trusted_digest:
            raise AssertionError("ready row lost trusted reference binding")

    if held_ids != {f"SLR-{i:04d}" for i in range(151, 181)}:
        raise AssertionError("held packet IDs do not match the frozen contract")

    manifest = output_manifest(report_a)
    if manifest["reference_sha256"] != trusted_digest:
        raise AssertionError("manifest lost trusted reference binding")
    return {
        "status": "PASS",
        "packets": 180,
        "ready": 150,
        "hold": 30,
        "reason_counts": report_a["reason_counts"],
        "reference_generation_id": report_a["reference_generation_id"],
        "reference_sha256": report_a["reference_sha256"],
        "batch_digest": report_a["batch_digest"],
        "json_sha256": hashlib.sha256(json_a).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_a).hexdigest(),
        "manifest": manifest,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_acceptance(), sort_keys=True, indent=2))
