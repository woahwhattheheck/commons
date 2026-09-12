from __future__ import annotations

import unittest

import sticky_obligation as S


def carry(*, quantity: int = 1, item: str = "WHEAT"):
    return S.issue_carry_consumption(
        actor="hand-0",
        item=item,
        quantity=quantity,
        created_step=10,
        due_end=23,
        capacity_pressure_units=quantity,
    )


def row(step: int, actor: str, op: str, **extra):
    return {"step": step, "actor": actor, "op": op, **extra}


class CarryCallbackCustodyTests(unittest.TestCase):
    def test_duplicate_feed_rows_cannot_mint_two_sink_units(self):
        with self.assertRaisesRegex(
            S.UnsupportedObligation,
            "duplicate obligated actor row in callback",
        ):
            S.prove_carry_consumption(
                carry(quantity=2),
                [
                    row(11, "hand-0", "FEED", effectful=True),
                    row(11, "hand-0", "FEED", effectful=True),
                ],
                current_inventory_units=0,
            )

    def test_early_feed_cannot_hide_same_callback_duplicate_drop(self):
        with self.assertRaisesRegex(
            S.UnsupportedObligation,
            "duplicate obligated actor row in callback",
        ):
            S.prove_carry_consumption(
                carry(),
                [
                    row(11, "hand-0", "FEED", effectful=True),
                    row(11, "hand-0", "DROP"),
                ],
                current_inventory_units=0,
            )

    def test_same_callback_other_actor_does_not_collide(self):
        got = S.prove_carry_consumption(
            carry(),
            [
                row(11, "hand-0", "FEED", effectful=True),
                row(11, "hand-1", "DROP"),
            ],
            current_inventory_units=0,
        )
        self.assertTrue(got["proven"])
        self.assertEqual(11, got["sink_step"])

    def test_same_actor_across_different_callbacks_remains_legal_when_effect_is_proved(self):
        got = S.prove_carry_consumption(
            carry(quantity=2),
            [
                row(11, "hand-0", "FEED", effectful=True, site=[2, 3]),
                row(12, "hand-0", "FEED", effectful=True, site=[2, 4]),
            ],
            current_inventory_units=0,
        )
        self.assertTrue(got["proven"])
        self.assertEqual(12, got["sink_step"])
        self.assertEqual(2, got["sink_units"])
        self.assertEqual(0, got["unproved_sink_rows"])

    def test_bare_sink_opcode_is_not_consumption_evidence(self):
        for item, op in (("WHEAT", "FEED"), ("FERTILIZER", "FERTILIZE")):
            with self.subTest(item=item, op=op):
                got = S.prove_carry_consumption(
                    carry(item=item),
                    [row(11, "hand-0", op)],
                    current_inventory_units=0,
                )
                self.assertFalse(got["proven"])
                self.assertEqual(0, got["sink_units"])
                self.assertEqual(1, got["unproved_sink_rows"])
                self.assertTrue(got["sink_effect_evidence_required"])

    def test_same_animal_later_feed_noop_counts_only_first_effect(self):
        got = S.prove_carry_consumption(
            carry(quantity=2),
            [
                row(11, "hand-0", "FEED", effectful=True, site=[5, 5]),
                row(12, "hand-0", "FEED", effectful=False, site=[5, 5]),
            ],
            current_inventory_units=0,
        )
        self.assertFalse(got["proven"])
        self.assertEqual(1, got["sink_units"])
        self.assertEqual(1, got["unproved_sink_rows"])

    def test_truthy_non_bool_sink_effect_proof_is_rejected(self):
        for poison in (1, "yes", [], {}):
            with self.subTest(poison=poison), self.assertRaisesRegex(
                S.UnsupportedObligation,
                "projected sink effectful must be a bool",
            ):
                S.prove_carry_consumption(
                    carry(),
                    [row(11, "hand-0", "FEED", effectful=poison)],
                    current_inventory_units=0,
                )


if __name__ == "__main__":
    unittest.main()
