# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import ablate_e08 as e08

REPO = Path(__file__).resolve().parents[6]


def git_show(commit: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{commit}:{e08.SOURCE_PATH}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout


class E08SubmittedV4AblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v4 = git_show(e08.V4_SOURCE_COMMIT)
        cls.v31 = git_show(e08.V31_SOURCE_COMMIT)
        cls.patched, cls.receipt = e08.ablate_submitted_v4(cls.v4)
        cls.patched_text = cls.patched.decode("utf-8")

    def test_exact_historical_source_authorities(self):
        self.assertEqual(e08.git_blob_sha1(self.v4), e08.V4_FROZEN_GIT_BLOB)
        self.assertEqual(e08.git_blob_sha1(self.v31), e08.V31_FROZEN_GIT_BLOB)
        self.assertEqual(self.receipt["control_source_git_blob"], e08.V4_FROZEN_GIT_BLOB)
        self.assertEqual(self.receipt["reference_v31_source_git_blob"], e08.V31_FROZEN_GIT_BLOB)

    def test_rejects_any_non_exact_v4_input(self):
        bad = bytearray(self.v4)
        bad[-2] ^= 1
        with self.assertRaises(e08.SourceAuthorityError):
            e08.ablate_submitted_v4(bytes(bad))

    def test_patch_is_deterministic_and_compilable(self):
        again, again_receipt = e08.ablate_submitted_v4(self.v4)
        self.assertEqual(again, self.patched)
        self.assertEqual(again_receipt, self.receipt)
        compile(self.patched, "e08-treatment", "exec")
        self.assertNotEqual(self.patched, self.v4)

    def test_transform_no_longer_calls_e08_horizon_family(self):
        transform = self.patched_text.split("class FrozenSelected", 1)[1]
        self.assertNotIn("end,horizon=event_aware_horizon(", transform)
        self.assertNotIn("unit_event=(represented_shed_event(", transform)
        self.assertNotIn("dates=product_event_dates(", transform)
        self.assertIn("end=min(now+HORIZON,last,(now//24+1)*24-1)", transform)
        self.assertIn("if now<checkpoint<=end:end=checkpoint-1", transform)
        self.assertIn("item_end=end", transform)

    def test_all_e08_downstream_windows_collapse_to_fixed_end(self):
        transform = self.patched_text.split("class FrozenSelected", 1)[1]
        self.assertNotIn("item_end=max(", transform)
        self.assertEqual(transform.count("item_end=end"), 1)
        # Post-E08 V4 mechanics are deliberately retained, but each sees the
        # fixed V3.1-style boundary through item_end=end.
        for token in (
            "reference.append((min(t,item_end),q))",
            "for t in range(now+1,item_end+1):",
            "item_budget=self.cash_reserve(obs,config,base,item_end)",
            "funded_minimum_now(obs,config,base,farm,private,route,item_end,",
            "self.receipt_profile(obs,base,farm,private,item_end,item,config)",
        ):
            self.assertIn(token, transform, token)
        # Joint SELL keeps its later-V4 implementation but stays on the same
        # fixed global end, so this treatment does not ablate E05.
        self.assertIn(
            "joint_resource_bound(obs,config,base,farm,private,route,end)",
            transform,
        )

    def test_treatment_does_not_stamp_trace_only_ablation_marker(self):
        transform = self.patched_text.split("class FrozenSelected", 1)[1]
        self.assertNotIn("submitted-v31-fixed", transform)
        self.assertNotIn("'ablation'", transform)
        self.assertIn("'unit_event':None,'extended':False", transform)

    def test_submitted_v31_contains_same_fixed_horizon_boundary(self):
        text = self.v31.decode("utf-8")
        self.assertIn("end=min(now+HORIZON,last,(now//24+1)*24-1)", text)
        self.assertIn("if now<checkpoint<=end:end=checkpoint-1", text)
        self.assertIn(
            "dates=[now]+[t for t in range(now+1,end+1) if any(absorption(p,t-1,shops,config) for p in PRODUCTS)]",
            text,
        )

    def test_later_v4_mechanics_remain_present(self):
        for token in (
            "funded_minimum_now(",
            "fund_same_turn_acquisition(",
            "joint_plan_metrics(",
            "seller_choice_rank(",
            "materialize_sales(",
        ):
            self.assertEqual(
                self.patched_text.count(token),
                self.v4.decode("utf-8").count(token),
                token,
            )
        self.assertEqual(
            self.receipt["preserved_v4_mechanics"],
            [
                "funded_minimum_now",
                "fund_same_turn_acquisition",
                "joint_plan_metrics",
                "seller_choice_rank",
                "materialize_sales",
            ],
        )

    def test_absorption_just_outside_old_window_stays_outside(self):
        end, dates = e08.legacy_horizon_and_dates(
            now=10, last=718, decisions=(), absorption_dates=(21,)
        )
        self.assertEqual(end, 18)
        self.assertEqual(dates, (10, 18))

    def test_checkpoint_still_clamps_before_future_event(self):
        end, dates = e08.legacy_horizon_and_dates(
            now=10, last=718, decisions=(15,), absorption_dates=(13, 21)
        )
        self.assertEqual(end, 14)
        self.assertEqual(dates, (10, 13, 14))

    def test_day_and_terminal_bounds_remain_hard(self):
        end, _ = e08.legacy_horizon_and_dates(
            now=20, last=718, decisions=(), absorption_dates=(29,)
        )
        self.assertEqual(end, 23)
        end, _ = e08.legacy_horizon_and_dates(
            now=713, last=718, decisions=(), absorption_dates=(719,)
        )
        self.assertEqual(end, 718)

    def test_generator_absorption_dates_are_stable(self):
        end, dates = e08.legacy_horizon_and_dates(
            now=10, last=718, decisions=(), absorption_dates=(d for d in (13, 17))
        )
        self.assertEqual(end, 18)
        self.assertEqual(dates, (10, 13, 17, 18))

    def test_helper_replacement_is_exact_once(self):
        text = e08._E08_HORIZON_BLOCK + "middle\n" + e08._E08_ITEM_WINDOW_BLOCK
        out = e08.rewrite_e08_text(text)
        self.assertEqual(out.count("'unit_event':None,'extended':False"), 1)
        self.assertNotIn("submitted-v31-fixed", out)
        self.assertEqual(out.count("item_end=end"), 1)
        with self.assertRaises(e08.SourceAuthorityError):
            e08.rewrite_e08_text(text + e08._E08_HORIZON_BLOCK)


if __name__ == "__main__":
    unittest.main(verbosity=2)
