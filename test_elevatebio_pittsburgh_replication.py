#!/usr/bin/env python3
"""Binary acceptance for elevatebio-pittsburgh-replication-lims-01."""

from __future__ import annotations

import unittest

import elevatebio_pittsburgh_replication as gate


class ElevatebioPittsburghReplicationTests(unittest.TestCase):
    def test_acceptance_fixture_is_400_two_site(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 400)
        by_site = {name: 0 for name in gate.SITES}
        exceptions = {"METHOD_VERSION": 0, "PERMISSION": 0}
        for row in rows:
            by_site[row["site"]] += 1
            if row["exception_type"]:
                exceptions[row["exception_type"]] += 1
        self.assertEqual(by_site, {"WALTHAM": 200, "PITTSBURGH": 200})
        self.assertEqual(exceptions, {"METHOD_VERSION": 8, "PERMISSION": 8})

    def test_pass_contract_exact_state_counts(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        counts = gate.expected_actual(result)
        self.assertEqual(
            counts["expected"],
            {
                "input_rows": 400,
                "valid_completed": 384,
                "hold": 16,
                "waltham": 200,
                "pittsburgh": 200,
                "human_disposed_batches": 16,
                "autonomous_disposed": 0,
                "identical_pairs": 192,
                "interfaces": 5,
            },
        )
        self.assertEqual(counts["actual"], counts["expected"])
        self.assertTrue(counts["match"])
        self.assertEqual(result["hold_codes"], list(gate.EXPECTED_HOLD_CODES))
        self.assertEqual(
            result["hold_code_counts"],
            {"HOLD_METHOD_VERSION": 8, "HOLD_PERMISSION": 8},
        )

    def test_approved_methods_match_across_sites(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["pair_count"], 192)
        self.assertEqual(result["identical_pairs"], 192)
        self.assertTrue(result["pairs_all_identical"])
        self.assertTrue(all(item["identical"] for item in result["pairs"]))
        self.assertEqual(result["calc_sha256"], gate.GOLDEN_CALC_SHA256)
        wal = next(item for item in result["accessions"] if item["sample_id"] == "SYN-WAL-QC-001")
        pit = next(item for item in result["accessions"] if item["sample_id"] == "SYN-PIT-QC-001")
        self.assertEqual(wal["method"], pit["method"])
        self.assertEqual(wal["method_version"], pit["method_version"])
        self.assertEqual(wal["raw_value"], pit["raw_value"])
        self.assertEqual(wal["value"], pit["value"])
        self.assertEqual(wal["route"], pit["route"])
        self.assertNotEqual(wal["namespace"], pit["namespace"])

    def test_pittsburgh_identifiers_stay_isolated(self) -> None:
        result = gate.run_gate()
        self.assertTrue(result["pittsburgh_ids_isolated"])
        self.assertTrue(result["waltham_ids_isolated"])
        pit = [item for item in result["accessions"] if item["site"] == "PITTSBURGH"]
        wal = [item for item in result["accessions"] if item["site"] == "WALTHAM"]
        self.assertEqual(len(pit), 192)
        self.assertEqual(len(wal), 192)
        self.assertTrue(all(item["sample_id"].startswith("SYN-PIT-") for item in pit))
        self.assertTrue(all(item["namespace"] == "eb.pittsburgh.lims" for item in pit))
        self.assertTrue(all(item["tenant"] == "eb-pit-tenant-01" for item in pit))
        self.assertTrue(all(item["sample_id"].startswith("SYN-WAL-") for item in wal))
        self.assertTrue(all("WAL" not in item["sample_id"] for item in pit))
        self.assertTrue(all("PIT" not in item["sample_id"] for item in wal))

    def test_cross_site_access_denied_by_role_matrix(self) -> None:
        result = gate.run_gate()
        self.assertTrue(
            all(item["code"] == "CROSS_SITE_DENIED" for item in result["cross_site_denials"])
        )
        self.assertTrue(
            all(item["code"] == "CROSS_SITE_DENIED" for item in result["governor_sample_denials"])
        )
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        denied = gate.lookup_sample(journal, "SYN-PIT-QC-001", "WAL_QA")
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "CROSS_SITE_DENIED")
        allowed = gate.lookup_sample(journal, "SYN-PIT-QC-001", "PIT_QC")
        self.assertTrue(allowed["ok"])
        self.assertEqual(allowed["record"]["namespace"], "eb.pittsburgh.lims")
        self.assertFalse(gate.role_may("WAL_QC", "PITTSBURGH", "QC", "ACCESS"))
        self.assertFalse(gate.role_may("PIT_QA", "WALTHAM", "QC", "DISPOSE"))
        self.assertTrue(gate.role_may("PIT_QA", "PITTSBURGH", "QC", "DISPOSE"))
        self.assertEqual(gate.access_permission("TWO_SITE_GOV", "PITTSBURGH", "MSAT"), "GOVERN")

    def test_seeded_method_version_and_permission_holds(self) -> None:
        result = gate.run_gate()
        self.assertEqual(len(result["holds"]), 16)
        method_holds = [item for item in result["holds"] if item["code"] == "HOLD_METHOD_VERSION"]
        perm_holds = [item for item in result["holds"] if item["code"] == "HOLD_PERMISSION"]
        self.assertEqual(len(method_holds), 8)
        self.assertEqual(len(perm_holds), 8)
        self.assertEqual(sum(1 for item in method_holds if item["site"] == "WALTHAM"), 4)
        self.assertEqual(sum(1 for item in method_holds if item["site"] == "PITTSBURGH"), 4)
        self.assertEqual(sum(1 for item in perm_holds if item["site"] == "WALTHAM"), 4)
        self.assertEqual(sum(1 for item in perm_holds if item["site"] == "PITTSBURGH"), 4)
        wal_method = next(item for item in method_holds if item["row_id"] == "WAL-QC-145")
        self.assertGreater(wal_method["method_version"], gate.APPROVED_METHODS[wal_method["method"]]["version"])
        wal_perm = next(item for item in perm_holds if item["row_id"] == "WAL-QC-149")
        self.assertEqual(wal_perm["accessor_role"], "PIT_QC")
        self.assertTrue(all(item["state"] == "HOLD" for item in result["holds"]))

    def test_named_human_batch_disposition_required(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["human_disposed_batches"], 16)
        self.assertEqual(result["autonomous_disposed"], 0)
        self.assertTrue(
            all(
                item["code"] == "AUTONOMOUS_DISPOSITION_DENIED"
                for item in result["autonomous_disposition_effects"]
            )
        )
        self.assertTrue(all(item.get("ok") for item in result["human_disposition_effects"]))
        signs = [item for item in result["signatures"] if item["kind"] == "BATCH_DISPOSITION"]
        self.assertEqual(len(signs), 16)
        self.assertTrue(all(item["named_human"] for item in signs))
        self.assertEqual(
            {item["disposed_by"] for item in result["batches"]},
            {gate.HUMAN_WAL, gate.HUMAN_PIT},
        )
        journal = gate.empty_journal()
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        gate.assign_batches(journal)
        bid = next(iter(journal["tenants"]["PITTSBURGH"]["batches"]))
        bot = gate.dispose_batch(journal, bid, actor_role="SYSTEM", actor="bot")
        self.assertFalse(bot["ok"])
        self.assertEqual(bot["code"], "AUTONOMOUS_DISPOSITION_DENIED")
        cross = gate.dispose_batch(journal, bid, actor_role="WAL_QA", actor=gate.HUMAN_WAL)
        self.assertFalse(cross["ok"])
        self.assertEqual(cross["code"], "HOLD_PERMISSION")
        human = gate.dispose_batch(journal, bid, actor_role="PIT_QA", actor=gate.HUMAN_PIT)
        self.assertTrue(human["ok"])

    def test_replay_changes_zero_records_and_hashes_match(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        self.assertEqual(first["audit_sha256"], gate.GOLDEN_AUDIT_SHA256)
        self.assertEqual(first["calc_sha256"], gate.GOLDEN_CALC_SHA256)
        self.assertEqual(first["interface_hash_bundle"], gate.GOLDEN_INTERFACE_SHA256)
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(gate.sha256_hex(first["audit"]), first["audit_sha256"])

        journal = gate.empty_journal()
        gate.bind_signed_fixtures(journal)
        for row in gate.build_acceptance_fixture():
            gate.ingest_row(journal, row)
        self.assertEqual(sum(len(journal["tenants"][site]["accessions"]) for site in gate.SITES), 384)
        self.assertEqual(len(journal["holds"]), 16)
        replay = gate.replay_into(journal)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["accession_count"], 384)
        self.assertEqual(replay["hold_count"], 16)
        self.assertEqual(replay["replay_noops"], 384)

    def test_mock_interfaces_match_canonical_hash_and_stay_read_only(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["interfaces"], "SIMULATED_READ_ONLY")
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["production_tenant_change"], 0)
        self.assertFalse(result["validation_claimed"])
        self.assertFalse(result["buyer_approved_golden_round_trip"])
        self.assertEqual(set(result["interface_hashes"]), set(gate.INTERFACES))
        for name in gate.INTERFACES:
            self.assertEqual(result["interface_hashes"][name], gate.INTERFACE_CONTRACTS[name]["sha256"])
            self.assertEqual(len(result["interface_hashes"][name]), 64)
        self.assertTrue(all(item["code"] == "ADAPTER_WRITE_DENIED" for item in result["write_denials"]))
        self.assertEqual(len(result["write_denials"]), 5)
        adapters = gate.bind_adapters()
        journal = gate.empty_journal()
        denials = gate.attempt_adapter_writes(adapters, journal)
        self.assertEqual(len(denials), 5)
        self.assertTrue(all(item["live"] is False for item in denials))
        self.assertFalse(adapters["MES"].live)
        self.assertFalse(adapters["QMS"].live)

    def test_signed_fixtures_and_two_site_governance(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["fixtures"]["WALTHAM"]["signed_by"], gate.FIXTURE_SIGNERS["WALTHAM"])
        self.assertEqual(result["fixtures"]["PITTSBURGH"]["signed_by"], gate.FIXTURE_SIGNERS["PITTSBURGH"])
        self.assertEqual(len(result["fixtures"]["WALTHAM"]["sha256"]), 64)
        self.assertNotEqual(result["fixtures"]["WALTHAM"]["sha256"], result["fixtures"]["PITTSBURGH"]["sha256"])
        fixture_signs = [item for item in result["signatures"] if item["kind"] == "FIXTURE"]
        self.assertEqual(len(fixture_signs), 2)
        self.assertEqual(result["namespaces"]["PITTSBURGH"], "eb.pittsburgh.lims")
        self.assertEqual(result["tenants"]["PITTSBURGH"], "eb-pit-tenant-01")
        self.assertEqual(len(result["role_matrix"]), 12)


if __name__ == "__main__":
    unittest.main()
