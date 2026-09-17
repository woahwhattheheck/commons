import copy
import unittest

from research.open_pr_cash_claim_recovery_20260916.validate import (
    ValidationError,
    load,
    validate,
)


class Tests(unittest.TestCase):
    def setUp(self):
        self.doc = load()

    def bad(self, mutate):
        doc = copy.deepcopy(self.doc)
        mutate(doc)
        with self.assertRaises(ValidationError):
            validate(doc)

    def test_snapshot_valid(self):
        self.assertEqual(
            validate(self.doc)["paid_by_denomination"],
            {"USD": "1.00", "RTC": "25"},
        )

    def test_merge_cannot_become_paid(self):
        self.bad(
            lambda d: d["rows"][3].update(
                settlement_state="PAID",
                proof_level="MERGED_PLUS_ADVERTISED_ONLY",
            )
        )

    def test_nonpaid_cannot_gain_award(self):
        self.bad(
            lambda d: d["rows"][3].update(
                awarded={"amount": "90", "denomination": "USD", "truth": "SPONSOR_AWARD"}
            )
        )

    def test_omi_quote_cannot_become_advertised(self):
        self.bad(
            lambda d: d["rows"][4].update(
                advertised={"amount": "100", "denomination": "USD", "truth": "ADVERTISED"}
            )
        )

    def test_private_evidence_digest_required_for_paid(self):
        self.bad(lambda d: d["rows"][0].update(private_evidence=None))

    def test_paid_requires_sponsor_proof(self):
        self.bad(lambda d: d["rows"][1].update(proof_level="MERGED_ONLY"))

    def test_rtc_cannot_gain_usd_equivalent(self):
        self.bad(lambda d: d["rows"][1]["paid"].update(usd_equivalent="2.50"))

    def test_outbound_not_authorized(self):
        self.bad(lambda d: d["rows"][2].update(new_outbound_authorized=True))

    def test_global_outbound_not_authorized(self):
        self.bad(lambda d: d["authority"].update(new_outbound_authorized=True))

    def test_cross_denomination_conversion_not_authorized(self):
        self.bad(
            lambda d: d["authority"].update(
                cross_denomination_conversion_authorized=True
            )
        )

    def test_revenue_recognition_not_computed(self):
        self.bad(
            lambda d: d["authority"].update(
                cash_or_revenue_recognition_computed=True
            )
        )

    def test_paid_totals_fail_on_drift(self):
        self.bad(lambda d: d["rows"][0]["paid"].update(amount="2.00"))

    def test_summary_drift(self):
        self.bad(lambda d: d["summary"].update(paid_rows=3))

    def test_ready_for_muse_not_in_snapshot(self):
        self.bad(lambda d: d["rows"][3].update(next_action="READY_FOR_MUSE"))

    def test_duplicate_id(self):
        self.bad(lambda d: d["rows"][1].update(id=d["rows"][0]["id"]))

    def test_amount_must_be_string(self):
        self.bad(lambda d: d["rows"][0]["paid"].update(amount=1.0))

    def test_nonfinite_amount_rejected(self):
        self.bad(lambda d: d["rows"][0]["paid"].update(amount="NaN"))


if __name__ == "__main__":
    unittest.main()
