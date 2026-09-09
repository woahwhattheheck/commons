# SPDX-License-Identifier: Apache-2.0
"""Exact-current admission witnesses for the isolated Capillary candidate.

This review-only test intentionally uses the real current four-route controller
bank and the same imported module graph for control and candidate construction.
It does not mutate candidate, compiler, runtime, configuration, or game bytes.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]
LAB = REPO / "revenue" / "kaggriculture" / "cloud-execution-lab"
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import scheduler  # noqa: E402
import titan_capillary as capillary_module  # noqa: E402
from jit_seed_staging import compile_jit_expensive_seed_routes  # noqa: E402
from titan_capillary import CapillaryTitanAgent  # noqa: E402
from titan_runtime import TitanAgent  # noqa: E402


MARKER = ["BUY_SEED", "MELON", 1]


def digest(value) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def certified_marker_stage(routes, **_kwargs):
    """Deterministic changed compiler result used only to expose ownership."""
    staged = deepcopy(dict(routes))
    route_name = next(iter(staged))
    route = list(staged[route_name])
    action = deepcopy(route[0])
    action["market"] = list(action.get("market", [])) + [list(MARKER)]
    route[0] = action
    staged[route_name] = route
    return staged, {
        "changed": True,
        "certified": True,
        "reason": "ownership_witness",
        "changed_routes": [str(route_name)],
        "changed_steps": {str(route_name): [0]},
    }


class ExactCurrentCompilerAdmissionTests(unittest.TestCase):
    def test_real_four_route_bank_is_a_changed_certified_candidate(self):
        """A minimized one-route fixture cannot substitute for current bytes."""
        source = scheduler.parent.routes()
        before = deepcopy(source)
        before_digest = digest(before)

        staged, report = compile_jit_expensive_seed_routes(
            source,
            max_orders=10,
            turns_per_day=24,
        )
        after_source_digest = digest(source)
        staged_digest = digest(staged)
        receipt = {
            "route_count": len(source),
            "route_names": sorted(str(name) for name in source),
            "source_before_sha256": before_digest,
            "source_after_sha256": after_source_digest,
            "staged_sha256": staged_digest,
            "report": report,
        }
        print("CAPILLARY_EXACT_CURRENT_COMPILER=" + json.dumps(receipt, sort_keys=True))

        self.assertEqual(len(source), 4, receipt)
        self.assertEqual(source, before, receipt)
        self.assertEqual(after_source_digest, before_digest, receipt)
        self.assertTrue(report.get("certified"), receipt)
        self.assertTrue(report.get("changed"), receipt)
        self.assertNotEqual(staged_digest, before_digest, receipt)
        self.assertTrue(report.get("changed_routes"), receipt)
        self.assertTrue(report.get("changed_steps"), receipt)


class ExactCurrentRouteOwnershipTests(unittest.TestCase):
    def test_candidate_never_mutates_parent_global_or_plain_instance_routes(self):
        """Control and candidate must remain isolated in one interpreter graph."""
        parent = scheduler.parent
        shared = parent.routes()
        shared_snapshot = deepcopy(shared)
        shared_digest = digest(shared_snapshot)

        plain = TitanAgent()
        plain._initialize()
        self.assertIs(plain.controller.R, shared)
        self.assertEqual(digest(plain.controller.R), shared_digest)

        candidate = CapillaryTitanAgent()
        candidate._capillary_configuration = {
            "maxMarketOrdersPerTurn": 10,
            "turnsPerDay": 24,
        }
        try:
            with patch.object(
                capillary_module,
                "compile_jit_expensive_seed_routes",
                side_effect=certified_marker_stage,
            ):
                candidate._initialize()

            receipt = {
                "shared_identity": id(shared),
                "plain_identity": id(plain.controller.R),
                "candidate_identity": id(candidate.controller.R),
                "spatial_identity": id(candidate.spatial._crop_routes),
                "shared_sha256": digest(shared),
                "plain_sha256": digest(plain.controller.R),
                "candidate_sha256": digest(candidate.controller.R),
                "compile_report": candidate._capillary_compile_report,
            }
            print("CAPILLARY_EXACT_CURRENT_OWNERSHIP=" + json.dumps(receipt, sort_keys=True))

            self.assertTrue(candidate._capillary_compile_report.get("certified"), receipt)
            self.assertIsNot(candidate.controller.R, shared, receipt)
            self.assertIsNot(candidate.controller.R, plain.controller.R, receipt)
            self.assertIs(candidate.spatial._crop_routes, candidate.controller.R, receipt)
            self.assertEqual(parent.routes(), shared_snapshot, receipt)
            self.assertEqual(plain.controller.R, shared_snapshot, receipt)

            later_plain = TitanAgent()
            later_plain._initialize()
            self.assertIs(later_plain.controller.R, shared, receipt)
            self.assertEqual(later_plain.controller.R, shared_snapshot, receipt)
        finally:
            # Restore the shared module bank even when predecessor bytes fail the
            # admission assertion, so this evidence test cannot contaminate any
            # subsequent test in the hosted process.
            shared.clear()
            shared.update(deepcopy(shared_snapshot))


if __name__ == "__main__":
    unittest.main(verbosity=2)
