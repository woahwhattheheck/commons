"""Frozen synthetic acceptance fixtures for the IQVIA Site Lab evidence gate."""
from __future__ import annotations

import copy
import hashlib
from typing import Any

from .gate import CODES, SCHEMA


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _base(index: int) -> dict[str, Any]:
    packet_id = f"SLR-{index:04d}"
    refs = {
        key: _h(f"{packet_id}:{key}:source-v1")
        for key in (
            "protocol",
            "requisition",
            "kit",
            "collection",
            "courier",
            "accession",
            "method",
            "queries",
        )
    }
    return {
        "schema": SCHEMA,
        "packet_id": packet_id,
        "protocol_id": "PROTO-ALPHA",
        "expected_protocol_id": "PROTO-ALPHA",
        "expected_visit_id": "VISIT-02",
        "requisition_protocol_id": "PROTO-ALPHA",
        "requisition_visit_id": "VISIT-02",
        "requisition_version": "REQ-v3",
        "kit_lot": f"KIT-{(index % 7) + 1:02d}",
        "kit_expires_at": "2026-10-01T00:00:00Z",
        "collection_at": "2026-09-13T12:00:00Z",
        "collection_window_start": "2026-09-13T08:00:00Z",
        "collection_window_end": "2026-09-13T16:00:00Z",
        "courier_scan_id": f"COURIER-{index:04d}",
        "courier_temperature_c": 4.0,
        "courier_min_c": 2.0,
        "courier_max_c": 8.0,
        "accession_id": f"ACC-{index:04d}",
        "sample_type": "SERUM",
        "required_sample_type": "SERUM",
        "method_id": "METHOD-CHEM-7",
        "method_allowed_sample_types": ["PLASMA", "SERUM"],
        "queries": [
            {
                "query_id": f"Q-{index:04d}-1",
                "status": "RESOLVED",
                "resolution_evidence_hash": _h(f"{packet_id}:query-resolution"),
            }
        ],
        "source_refs": refs,
    }


def frozen_packets() -> list[dict[str, Any]]:
    packets = [_base(i) for i in range(1, 181)]

    for packet in packets[150:155]:
        packet["requisition_visit_id"] = "VISIT-03"

    for packet in packets[155:160]:
        packet["kit_expires_at"] = "2026-09-12T23:59:59Z"

    for packet in packets[160:165]:
        packet["collection_at"] = "2026-09-13T17:00:00Z"

    for packet in packets[165:170]:
        packet["courier_scan_id"] = None
        packet["courier_temperature_c"] = None

    for packet in packets[170:175]:
        packet["sample_type"] = "WHOLE_BLOOD"

    for packet in packets[175:180]:
        packet["queries"][0]["status"] = "OPEN"
        packet["queries"][0]["resolution_evidence_hash"] = None

    return copy.deepcopy(packets)


def expected_holds() -> dict[str, list[str]]:
    return {
        code: [f"SLR-{i:04d}" for i in range(start, start + 5)]
        for code, start in zip(CODES, (151, 156, 161, 166, 171, 176))
    }
