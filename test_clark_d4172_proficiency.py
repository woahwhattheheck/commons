#!/usr/bin/env python3
"""Binary acceptance for clark-d4172-proficiency-lims-01."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

import clark_d4172_proficiency as gate

ROOT = Path(__file__).resolve().parent
PUBLIC_FIXTURE = ROOT / "revenue" / "clark_d4172_proficiency" / "public_fixture.json"
GOLDEN = ROOT / "revenue" / "clark_d4172_proficiency" / "golden.json"


class ClarkD4172ProficiencyTests(unittest.TestCase):
    def test_acceptance_fixture_is_sixty_frozen_sets(self) -> None:
        pack = gate.build_acceptance_fixture()
        self.assertEqual(len(pack["sets"]), 60)
        self.assertEqual(len(pack["sealed"]), 120)
        self.assertEqual(len(pack["fixture_sha256"]), 64)
        kinds = [row["kind"] for row in pack["sets"]]
        self.assertEqual(kinds.count("VALID"), 48)
        self.assertEqual(kinds.count("MISSING_REPLICATE"), 6)
        self.assertEqual(kinds.count("QC_REPEATABILITY"), 3)
        self.assertEqual(kinds.count("QC_REPRODUCIBILITY"), 3)
        again = gate.build_acceptance_fixture()
        self.assertEqual(pack["fixture_sha256"], again["fixture_sha256"])
        self.assertEqual(gate.sha256_hex(pack), gate.sha256_hex(again))

    def test_pass_contract_exact_counts_and_holds(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_sets"], 60)
        self.assertEqual(result["ready"], 48)
        self.assertEqual(result["held"], 12)
        self.assertEqual(result["ready_ids"], gate.VALID_SET_IDS)
        self.assertEqual(
            result["hold_ids"],
            gate.MISSING_SET_IDS + gate.R_BREACH_SET_IDS + gate.R_CAP_BREACH_SET_IDS,
        )
        self.assertEqual(
            result["hold_codes"],
            [
                "HOLD_MISSING_REPLICATE",
                "HOLD_QC_REPEATABILITY",
                "HOLD_QC_REPRODUCIBILITY",
            ],
        )
        self.assertEqual(result["released_coas"], 0)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "SIMULATED")
        self.assertFalse(result["autonomous_certification"])
        self.assertFalse(result["autonomous_release"])

    def test_golden_statistics_and_rounding_are_exact(self) -> None:
        result = gate.run_gate()
        stats = result["golden_stats"]
        first = stats["D4172-PT-01"]
        self.assertEqual(first["state"], "READY_FOR_HUMAN")
        self.assertIsNone(first["hold"])
        self.assertEqual(first["wsd_mm"], "0.41")
        self.assertEqual(first["repeatability_delta_mm"], "0.00")
        self.assertEqual(first["reproducibility_delta_mm"], "0.00")
        self.assertEqual(len(first["provenance_sha256"]), 64)

        missing = stats["D4172-PT-49"]
        self.assertEqual(missing["hold"], "HOLD_MISSING_REPLICATE")
        self.assertIsNone(missing["wsd_mm"])

        r_breach = stats["D4172-PT-55"]
        self.assertEqual(r_breach["hold"], "HOLD_QC_REPEATABILITY")
        self.assertEqual(r_breach["repeatability_delta_mm"], "0.20")

        big_r = stats["D4172-PT-58"]
        self.assertEqual(big_r["hold"], "HOLD_QC_REPRODUCIBILITY")
        self.assertGreater(gate._q(big_r["reproducibility_delta_mm"]), gate.R_REPRODUCIBILITY)

        for set_id, row in stats.items():
            if row["wsd_mm"] is not None:
                self.assertRegex(row["wsd_mm"], r"^\d+\.\d{2}$", msg=set_id)
            if row["repeatability_delta_mm"] is not None:
                self.assertRegex(row["repeatability_delta_mm"], r"^\d+\.\d{2}$", msg=set_id)

    def test_replay_is_identical_and_adds_nothing(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["custody_head"], second["custody_head"])
        self.assertEqual(len(first["manifest_sha256"]), 64)

        pack = gate.build_acceptance_fixture()
        journal = gate.empty_journal()
        journal["sealed"] = deepcopy(pack["sealed"])
        for row in pack["sets"]:
            gate.ingest_set(journal, row)
        replay = gate.replay_into(journal, pack)
        self.assertEqual(replay["added_set_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["replay_noops"], 60)
        self.assertEqual(replay["record_count"], 60)
        self.assertEqual(replay["hold_count"], 12)

    def test_zero_sample_or_participant_swaps_on_frozen_fixture(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["sample_swaps"], 0)
        self.assertEqual(result["participant_swaps"], 0)
        blinds = [(item["participant_blind_id"], item["sample_blind_id"]) for item in result["public_packets"]]
        self.assertEqual(len(blinds), 60)
        self.assertEqual(len(set(blinds)), 60)
        self.assertEqual(len({item[0] for item in blinds}), 60)
        self.assertEqual(len({item[1] for item in blinds}), 60)

    def test_injected_swap_is_a_deterministic_hold(self) -> None:
        pack = gate.build_acceptance_fixture()
        donor = deepcopy(pack["sets"][0])
        victim = deepcopy(pack["sets"][1])
        victim["sample_blind_id"] = donor["sample_blind_id"]
        victim["set_id"] = "D4172-PT-SWAP"
        journal = gate.empty_journal()
        journal["sealed"] = deepcopy(pack["sealed"])
        gate.ingest_set(journal, donor)
        effect = gate.ingest_set(journal, victim)
        self.assertEqual(effect["kind"], "HOLD")
        self.assertIn(effect["code"], {"HOLD_SAMPLE_SWAP", "HOLD_PARTICIPANT_SWAP"})
        self.assertTrue(str(journal["records"]["D4172-PT-SWAP"]["state"]).startswith("HOLD"))

    def test_pre_release_views_do_not_leak_identities(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["identity_leaks"], [])
        pack = gate.build_acceptance_fixture()
        extra = tuple(sorted(pack["sealed"].values()))
        for view in (result["public_packets"], result["coa_drafts"], result["cycle_digest"]):
            leaks = gate.leak_tokens_in(view, extra)
            self.assertEqual(leaks, [], msg=str(view)[:200])
            blob = gate._canonical(view)
            self.assertNotIn("Clark Testing", blob)
            self.assertNotIn("Heffernan", blob)
            self.assertNotIn("LAB-SYN-", blob)
            self.assertNotIn("OIL-SYN-", blob)

    def test_missing_replicate_and_qc_holds_are_deterministic(self) -> None:
        result = gate.run_gate()
        stats = result["golden_stats"]
        for set_id in gate.MISSING_SET_IDS:
            self.assertEqual(stats[set_id]["state"], "HOLD_MISSING_REPLICATE")
        for set_id in gate.R_BREACH_SET_IDS:
            self.assertEqual(stats[set_id]["state"], "HOLD_QC_REPEATABILITY")
        for set_id in gate.R_CAP_BREACH_SET_IDS:
            self.assertEqual(stats[set_id]["state"], "HOLD_QC_REPRODUCIBILITY")

        denied = gate.dispose
        pack = gate.build_acceptance_fixture()
        journal = gate.empty_journal()
        journal["sealed"] = deepcopy(pack["sealed"])
        for row in pack["sets"]:
            gate.ingest_set(journal, row)
        hold_id = gate.MISSING_SET_IDS[0]
        autonomous = denied(journal, hold_id, actor_role="SYSTEM", actor="bot")
        self.assertFalse(autonomous["ok"])
        self.assertEqual(autonomous["code"], "AUTONOMOUS_RELEASE_DENIED")
        blocked = denied(journal, hold_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "HOLD_BLOCKS_RELEASE")
        voided = denied(
            journal, hold_id, actor_role="RELEASER", actor="reviewer-1", action="VOID"
        )
        self.assertTrue(voided["ok"])
        self.assertEqual(voided["disposition"], "VOID")

    def test_chain_of_custody_and_provenance_are_immutable(self) -> None:
        pack = gate.build_acceptance_fixture()
        journal = gate.empty_journal()
        journal["sealed"] = deepcopy(pack["sealed"])
        for row in pack["sets"]:
            gate.ingest_set(journal, row)
        events = journal["events"]
        self.assertGreaterEqual(len(events), 180)
        self.assertEqual(events[0]["prev_sha256"], "GENESIS")
        for index, event in enumerate(events[1:], start=1):
            self.assertEqual(event["prev_sha256"], events[index - 1]["event_sha256"])
            rebuilt = {
                "seq": event["seq"],
                "kind": event["kind"],
                "payload": event["payload"],
                "prev_sha256": event["prev_sha256"],
            }
            self.assertEqual(event["event_sha256"], gate.sha256_hex(rebuilt))
        first = journal["records"]["D4172-PT-01"]
        self.assertEqual(first["provenance"]["formula_id"], gate.FORMULA_ID)
        self.assertEqual(first["provenance"]["rounding"], "0.01/ROUND_HALF_EVEN")
        self.assertEqual(len(first["provenance"]["inputs_sha256"]), 64)
        self.assertEqual(len(first["custody"]), 1)

    def test_human_only_disposition_and_coa_unseal(self) -> None:
        pack = gate.build_acceptance_fixture()
        journal = gate.empty_journal()
        journal["sealed"] = deepcopy(pack["sealed"])
        first_row = pack["sets"][0]
        gate.ingest_set(journal, first_row)
        set_id = first_row["set_id"]
        record = journal["records"][set_id]
        self.assertEqual(record["state"], "READY_FOR_HUMAN")
        self.assertEqual(gate.draft_coa(record)["released"], False)
        self.assertIsNone(gate.draft_coa(record).get("customer_sample_id"))

        bot = gate.dispose(journal, set_id, actor_role="SYSTEM", actor="bot")
        self.assertFalse(bot["ok"])
        self.assertEqual(bot["code"], "AUTONOMOUS_RELEASE_DENIED")
        self.assertFalse(record["released"])

        human = gate.dispose(journal, set_id, actor_role="RELEASER", actor="reviewer-1")
        self.assertTrue(human["ok"])
        self.assertEqual(record["state"], "RELEASED")
        self.assertEqual(record["released_by"], "reviewer-1")
        self.assertEqual(record["coa"]["customer_sample_id"], pack["sealed"][first_row["sample_blind_id"]])
        self.assertTrue(record["coa"]["customer_sample_id"].startswith("OIL-SYN-"))

        views = gate.pre_release_views(journal)
        leaks = gate.leak_tokens_in(views, tuple(pack["sealed"].values()))
        self.assertEqual(leaks, [])

    def test_public_fixture_matches_generator_and_stays_unsealed(self) -> None:
        pack = gate.build_acceptance_fixture()
        public = json.loads(PUBLIC_FIXTURE.read_text(encoding="utf-8"))
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertNotIn("sealed", public)
        self.assertEqual(public["fixture_sha256"], pack["fixture_sha256"])
        self.assertEqual(public["sets"], pack["sets"])
        self.assertEqual(golden["manifest_sha256"], gate.run_gate()["manifest_sha256"])
        self.assertEqual(gate.leak_tokens_in(public, tuple(pack["sealed"].values())), [])

    def test_method_version_mismatch_holds(self) -> None:
        pack = gate.build_acceptance_fixture()
        row = deepcopy(pack["sets"][2])
        row["set_id"] = "D4172-PT-MV"
        row["sample_blind_id"] = "S-method-version"
        row["participant_blind_id"] = "P-method-version"
        row["method_version"] = "D4172-94"
        journal = gate.empty_journal()
        effect = gate.ingest_set(journal, row)
        self.assertEqual(effect["code"], "HOLD_METHOD_VERSION")
        self.assertEqual(journal["records"]["D4172-PT-MV"]["state"], "HOLD_METHOD_VERSION")


if __name__ == "__main__":
    unittest.main()
