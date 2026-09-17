from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "revenue" / "gguf_enterprise_close_kit" / "close_kit.py"
INTAKE = ROOT / "revenue" / "gguf_enterprise_close_kit" / "sample_intake.json"
EVIDENCE = ROOT / "revenue" / "gguf_enterprise_close_kit" / "sample_evidence.json"
RECOVERY = ROOT / "revenue" / "payment_ready" / "recovery.json"
PACK = ROOT / "revenue" / "payment_ready" / "pack.json"

spec = importlib.util.spec_from_file_location("gguf_close_kit_test", MODULE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class GgufEnterpriseCloseKitTests(unittest.TestCase):
    def test_canonical_offer_matches_existing_recovery_and_pack(self) -> None:
        recovery = load(RECOVERY)
        pack = load(PACK)
        offer = mod.canonical_offer()
        for source in (recovery["offer"], pack["offer"]):
            self.assertEqual(source["offer_id"], offer["offer_id"])
            self.assertEqual(source["fixed_amount"], offer["fixed_amount"])
            self.assertEqual(source["term_calendar_days"], offer["term_calendar_days"])
            self.assertEqual(source["acceptance_rule"].lower(), offer["acceptance_rule"])
        self.assertEqual(recovery["offer"]["terms_sha256"], offer["terms_sha256"])
        self.assertEqual([row["amount"] for row in recovery["offer"]["milestones"]], [6000, 6000])
        self.assertEqual(recovery["offer"]["acceptance_tests"], list(mod.ACCEPTANCE_IDS))

    def test_synthetic_sample_is_complete_but_never_commercial_truth(self) -> None:
        packet = mod.compile_packet(load(INTAKE), load(EVIDENCE))
        self.assertEqual(packet["terminal_state"], "SYNTHETIC_DEMO_COMPLETE")
        self.assertTrue(packet["acceptance"]["all_at1_at6_evidence_complete"])
        self.assertTrue(all(packet["acceptance"]["tests"].values()))
        self.assertTrue(packet["truth"]["synthetic_demo"])
        self.assertFalse(packet["truth"]["build_is_buyer_interest"])
        self.assertFalse(packet["truth"]["build_is_payment"])
        self.assertFalse(packet["truth"]["build_is_revenue"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))
        mod.verify_packet(packet)

    def test_metric_lift_is_irrelevant_to_acceptance(self) -> None:
        evidence = load(EVIDENCE)
        evidence["harness_runs"]["ablation"]["metrics"]["task_score"] = 0.99
        evidence["harness_runs"]["restore"]["metrics"]["task_score"] = 0.10
        packet = mod.compile_packet(load(INTAKE), evidence)
        self.assertTrue(packet["acceptance"]["all_at1_at6_evidence_complete"])
        self.assertFalse(packet["benchmark"]["metric_lift_is_acceptance"])

    def test_ablation_must_change_artifact(self) -> None:
        evidence = load(EVIDENCE)
        evidence["artifacts"]["ablated_sha256"] = evidence["artifacts"]["original_sha256"]
        packet = mod.compile_packet(load(INTAKE), evidence)
        self.assertFalse(packet["acceptance"]["tests"]["AT2"])
        self.assertEqual(packet["terminal_state"], "SYNTHETIC_DEMO_HOLD")

    def test_restore_must_be_byte_exact(self) -> None:
        evidence = load(EVIDENCE)
        evidence["artifacts"]["restored_sha256"] = "9" * 64
        packet = mod.compile_packet(load(INTAKE), evidence)
        self.assertFalse(packet["acceptance"]["tests"]["AT3"])
        self.assertEqual(packet["terminal_state"], "SYNTHETIC_DEMO_HOLD")

    def test_privacy_flags_fail_closed(self) -> None:
        for flag in ("public_model_bytes_present", "public_secret_values_present", "public_private_contact_present"):
            intake = load(INTAKE)
            intake["privacy"][flag] = True
            with self.assertRaisesRegex(mod.InputError, "privacy violation"):
                mod.compile_packet(intake, load(EVIDENCE))

    def test_public_binary_claim_fails_closed(self) -> None:
        evidence = load(EVIDENCE)
        evidence["claims"]["public_binary_bytes_present"] = True
        with self.assertRaisesRegex(mod.InputError, "public binary bytes"):
            mod.compile_packet(load(INTAKE), evidence)

    def test_acceptance_or_payment_claims_fail_closed(self) -> None:
        for key in ("buyer_acceptance_claimed", "payment_claimed"):
            evidence = load(EVIDENCE)
            evidence["claims"][key] = True
            with self.assertRaises(mod.InputError):
                mod.compile_packet(load(INTAKE), evidence)

    def test_unknown_fields_are_rejected(self) -> None:
        intake = load(INTAKE)
        intake["buyer_email"] = "forbidden@example.invalid"
        with self.assertRaisesRegex(mod.InputError, "schema mismatch"):
            mod.compile_packet(intake, load(EVIDENCE))

    def test_synthetic_cannot_assert_customer_readiness_or_refs(self) -> None:
        intake = load(INTAKE)
        intake["customer_readiness"]["nda_signed"] = True
        with self.assertRaisesRegex(mod.InputError, "synthetic demo"):
            mod.compile_packet(intake, load(EVIDENCE))
        intake = load(INTAKE)
        intake["evidence_refs"]["nda_sha256"] = "2" * 64
        with self.assertRaisesRegex(mod.InputError, "synthetic demo"):
            mod.compile_packet(intake, load(EVIDENCE))

    def test_customer_mode_holds_until_every_start_gate(self) -> None:
        intake = load(INTAKE)
        intake["mode"] = "CUSTOMER_PRIVATE"
        intake["scope"]["data_classification"] = "PRIVATE_CUSTOMER_CONTROLLED"
        packet = mod.compile_packet(intake, load(EVIDENCE))
        self.assertEqual(packet["terminal_state"], "HOLD_PRE_FILE_EXCHANGE")
        self.assertEqual(len(packet["readiness"]["holds"]), 5)

    def test_customer_ready_packet_can_reach_owner_m2_review_without_claiming_acceptance(self) -> None:
        intake = load(INTAKE)
        intake["mode"] = "CUSTOMER_PRIVATE"
        intake["scope"]["data_classification"] = "PRIVATE_CUSTOMER_CONTROLLED"
        for key in intake["customer_readiness"]:
            intake["customer_readiness"][key] = True
        intake["evidence_refs"] = {"nda_sha256": "2" * 64, "sow_sha256": "3" * 64, "m1_sha256": "4" * 64}
        packet = mod.compile_packet(intake, load(EVIDENCE))
        self.assertEqual(packet["terminal_state"], "READY_FOR_OWNER_M2_ACCEPTANCE_REVIEW")
        self.assertEqual(packet["milestones"]["M2"], "READY_FOR_OWNER_ACCEPTANCE_REVIEW")
        self.assertTrue(packet["expansion"]["white_box_30d_discussion_ready"])
        self.assertFalse(packet["acceptance"]["legal_acceptance_claimed"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))

    def test_true_customer_gate_requires_matching_digest(self) -> None:
        intake = load(INTAKE)
        intake["mode"] = "CUSTOMER_PRIVATE"
        intake["scope"]["data_classification"] = "PRIVATE_CUSTOMER_CONTROLLED"
        intake["customer_readiness"]["nda_signed"] = True
        with self.assertRaisesRegex(mod.InputError, "requires nda_sha256"):
            mod.compile_packet(intake, load(EVIDENCE))

    def test_digest_without_true_gate_is_rejected(self) -> None:
        intake = load(INTAKE)
        intake["mode"] = "CUSTOMER_PRIVATE"
        intake["scope"]["data_classification"] = "PRIVATE_CUSTOMER_CONTROLLED"
        intake["evidence_refs"]["sow_sha256"] = "3" * 64
        with self.assertRaisesRegex(mod.InputError, "present while sow_signed=false"):
            mod.compile_packet(intake, load(EVIDENCE))

    def test_case_id_mismatch_rejected(self) -> None:
        evidence = load(EVIDENCE)
        evidence["case_id"] = "synthetic-other-001"
        with self.assertRaisesRegex(mod.InputError, "case_id mismatch"):
            mod.compile_packet(load(INTAKE), evidence)

    def test_metric_key_set_mismatch_rejected(self) -> None:
        evidence = load(EVIDENCE)
        del evidence["harness_runs"]["restore"]["metrics"]["latency_ms"]
        with self.assertRaisesRegex(mod.InputError, "metric key sets"):
            mod.compile_packet(load(INTAKE), evidence)

    def test_receipt_tamper_rejected(self) -> None:
        packet = mod.compile_packet(load(INTAKE), load(EVIDENCE))
        packet["terminal_state"] = "READY_FOR_OWNER_M2_ACCEPTANCE_REVIEW"
        with self.assertRaisesRegex(mod.InputError, "receipt mismatch"):
            mod.verify_packet(packet)

    def test_semantic_tamper_with_recomputed_outer_digest_rejected(self) -> None:
        packet = mod.compile_packet(load(INTAKE), load(EVIDENCE))
        packet["authority"]["payment_capture_authorized"] = True
        unsigned = copy.deepcopy(packet)
        unsigned.pop("packet_receipt_sha256")
        packet["packet_receipt_sha256"] = mod.sha256_obj(unsigned)
        with self.assertRaisesRegex(mod.InputError, "semantic verification"):
            mod.verify_packet(packet)

    def test_markdown_truth_labels_synthetic_sample(self) -> None:
        md = mod.render_markdown(mod.compile_packet(load(INTAKE), load(EVIDENCE)))
        self.assertIn("SYNTHETIC / UNPAID / NOT A CUSTOMER CASE", md)
        self.assertIn("rollback evidence, not metric lift", md)
        self.assertIn("does not authorize buyer contact", md)

    def test_cli_compile_verify_and_exclusive_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            packet = Path(td) / "packet.json"
            report = Path(td) / "report.md"
            proc = subprocess.run([sys.executable, str(MODULE), "compile", str(INTAKE), str(EVIDENCE), "--json-out", str(packet), "--markdown-out", str(report)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("SYNTHETIC / UNPAID", report.read_text(encoding="utf-8"))
            verified = subprocess.run([sys.executable, str(MODULE), "verify", str(packet)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(verified.stdout.strip(), "VERIFIED")
            again = subprocess.run([sys.executable, str(MODULE), "compile", str(INTAKE), str(EVIDENCE), "--json-out", str(packet)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(again.returncode, 2)
            self.assertIn("exclusive create refused", again.stderr)

    def test_duplicate_keys_and_nonfinite_json_rejected(self) -> None:
        with self.assertRaisesRegex(mod.InputError, "duplicate JSON key"):
            mod.parse_json_strict('{"x":1,"x":2}')
        with self.assertRaisesRegex(mod.InputError, "non-finite"):
            mod.parse_json_strict('{"x":NaN}')


if __name__ == "__main__":
    unittest.main()
