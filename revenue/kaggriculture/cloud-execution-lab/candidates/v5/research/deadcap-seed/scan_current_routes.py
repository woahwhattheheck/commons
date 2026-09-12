# SPDX-License-Identifier: Apache-2.0
"""Static census for the exact canonical Arlene route family used by V5."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from deadcap_seed import census_authored_routes

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[3]
VENDOR = LAB / "reference" / "next-panel" / "vendor" / "arlene.py"


def _load_vendor(path: Path):
    spec = importlib.util.spec_from_file_location("deadcap_v5_current_routes", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load current route vendor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    raw = VENDOR.read_bytes()
    vendor = _load_vendor(VENDOR)
    routes = vendor.routes()
    report = census_authored_routes(routes)
    out = {
        "schema": "titan-v5-deadcap-seed-census-v1",
        "vendor_path": str(VENDOR.relative_to(LAB)),
        "vendor_sha256": hashlib.sha256(raw).hexdigest(),
        "route_count": len(routes) if isinstance(routes, dict) else None,
        "route_lengths": ({str(k): len(v) for k, v in routes.items()}
                          if isinstance(routes, dict) else None),
        "census": report,
    }
    print(json.dumps(out, sort_keys=True, separators=(",", ":")))
    return 0 if report.get("certified") else 2


if __name__ == "__main__":
    raise SystemExit(main())
