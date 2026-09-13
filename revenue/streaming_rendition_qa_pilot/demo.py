from __future__ import annotations

import json
from typing import Any

from revenue.streaming_rendition_release_gate.fixture import build_fixture

from .pilot import DIAGNOSTIC, SCHEMA, compile_receipt


def build_demo_intake() -> dict[str, Any]:
    packets, _ = build_fixture()
    selected = packets[:5] + [packets[140 + 4 * idx] for idx in range(7)]
    return {
        "schema": SCHEMA,
        "pilot_id": "demo-rendition-qa-001",
        "customer_ref": "synthetic-buyer",
        "tier": DIAGNOSTIC,
        "packets": selected,
    }


def main() -> int:
    receipt = compile_receipt(build_demo_intake())
    payload = {
        "report": receipt["report"],
        "report_sha256": receipt["report_sha256"],
    }
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
