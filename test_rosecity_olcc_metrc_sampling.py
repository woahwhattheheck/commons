#!/usr/bin/env python3
"""Binary acceptance for rosecity-olcc-metrc-sampling-lims-01."""

from __future__ import annotations

import unittest
from copy import deepcopy

import rosecity_olcc_metrc_sampling as gate


class RoseCityOlccMetrcSamplingTests(unittest.TestCase):
    def test_acceptance_fixture_split(self) -> None:
        rows = gate.build_acceptance_fixture()
        self.assertEqual(len(rows), 100)
        defects = [row.get("defect") for row in rows]
        self.assertEqual(defects.count(None), 75)
        self.assertEqual(defects.count("MISSING_METRC_TRANSFER"), 8)
        self.assertEqual(defects.count("BATCH_COUNT_MISMATCH"), 7)
        self.assertEqual(defects.count("DUPLICATE_PACKAGE_ID"), 5)
        self.assertEqual(defects.count("UNCONFIRMED_APPOINTMENT"), 5)

    def test_pass_contract_exact_75_ready_25_hold(self) -> None:
        result = gate.run_gate()
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_rows"], 100)
        self.assertEqual(result["dispatch_ready"], 75)
        self.assertEqual(result["hold"], 25)
        self.assertEqual(result["dispatch_count"], 75)
        self.assertEqual(result["hold_dispatch_count"], 0)
        self.assertEqual(
            result["hold_code_counts"],
            {
                "MISSING_METRC_TRANSFER": 8,
                "BATCH_COUNT_MISMATCH": 7,
                "DUPLICATE_PACKAGE_ID": 5,
                "UNCONFIRMED_APPOINTMENT": 5,
            },
        )
        self.assertEqual(result["emails_sent"], 0)
        self.assertEqual(result["coa_released"], 0)
        self.assertFalse(result["metrc_write"])
        self.assertFalse(result["automatic_release"])
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["interfaces"], "READ_ONLY_SYNTHETIC")

    def test_holds_produce_zero_dispatches(self) -> None:
        result = gate.run_gate()
        hold_ids = set(result["hold_request_ids"])
        self.assertEqual(len(hold_ids), 25)
        for item in result["dispatches"]:
            self.assertNotIn(item["request_id"], hold_ids)
            self.assertEqual(item["status"], "DISPATCH_READY")
        for item in result["holds"]:
            self.assertIsNone(item["dispatch_id"])
            self.assertIsNone(item["custody_id"])
            self.assertIsNone(item["accession_id"])
            self.assertFalse(item["email_sent"])
            self.assertFalse(item["coa_released"])

    def test_valid_pickup_has_one_immutable_custody_and_accession(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["custody_count"], 75)
        self.assertEqual(result["accession_count"], 75)
        self.assertEqual(len(set(result["custody_ids"])), 75)
        self.assertEqual(len(set(result["accession_ids"])), 75)
        self.assertTrue(result["custody_immutable"])

        by_request_custody = {}
        for chain in result["custody_chains"]:
            by_request_custody.setdefault(chain["request_id"], []).append(chain)
        by_request_acc = {}
        for acc in result["accessions"]:
            by_request_acc.setdefault(acc["request_id"], []).append(acc)

        for item in result["dispatches"]:
            request_id = item["request_id"]
            chains = by_request_custody[request_id]
            accs = by_request_acc[request_id]
            self.assertEqual(len(chains), 1)
            self.assertEqual(len(accs), 1)
            chain = chains[0]
            self.assertTrue(chain["immutable"])
            self.assertTrue(chain["sealed"])
            self.assertEqual(chain["accession_id"], accs[0]["accession_id"])
            self.assertEqual(chain["accession_id"], item["accession_id"])
            self.assertEqual(chain["custody_id"], item["custody_id"])
            kinds = [link["kind"] for link in chain["links"]]
            self.assertEqual(
                kinds,
                ["WEB_REQUEST", "APPOINTMENT", "METRC_TRANSFER", "FIELD_PICKUP", "ACCESSION"],
            )
            denied = gate.mutate_custody(chain, kind="TAMPER")
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["code"], "IMMUTABLE_CUSTODY")
            self.assertFalse(denied["applied"])

    def test_replay_is_idempotent(self) -> None:
        first = gate.run_gate()
        second = gate.run_gate()
        self.assertEqual(gate.sha256_hex(first), gate.sha256_hex(second))
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(first["manifest_sha256"]), 64)

        rows = gate.build_acceptance_fixture()
        metrc, email = gate.adapters_from_rows(rows)
        journal = gate.empty_journal()
        gate.ingest_fixture(journal, rows, metrc_adapter=metrc, email_adapter=email)
        self.assertEqual(len(journal["dispatches"]), 75)
        self.assertEqual(len(journal["holds"]), 25)
        replay = gate.replay_into(journal, rows, metrc_adapter=metrc, email_adapter=email)
        self.assertEqual(replay["added_dispatch_count"], 0)
        self.assertEqual(replay["added_accession_count"], 0)
        self.assertEqual(replay["added_custody_count"], 0)
        self.assertEqual(replay["added_holds"], 0)
        self.assertEqual(replay["replay_noops"], 100)
        self.assertEqual(replay["dispatch_count"], 75)
        self.assertEqual(replay["hold_count"], 25)

    def test_email_destination_linked_but_never_sent(self) -> None:
        result = gate.run_gate()
        self.assertEqual(result["email_linked"], 75)
        self.assertEqual(result["emails_sent"], 0)
        self.assertEqual(result["email_adapter_sent"], 0)
        self.assertEqual(result["email_send_denied"], 75)
        for item in result["dispatches"]:
            self.assertTrue(item["email_linked"])
            self.assertTrue(str(item["email_destination"]).endswith("@rosecity.example.test"))
            self.assertFalse(item["email_sent"])
            self.assertFalse(item["coa_released"])
            self.assertFalse(item["auto_release"])
        self.assertTrue(all(item["code"] == "EMAIL_SEND_DENIED" for item in result["email_denials"]))
        self.assertTrue(all(item["code"] == "AUTO_RELEASE_DENIED" for item in result["release_denials"]))

    def test_readonly_adapters_deny_metrc_write_and_email_send(self) -> None:
        rows = gate.build_acceptance_fixture()
        metrc, email = gate.adapters_from_rows(rows)
        found = metrc.get_transfer("RCL-001")
        self.assertIsNotNone(found)
        self.assertEqual(found["transfer_id"], "TR-001")
        self.assertIsNone(metrc.get_transfer("RCL-076"))
        denied_write = metrc.write_transfer("RCL-001", {"transfer_id": "FORGED"})
        self.assertFalse(denied_write["ok"])
        self.assertEqual(denied_write["code"], "METRC_WRITE_DENIED")
        self.assertFalse(denied_write["applied"])
        self.assertEqual(metrc.write_attempts, 1)
        after = metrc.get_transfer("RCL-001")
        self.assertEqual(after["transfer_id"], "TR-001")

        dest = email.destination_for("RCL-001")
        self.assertEqual(dest, "results+001@rosecity.example.test")
        denied_send = email.send("RCL-001", dest, body="CoA")
        self.assertFalse(denied_send["ok"])
        self.assertEqual(denied_send["code"], "EMAIL_SEND_DENIED")
        self.assertFalse(denied_send["sent"])
        self.assertEqual(email.send_attempts, 1)
        self.assertEqual(email.sent, [])

        result = gate.run_gate()
        self.assertTrue(result["metrc_write_denied"])
        self.assertFalse(result["metrc_write"])
        self.assertFalse(result["state_write"])
        self.assertFalse(result["compliance_decision"])
        self.assertFalse(result["outreach"])
        self.assertFalse(result["prospect_demo"])

    def test_hold_codes_match_fixture_rows(self) -> None:
        result = gate.run_gate()
        by_code: dict[str, list[str]] = {}
        for item in result["holds"]:
            by_code.setdefault(item["code"], []).append(item["request_id"])
        self.assertEqual(
            sorted(by_code["MISSING_METRC_TRANSFER"]),
            ["RCL-%03d" % n for n in range(76, 84)],
        )
        self.assertEqual(
            sorted(by_code["BATCH_COUNT_MISMATCH"]),
            ["RCL-%03d" % n for n in range(84, 91)],
        )
        self.assertEqual(
            sorted(by_code["DUPLICATE_PACKAGE_ID"]),
            ["RCL-%03d" % n for n in range(91, 96)],
        )
        self.assertEqual(
            sorted(by_code["UNCONFIRMED_APPOINTMENT"]),
            ["RCL-%03d" % n for n in range(96, 101)],
        )
        self.assertEqual(
            result["ready_request_ids"],
            ["RCL-%03d" % n for n in range(1, 76)],
        )

    def test_unconfirmed_wins_even_when_metrc_is_present(self) -> None:
        row = next(
            item
            for item in gate.build_acceptance_fixture()
            if item["request_id"] == "RCL-096"
        )
        self.assertFalse(row["appointment"]["confirmed"])
        self.assertIsNotNone(row["metrc_transfer"])
        verdict = gate.classify_request(row, package_counts={})
        self.assertEqual(verdict["status"], "HOLD")
        self.assertEqual(verdict["code"], "UNCONFIRMED_APPOINTMENT")

    def test_duplicate_package_ids_are_global(self) -> None:
        rows = gate.build_acceptance_fixture()
        counts = gate.package_frequency(rows)
        self.assertEqual(counts[gate.DUP_PACKAGE_ID], 5)
        for n in range(91, 96):
            row = next(item for item in rows if item["request_id"] == "RCL-%03d" % n)
            verdict = gate.classify_request(row, package_counts=counts)
            self.assertEqual(verdict["code"], "DUPLICATE_PACKAGE_ID")

        lone = deepcopy(rows[0])
        lone["request_id"] = "RCL-SOLO"
        lone["web_request"]["package_ids"] = ["1A4FF00000000000SOLO0001"]
        lone["metrc_transfer"]["package_ids"] = ["1A4FF00000000000SOLO0001"]
        solo_counts = gate.package_frequency([lone])
        self.assertEqual(gate.classify_request(lone, package_counts=solo_counts)["status"], "DISPATCH_READY")

        twin = deepcopy(lone)
        twin["request_id"] = "RCL-TWIN"
        twin_counts = gate.package_frequency([lone, twin])
        self.assertEqual(gate.classify_request(lone, package_counts=twin_counts)["code"], "DUPLICATE_PACKAGE_ID")
        self.assertEqual(gate.classify_request(twin, package_counts=twin_counts)["code"], "DUPLICATE_PACKAGE_ID")


if __name__ == "__main__":
    unittest.main()
