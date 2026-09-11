# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from certified_report_v2 import CertifiedReportError, build_report


def report(rows):
    return {"games": rows}


def diag(*, source_seat=0, steps=(), checks=None, matches=None, handoff_step=696, handoff_reason="missing_route_row"):
    steps = list(steps)
    if matches is None:
        matches = len(steps)
    if checks is None:
        checks = matches
    return {
        "mode": "post24_full",
        "certificate_mode": "full",
        "source_seat": source_seat,
        "start_step": 24,
        "active": handoff_step is None,
        "handoff_step": handoff_step,
        "handoff_reason": handoff_reason,
        "certificate_checks": checks,
        "certificate_matches": matches,
        "activation_count": len(steps),
        "activation_steps": steps,
        "certificate_donor_head": "cbfff2bec813e2c2609ce9c5819b74669e98c566",
        "certificate_donor_blob": "89a3325eb541ae0e8a81e1e0a426292820f10d98",
        "market_outcome_claim": False,
    }


def game(opponent, seed, seat, scores, trace, runtime_diag=None):
    actors = [{}, {}]
    if runtime_diag is not None:
        actors[seat]["agent_diagnostics"] = runtime_diag
    return {
        "status": "complete",
        "failure": None,
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "scores": scores,
        "trace_sha256": trace,
        "actors": actors,
    }


class CertifiedReportV2Tests(unittest.TestCase):
    def write(self, root, name, rows):
        path = root / name
        path.write_text(json.dumps(report(rows)), encoding="utf-8")
        return path

    def build(self, root, certified_rows):
        control_rows = [
            game("arlene", 1, 0, [100, 90], "c0"),
            game("arlene", 1, 1, [90, 100], "c1"),
        ]
        unsafe_rows = [
            game("arlene", 1, 0, [120, 90], "u0"),
            game("arlene", 1, 1, [90, 120], "u1"),
        ]
        return build_report(
            self.write(root, "control.json", control_rows),
            self.write(root, "unsafe.json", unsafe_rows),
            self.write(root, "certified.json", certified_rows),
            source_seat=0,
        )

    def test_runtime_activation_survives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.build(
                root,
                [
                    game("arlene", 1, 0, [110, 90], "g0", diag(steps=[24], checks=1, matches=1)),
                    game(
                        "arlene",
                        1,
                        1,
                        [90, 100],
                        "c1",
                        diag(steps=[], checks=0, matches=0, handoff_step=24, handoff_reason="source_seat_mismatch"),
                    ),
                ],
            )
            self.assertEqual(result["verdict"], "CERTIFIED_SURVIVOR")
            self.assertTrue(result["source_seat_activated"])
            self.assertEqual(result["source_seat_activation_events"], 1)

    def test_trace_change_without_runtime_activation_is_not_activation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.build(
                root,
                [
                    game("arlene", 1, 0, [110, 90], "changed", diag(steps=[], checks=1, matches=1)),
                    game(
                        "arlene",
                        1,
                        1,
                        [90, 100],
                        "c1",
                        diag(steps=[], checks=0, matches=0, handoff_step=24, handoff_reason="source_seat_mismatch"),
                    ),
                ],
            )
            self.assertEqual(result["verdict"], "CERTIFICATE_REJECTS_TRANSPLANT")
            self.assertFalse(result["source_seat_activated"])
            self.assertGreater(result["certified_prefix"]["trace_changed_cells"], 0)

    def test_missing_runtime_diagnostics_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(CertifiedReportError, "diagnostics are absent"):
                self.build(
                    root,
                    [
                        game("arlene", 1, 0, [110, 90], "g0"),
                        game(
                            "arlene",
                            1,
                            1,
                            [90, 100],
                            "c1",
                            diag(steps=[], checks=0, matches=0, handoff_step=24, handoff_reason="source_seat_mismatch"),
                        ),
                    ],
                )

    def test_inconsistent_activation_count_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            broken = diag(steps=[24], checks=1, matches=1)
            broken["activation_count"] = 0
            with self.assertRaisesRegex(CertifiedReportError, "activation_count"):
                self.build(
                    root,
                    [
                        game("arlene", 1, 0, [110, 90], "g0", broken),
                        game(
                            "arlene",
                            1,
                            1,
                            [90, 100],
                            "c1",
                            diag(steps=[], checks=0, matches=0, handoff_step=24, handoff_reason="source_seat_mismatch"),
                        ),
                    ],
                )

    def test_off_seat_activation_blocks_exact_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.build(
                root,
                [
                    game("arlene", 1, 0, [110, 90], "g0", diag(steps=[24], checks=1, matches=1)),
                    game("arlene", 1, 1, [90, 100], "c1", diag(steps=[24], checks=1, matches=1)),
                ],
            )
            self.assertEqual(result["verdict"], "CERTIFIED_HOLD")
            self.assertFalse(result["off_seat_exact_fallback"])


if __name__ == "__main__":
    unittest.main()
