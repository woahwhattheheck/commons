#!/usr/bin/env python3
"""Reproduce same-submission changed-payload double accession on current Agri Seed gate.

This is a frozen negative witness for BD03. Exit 0 means the predecessor defect
is present: two individually valid rows with one stable submission_id but
materially different payloads/bag barcodes both accession, even when the second
row carries a stale copied source_sha256 from the first payload.
"""
from __future__ import annotations

import json

import agriseed_rush_work_allocator as gate


def main() -> int:
    first, second = gate.build_acceptance_fixture()[:2]
    changed = dict(second)
    changed["submission_id"] = first["submission_id"]
    # Deliberately copy the old caller-supplied digest. A correct replay guard
    # must bind/recompute canonical payload identity rather than trust this field.
    changed["source_sha256"] = first["source_sha256"]

    result = gate.run_gate([first, changed])
    same_id_accessions = [
        row for row in result["accessions"] if row["submission_id"] == first["submission_id"]
    ]
    reproduced = (
        result["ok"] is True
        and result["accessioned"] == 2
        and result["held"] == 0
        and len(same_id_accessions) == 2
        and same_id_accessions[0]["bag_barcode"] != same_id_accessions[1]["bag_barcode"]
        and same_id_accessions[0]["report_sha256"] != same_id_accessions[1]["report_sha256"]
        and result["released_after_named_human"] == 2
    )
    evidence = {
        "schema": "agriseed-submission-payload-replay-reproducer/v1",
        "reproduced": reproduced,
        "submission_id": first["submission_id"],
        "input_source_sha256s_equal": first["source_sha256"] == changed["source_sha256"],
        "accessioned": result["accessioned"],
        "held": result["held"],
        "same_id_accession_count": len(same_id_accessions),
        "accession_ids": [row["accession_id"] for row in same_id_accessions],
        "bag_barcodes": [row["bag_barcode"] for row in same_id_accessions],
        "report_sha256s": [row["report_sha256"] for row in same_id_accessions],
        "released_after_named_human": result["released_after_named_human"],
        "expected_repair": (
            "bind each successfully accessioned submission_id to a freshly computed canonical "
            "_source_payload digest; exact replay must not accession again and changed-payload "
            "same-ID input must fail closed before bag/release mutation"
        ),
        "out_of_scope": "held-to-corrected first-seen binding remains BD04",
    }
    print(json.dumps(evidence, sort_keys=True, indent=2))
    return 0 if reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())
