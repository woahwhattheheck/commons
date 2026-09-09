from __future__ import annotations

from copy import deepcopy
import unittest

from analyze_panel import analyze_panel
from quadrant_payback import (
    CandidateVariant,
    CostLedger,
    LAST_SETTLED_STEP,
    ProjectedChain,
    assert_candidate_only_delta,
    candidate_variants,
    certify_completion,
    latest_safe_start_day,
    patch_titan_config,
)


def chain(**changes: object) -> ProjectedChain:
    values: dict[str, object] = {
        "start_step": 0,
        "buy_land_step": 0,
        "buy_seed_step": 0,
        "plant_step": 1,
        "service_steps": (2, 3),
        "harvest_step": 10,
        "deposit_step": 11,
        "sale_step": 12,
        "units_sold": 100,
        "observed_unit_quote": 120,
        "quote_observed_step": 0,
        "observed_cash": 20000,
        "cash_reserve": 6000,
        "costs": CostLedger(land=2000, seed=1000, labor=1000, service=1000),
        "product": "WHEAT",
    }
    values.update(changes)
    return ProjectedChain(**values)  # type: ignore[arg-type]


def base_config() -> dict[str, object]:
    return {
        "feature_ledger": {"runtime_features": {"fourth_quadrant": False, "other": True}},
        "fourth_quadrant": {
            "amount": 13,
            "cash_reserve": 10000,
            "max_start_day": 16,
            "movement_mode": "safe",
            "product": "WHEAT",
            "quadrant_indices": [3],
        },
        "untouched": {"x": 1},
    }


def panel_rows(variant: str = "fq-r6000-d8") -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for split, seeds in (("development", range(16)), ("holdout", range(100, 116))):
        for opponent in ("current", "arlene", "retained"):
            for seed in seeds:
                for seat in (0, 1):
                    rows.append(
                        {
                            "variant": variant,
                            "split": split,
                            "opponent": opponent,
                            "seed": seed,
                            "seat": seat,
                            "candidate_terminal_cash": 10010,
                            "control_terminal_cash": 10000,
                            "complete": True,
                            "timeout": False,
                            "error": False,
                            "activated": seed == min(seeds) and seat == 0,
                            "chain": chain().canonical_payload(),
                        }
                    )
    return rows


class CompletionCertificateTests(unittest.TestCase):
    def test_complete_profitable_chain_admits(self) -> None:
        result = certify_completion(chain())
        self.assertTrue(result.admitted)
        self.assertEqual(result.reason, "complete_prefunded_profitable_chain")
        self.assertEqual(result.net_terminal_value, 7000)

    def test_same_turn_seed_and_plant_declines(self) -> None:
        result = certify_completion(chain(buy_seed_step=1))
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "seed_not_owned_before_plant")

    def test_future_sale_cannot_fund_entry(self) -> None:
        result = certify_completion(chain(observed_cash=10999))
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "not_prefunded_without_future_sale")

    def test_future_quote_declines(self) -> None:
        result = certify_completion(chain(quote_observed_step=1))
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "future_or_unobserved_quote")

    def test_terminal_settlement_is_hard(self) -> None:
        self.assertTrue(certify_completion(chain(sale_step=LAST_SETTLED_STEP)).admitted)
        self.assertEqual(
            certify_completion(chain(sale_step=LAST_SETTLED_STEP + 1)).reason,
            "sale_after_terminal_settlement",
        )

    def test_terminal_value_must_strictly_exceed_cost(self) -> None:
        result = certify_completion(chain(units_sold=50, observed_unit_quote=100))
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "terminal_value_does_not_exceed_incremental_cost")

    def test_digest_is_deterministic_and_sensitive(self) -> None:
        self.assertEqual(chain().digest, chain().digest)
        self.assertNotEqual(chain().digest, chain(sale_step=13).digest)

    def test_latest_start_day_is_derived_from_settlement(self) -> None:
        self.assertEqual(latest_safe_start_day(productive_latency_steps=430), 12)
        self.assertEqual(latest_safe_start_day(productive_latency_steps=719), -1)


class CandidateConfigTests(unittest.TestCase):
    def test_grid_is_exact_and_unique(self) -> None:
        variants = candidate_variants()
        self.assertEqual(len(variants), 6)
        self.assertEqual(len({item.variant_id for item in variants}), 6)
        self.assertEqual(
            {item.variant_id for item in variants},
            {
                "fq-r6000-d8", "fq-r7500-d8", "fq-r9000-d8",
                "fq-r6000-d12", "fq-r7500-d12", "fq-r9000-d12",
            },
        )

    def test_patch_changes_only_allowed_leaves(self) -> None:
        before = base_config()
        after = patch_titan_config(before, CandidateVariant("fq-r6000-d8", 6000, 8))
        deltas = assert_candidate_only_delta(before, after)
        self.assertIn("/feature_ledger/runtime_features/fourth_quadrant", deltas)
        self.assertIn("/fourth_quadrant/cash_reserve", deltas)
        self.assertIn("/fourth_quadrant/max_start_day", deltas)
        self.assertEqual(before["untouched"], after["untouched"])

    def test_unexpected_delta_rejected(self) -> None:
        before = base_config()
        after = patch_titan_config(before, CandidateVariant("fq-r6000-d8", 6000, 8))
        after["rogue"] = True
        with self.assertRaisesRegex(ValueError, "unexpected candidate config"):
            assert_candidate_only_delta(before, after)


class PanelTests(unittest.TestCase):
    def test_complete_positive_panel_goes(self) -> None:
        result = analyze_panel(panel_rows())
        self.assertEqual(result["global_disposition"], "GO")
        self.assertEqual(result["selected_variant"], "fq-r6000-d8")

    def test_negative_heldout_bucket_holds(self) -> None:
        rows = panel_rows()
        for row in rows:
            if row["split"] == "holdout" and row["opponent"] == "arlene" and row["seat"] == 1:
                row["candidate_terminal_cash"] = 9000
        result = analyze_panel(rows)
        self.assertEqual(result["global_disposition"], "HOLD")

    def test_incomplete_game_holds(self) -> None:
        rows = panel_rows()
        rows[0]["complete"] = False
        result = analyze_panel(rows)
        self.assertEqual(result["global_disposition"], "HOLD")
        self.assertTrue(result["variants"][0]["failures"])

    def test_development_and_holdout_must_be_disjoint(self) -> None:
        rows = panel_rows()
        for row in rows:
            if row["split"] == "holdout" and row["seed"] == 100:
                row["seed"] = 0
        with self.assertRaisesRegex(ValueError, "development/holdout seed overlap"):
            analyze_panel(rows)

    def test_two_go_variants_do_not_authorize_integration(self) -> None:
        rows = panel_rows("fq-r6000-d8") + panel_rows("fq-r7500-d8")
        result = analyze_panel(rows)
        self.assertEqual(result["global_disposition"], "HOLD_MULTIPLE_GO_VARIANTS")
        self.assertFalse(result["canonical_enablement_authorized"])

    def test_missing_activation_chain_holds(self) -> None:
        rows = panel_rows()
        for row in rows:
            if row["activated"]:
                row["chain"] = None
                break
        result = analyze_panel(rows)
        self.assertEqual(result["global_disposition"], "HOLD")


if __name__ == "__main__":
    unittest.main()
