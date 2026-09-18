import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from opportunities.irs_5000233302 import preflight as pf

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 18, 1, 30, tzinfo=timezone.utc)


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class ReadyTests(unittest.TestCase):
    def test_default_packet_is_partner_ready_but_never_send_authority(self):
        r = pf.evaluate(
            load("source_snapshot.json"),
            load("owner_inputs.template.json"),
            load("partner_shortlist.json"),
            now=NOW,
        )
        self.assertEqual(r["state"], pf.PARTNER_PACKET_READY)
        self.assertEqual(r["direct_irs_state"], pf.DIRECT_IRS_HOLD)
        self.assertTrue(all(v is False for v in r["authority"].values()))
        self.assertIn(
            "MUSE_AND_FRESH_RELATIONSHIP_CENSUS_REQUIRED_BEFORE_ANY_CONTACT",
            r["warnings"],
        )

    def test_owner_placeholders_do_not_become_direct_irs_authority(self):
        r = pf.evaluate(
            load("source_snapshot.json"),
            load("owner_inputs.template.json"),
            load("partner_shortlist.json"),
            now=NOW,
        )
        self.assertIn("OWNER_FACT_UNVERIFIED:uei", r["warnings"])
        self.assertFalse(r["authority"]["irs_contact_authorized"])
        self.assertFalse(r["authority"]["prime_representation_authorized"])


class SourceTruthTests(unittest.TestCase):
    def test_rfp_upgrade_rejected(self):
        s = load("source_snapshot.json")
        s["notice_type"] = "RFP"
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(
                s,
                load("owner_inputs.template.json"),
                load("partner_shortlist.json"),
                now=NOW,
            )

    def test_proposal_upgrade_rejected(self):
        s = load("source_snapshot.json")
        s["response_is_proposal"] = True
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(
                s,
                load("owner_inputs.template.json"),
                load("partner_shortlist.json"),
                now=NOW,
            )

    def test_award_commitment_upgrade_rejected(self):
        s = load("source_snapshot.json")
        s["government_commitment_to_award"] = True
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(
                s,
                load("owner_inputs.template.json"),
                load("partner_shortlist.json"),
                now=NOW,
            )

    def test_authority_bit_cannot_be_flipped_in_source(self):
        s = load("source_snapshot.json")
        s["authority"]["contact_partner_authorized"] = True
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(
                s,
                load("owner_inputs.template.json"),
                load("partner_shortlist.json"),
                now=NOW,
            )

    def test_missing_market_research_question_rejected(self):
        s = load("source_snapshot.json")
        s["questions"].pop()
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(
                s,
                load("owner_inputs.template.json"),
                load("partner_shortlist.json"),
                now=NOW,
            )

    def test_task_area_drift_rejected(self):
        s = load("source_snapshot.json")
        s["task_areas"][7] = "MAGIC"
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(
                s,
                load("owner_inputs.template.json"),
                load("partner_shortlist.json"),
                now=NOW,
            )

    def test_stale_snapshot_holds(self):
        s = load("source_snapshot.json")
        s["checked_at"] = "2026-09-10T01:00:00Z"
        r = pf.evaluate(
            s,
            load("owner_inputs.template.json"),
            load("partner_shortlist.json"),
            now=NOW,
        )
        self.assertEqual(r["state"], pf.HOLD)
        self.assertIn("SOURCE_SNAPSHOT_STALE", r["blockers"])

    def test_deadline_passed_holds(self):
        r = pf.evaluate(
            load("source_snapshot.json"),
            load("owner_inputs.template.json"),
            load("partner_shortlist.json"),
            now=datetime(2026, 9, 25, 18, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(r["state"], pf.HOLD)
        self.assertIn("SOURCES_SOUGHT_DEADLINE_PASSED", r["blockers"])


class CommercialTruthTests(unittest.TestCase):
    def test_workshare_cannot_be_self_accepted(self):
        o = load("owner_inputs.template.json")
        o["commercial"]["offer_state"] = "ACCEPTED"
        r = pf.evaluate(
            load("source_snapshot.json"),
            o,
            load("partner_shortlist.json"),
            now=NOW,
        )
        self.assertEqual(r["state"], pf.HOLD)
        self.assertIn(
            "WORKSHARE_MUST_REMAIN_PROPOSED_NOT_ACCEPTED", r["blockers"]
        )

    def test_bad_price_rejected(self):
        o = load("owner_inputs.template.json")
        o["commercial"]["partner_workshare_price_usd"] = 0
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(
                load("source_snapshot.json"),
                o,
                load("partner_shortlist.json"),
                now=NOW,
            )


class PartnerTruthTests(unittest.TestCase):
    def test_partner_participation_cannot_be_self_asserted(self):
        p = load("partner_shortlist.json")
        p["partners"][0]["participation_in_5000233302"] = "PURSUING"
        r = pf.evaluate(
            load("source_snapshot.json"),
            load("owner_inputs.template.json"),
            p,
            now=NOW,
        )
        self.assertEqual(r["state"], pf.HOLD)
        self.assertIn(
            "PUBLIC_RESEARCH_MUST_NOT_SELF_ASSERT_PARTNER_PARTICIPATION",
            r["blockers"],
        )

    def test_route_cannot_self_authorize(self):
        p = load("partner_shortlist.json")
        p["partners"][0]["route"]["state"] = "AUTHORIZED"
        r = pf.evaluate(
            load("source_snapshot.json"),
            load("owner_inputs.template.json"),
            p,
            now=NOW,
        )
        self.assertEqual(r["state"], pf.HOLD)
        self.assertIn("PARTNER_ROUTE_MUST_NOT_SELF_AUTHORIZE", r["blockers"])

    def test_primary_route_must_be_maximus_first_party(self):
        p = load("partner_shortlist.json")
        p["partners"][0]["route"]["url"] = "https://example.com/form"
        with self.assertRaises(pf.PreflightError):
            pf.evaluate(
                load("source_snapshot.json"),
                load("owner_inputs.template.json"),
                p,
                now=NOW,
            )

    def test_all_shortlist_participation_stays_unknown(self):
        p = load("partner_shortlist.json")
        p["partners"][1]["participation_in_5000233302"] = "PURSUING"
        r = pf.evaluate(
            load("source_snapshot.json"),
            load("owner_inputs.template.json"),
            p,
            now=NOW,
        )
        self.assertEqual(r["state"], pf.HOLD)
        self.assertTrue(
            any(
                x.startswith("PARTNER_PARTICIPATION_MUST_BE_UNKNOWN:")
                for x in r["blockers"]
            )
        )


class ParserTests(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(pf.PreflightError):
                pf.load(path)

    def test_nonfinite_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json"
            path.write_text('{"x":NaN}', encoding="utf-8")
            with self.assertRaises(pf.PreflightError):
                pf.load(path)


if __name__ == "__main__":
    unittest.main()
