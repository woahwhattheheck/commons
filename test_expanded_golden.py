#!/usr/bin/env python3
"""Focused tests for independent expanded-golden digest binding."""
from __future__ import annotations

from copy import deepcopy
import unittest

from host.expanded_golden import (
    ExpandedGoldenError,
    canonical_expanded_rows,
    verify_expanded_golden,
)

# These literals are frozen independently of the generator functions below.
FROZEN_RECIPE = b'{"base":10,"count":3,"method":"M1"}\n'
FROZEN_RECIPE_SHA256 = "6e5348760268f67b062d60475eba646123e6126150518aa4f8f860ba97cb8a85"
FROZEN_EXPANDED_SHA256 = "b07ed4a8992468f7e73632cf8b791bffbc25855f994a91abbf65eb3d7789fe35"
EXPECTED_KEYS = ("id", "method_version", "unit", "value")


def generator_v1() -> list[dict[str, object]]:
    return [
        {"id": f"R{index + 1}", "method_version": "M1", "unit": "mg/L", "value": 10 + index}
        for index in range(3)
    ]


def generator_v2_coherent_drift() -> list[dict[str, object]]:
    # Imagine generator + validator were changed together from +index to +2*index.
    return [
        {"id": f"R{index + 1}", "method_version": "M1", "unit": "mg/L", "value": 10 + 2 * index}
        for index in range(3)
    ]


def drifted_expected_value(row_id: str) -> int:
    index = int(row_id.removeprefix("R")) - 1
    return 10 + 2 * index


class ExpandedGoldenTests(unittest.TestCase):
    def verify(self, rows):
        return verify_expanded_golden(
            rows,
            expected_expanded_sha256=FROZEN_EXPANDED_SHA256,
            expected_count=3,
            expected_keys=EXPECTED_KEYS,
            recipe_bytes=FROZEN_RECIPE,
            expected_recipe_sha256=FROZEN_RECIPE_SHA256,
        )

    def test_frozen_rows_match_independent_digest_and_recipe_channels(self):
        rows = generator_v1()
        receipt = self.verify(rows)
        self.assertEqual(FROZEN_EXPANDED_SHA256, receipt["expanded_sha256"])
        self.assertEqual(FROZEN_RECIPE_SHA256, receipt["recipe_sha256"])
        self.assertEqual(3, receipt["expanded_count"])
        self.assertEqual(sorted(EXPECTED_KEYS), receipt["expanded_keys"])

    def test_coherent_generator_and_validator_drift_is_killed_by_frozen_digest(self):
        rows = generator_v2_coherent_drift()

        # A self-consistency test derived from the same changed algorithm passes.
        self.assertTrue(all(row["value"] == drifted_expected_value(row["id"]) for row in rows))

        # The independently frozen expanded truth still detects the coherent drift.
        with self.assertRaisesRegex(ExpandedGoldenError, "expanded golden SHA-256 mismatch"):
            self.verify(rows)

    def test_count_and_schema_drift_fail_before_acceptance(self):
        with self.assertRaisesRegex(ExpandedGoldenError, "row count mismatch"):
            self.verify(generator_v1()[:-1])

        rows = generator_v1()
        rows[0]["rounding"] = 2
        with self.assertRaisesRegex(ExpandedGoldenError, "schema mismatch"):
            self.verify(rows)

    def test_recipe_digest_is_independent_from_expanded_digest(self):
        rows = generator_v1()
        before = deepcopy(rows)
        with self.assertRaisesRegex(ExpandedGoldenError, "recipe SHA-256 mismatch"):
            verify_expanded_golden(
                rows,
                expected_expanded_sha256=FROZEN_EXPANDED_SHA256,
                expected_count=3,
                expected_keys=EXPECTED_KEYS,
                recipe_bytes=b'{"base":999,"count":3,"method":"M1"}\n',
                expected_recipe_sha256=FROZEN_RECIPE_SHA256,
            )
        self.assertEqual(before, rows)

    def test_strict_json_and_digest_literals_fail_closed_without_mutating_rows(self):
        bad_cases = [
            [{"id": "R1", "method_version": "M1", "unit": "mg/L", "value": float("nan")}],
            [{"id": "R1", "method_version": "M1", "unit": "mg/L", "value": (1, 2)}],
            [{"id": "R1", "method_version": "M1", "unit": "mg/L", 7: 1}],
        ]
        for rows in bad_cases:
            with self.subTest(rows=rows):
                before = deepcopy(rows)
                with self.assertRaises(ExpandedGoldenError):
                    canonical_expanded_rows(rows)
                # NaN does not compare equal to itself, so compare representations.
                self.assertEqual(repr(before), repr(rows))

        rows = generator_v1()
        with self.assertRaisesRegex(ExpandedGoldenError, "64-character SHA-256"):
            verify_expanded_golden(
                rows,
                expected_expanded_sha256="not-a-digest",
                expected_count=3,
                expected_keys=EXPECTED_KEYS,
            )


if __name__ == "__main__":
    unittest.main()
