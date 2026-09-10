# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from route_probe import compare_snapshots


class RouteProbeTests(unittest.TestCase):
    def test_exact_transform(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            mechanism = root / "land_admission.py"
            mechanism.write_text(
                "BUY_LAND='BUY_LAND'\n"
                "def patch_routes(routes):\n"
                "    sites=[]\n"
                "    for name, route in routes.items():\n"
                "        route[1].setdefault('market', []).append([BUY_LAND])\n"
                "        sites.append({'route':name,'step':1,'market_index':0})\n"
                "    return {'activations':len(sites),'sites':sites}\n",
                encoding="utf-8",
            )
            before_routes = {
                "MAIN": [
                    {"market": []},
                    {"market": []},
                ]
            }
            after_routes = {
                "MAIN": [
                    {"market": []},
                    {"market": [["BUY_LAND"]]},
                ]
            }
            def snapshot(routes):
                payload = json.dumps(
                    routes, sort_keys=True, separators=(",", ":")
                ).encode()
                return {
                    "routes": routes,
                    "routes_sha256": hashlib.sha256(payload).hexdigest(),
                    "route_count": 1,
                }

            report = compare_snapshots(
                snapshot(before_routes),
                snapshot(after_routes),
                mechanism,
            )
            self.assertTrue(report["exact_transform_match"])
            self.assertEqual(report["changed_rows"], 1)
            self.assertEqual(report["first_divergence"]["step"], 1)


if __name__ == "__main__":
    unittest.main()
