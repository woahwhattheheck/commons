import copy
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import firewall as fw


def load(name):
    return json.loads((HERE / "fixtures" / name).read_text(encoding="utf-8"))


class FirewallV2Tests(unittest.TestCase):
    def test_current_qualified_packet_still_needs_independent_authority(self):
        d = fw.evaluate_current(load("qualified_owner_review.json"), writer="Z-Palisade-1445")
        self.assertTrue(d.qualified_for_owner_review)
        self.assertFalse(d.authorized_to_send)
        self.assertIn("OWNER_REVIEW_REQUIRED", d.warnings)
        self.assertIn("WRITER_LEASE_REQUIRED", d.warnings)
        self.assertEqual(d.mode, "CURRENT_PROCESS_TIME")

    def test_retained_synthetic_owner_and_muse_receipts_authorize_exact_example(self):
        d = fw.evaluate_current(load("authorized_example.json"), writer="Z-Palisade-1445")
        self.assertTrue(d.authorized_to_send)
        self.assertEqual(
            d.qualification_digest,
            "6a6dd84bd1a7350ddfc6a2fcc59a4491a1ee34675783cfb7e14479ed327e110c",
        )
        self.assertEqual(
            d.action_digest,
            "f9901eae619ad426f32b98eb2025a10bd7b1fcd09744fcec25786921a29b8bd9",
        )

    def test_candidate_cannot_self_author_owner_or_muse(self):
        p = load("qualified_owner_review.json")
        p["owner_review"] = {"status": "APPROVED", "reviewer": "Bryce"}
        p["writer_lease"] = {"status": "SELECTED", "selected_writer": "Z-Palisade-1445"}
        with self.assertRaisesRegex(fw.PacketError, "forbidden/unknown"):
            fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_candidate_clock_field_is_forbidden(self):
        p = load("qualified_owner_review.json")
        p["as_of_utc"] = "2020-01-01T00:00:00Z"
        with self.assertRaisesRegex(fw.PacketError, "forbidden/unknown"):
            fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_historical_rollback_is_permanently_non_authorizing_even_with_receipts(self):
        p = load("authorized_example.json")
        d = fw.evaluate_historical(
            p, at_utc="2020-01-02T00:00:00Z", writer="Z-Palisade-1445"
        )
        self.assertTrue(d.qualified_for_owner_review)
        self.assertFalse(d.authorized_to_send)
        self.assertEqual(d.mode, "HISTORICAL_REPLAY_NON_CURRENT")
        self.assertIn("HISTORICAL_REPLAY_NON_CURRENT", d.warnings)
        self.assertIsNone(d.owner_receipt_sha256)
        self.assertIsNone(d.writer_lease_receipt_sha256)

    def test_cli_has_no_now_authorization_argument(self):
        packet = HERE / "fixtures" / "authorized_example.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(HERE / "firewall.py"),
                str(packet),
                "--writer",
                "Z-Palisade-1445",
                "--now",
                "2020-01-01T00:00:00Z",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unrecognized arguments: --now", proc.stderr)

    def test_cli_historical_mode_is_non_authorizing(self):
        packet = HERE / "fixtures" / "authorized_example.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(HERE / "firewall.py"),
                str(packet),
                "--writer",
                "Z-Palisade-1445",
                "--historical-at",
                "2026-09-17T19:00:00Z",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["authorized_to_send"])
        self.assertEqual(payload["mode"], "HISTORICAL_REPLAY_NON_CURRENT")

    def test_action_mutation_invalidates_retained_authority(self):
        p = load("authorized_example.json")
        p["action"]["content_sha256"] = "1" * 64
        d = fw.evaluate_current(p, writer="Z-Palisade-1445")
        self.assertFalse(d.authorized_to_send)
        self.assertIn("OWNER_REVIEW_STALE_OR_FOREIGN", d.blockers)
        self.assertIn("WRITER_LEASE_STALE_OR_FOREIGN_ACTION", d.blockers)

    def test_opportunity_mutation_cannot_transplant_source_or_receipts(self):
        p = load("authorized_example.json")
        p["opportunity"]["id"] = "DEMO-2"
        d = fw.evaluate_current(p, writer="Z-Palisade-1445")
        self.assertFalse(d.authorized_to_send)
        self.assertIn("SOURCE_OPPORTUNITY_MISMATCH", d.blockers)
        self.assertIn("OWNER_REVIEW_STALE_OR_FOREIGN", d.blockers)
        self.assertIn("WRITER_LEASE_STALE_OR_FOREIGN_ACTION", d.blockers)

    def test_foreign_writer_cannot_reuse_muse_receipt(self):
        d = fw.evaluate_current(load("authorized_example.json"), writer="Z-Other")
        self.assertFalse(d.authorized_to_send)
        self.assertIn("WRITER_LEASE_FOREIGN_WRITER", d.blockers)

    def test_unknown_or_pathlike_receipt_ids_fail_closed(self):
        for value in ("../../forged", "not-retained"):
            p = load("qualified_owner_review.json")
            p["owner_review_receipt_id"] = value
            with self.subTest(value=value), self.assertRaises(fw.PacketError):
                fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_unknown_source_id_cannot_self_mint_source(self):
        p = load("qualified_owner_review.json")
        p["source"] = {"source_id": "attacker-source"}
        with self.assertRaisesRegex(fw.PacketError, "trusted retained-source index"):
            fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_source_object_cannot_supply_locator_or_sha(self):
        p = load("qualified_owner_review.json")
        p["source"] = {"source_id": "demo-source-v1", "sha256": "0" * 64}
        with self.assertRaisesRegex(fw.PacketError, "forbidden/unknown"):
            fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_strict_json_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(fw.PacketError, "duplicate JSON key"):
            fw._strict_json_bytes(b'{"a":1,"a":2}', "packet")

    def test_strict_json_rejects_non_finite_constants(self):
        with self.assertRaisesRegex(fw.PacketError, "non-finite"):
            fw._strict_json_bytes(b'{"a":NaN}', "packet")

    def test_programmatic_mapping_subclass_is_rejected(self):
        class Stateful(dict):
            pass

        with self.assertRaisesRegex(fw.PacketError, "plain JSON"):
            fw.evaluate_current(
                Stateful(load("qualified_owner_review.json")), writer="Z-Palisade-1445"
            )

    def test_nested_schema_is_closed(self):
        p = load("qualified_owner_review.json")
        p["action"]["owner_override"] = "APPROVED"
        with self.assertRaisesRegex(fw.PacketError, "forbidden/unknown"):
            fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_invalid_alternate_submission_route_is_rejected(self):
        p = load("qualified_owner_review.json")
        p["submission"]["locator"] = "ftp://buyer.example/submit"
        with self.assertRaisesRegex(fw.PacketError, "absolute http"):
            fw.evaluate_historical(
                p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
            )

    def test_unknown_submission_and_registration_hold(self):
        p = load("qualified_owner_review.json")
        p["submission"]["route_state"] = "UNKNOWN"
        p["submission"]["registration_required"] = True
        p["submission"]["registration_state"] = "UNKNOWN"
        d = fw.evaluate_historical(
            p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
        )
        self.assertIn("SUBMISSION_ROUTE_NOT_PROVEN", d.blockers)
        self.assertIn("REGISTRATION_NOT_PROVEN", d.blockers)

    def test_unknown_eligibility_never_qualifies(self):
        p = load("qualified_owner_review.json")
        p["eligibility"]["gates"][0]["state"] = "UNKNOWN"
        p["eligibility"]["gates"][0]["evidence_refs"] = []
        d = fw.evaluate_historical(
            p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
        )
        self.assertFalse(d.qualified_for_owner_review)
        self.assertIn("ELIGIBILITY_UNKNOWN:prime eligibility", d.blockers)

    def test_proven_eligibility_requires_evidence(self):
        p = load("qualified_owner_review.json")
        p["eligibility"]["gates"][0]["evidence_refs"] = []
        with self.assertRaisesRegex(fw.PacketError, "needs evidence_refs"):
            fw.evaluate_historical(
                p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
            )

    def test_dnr_and_bounce_dominate(self):
        for state in ("DNR", "BOUNCE"):
            p = load("qualified_owner_review.json")
            p["target"]["relationship_state"] = state
            d = fw.evaluate_historical(
                p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
            )
            with self.subTest(state=state):
                self.assertFalse(d.qualified_for_owner_review)
                self.assertIn(f"RELATIONSHIP_{state}", d.blockers)

    def test_email_route_contact_aliases_normalize(self):
        p = load("qualified_owner_review.json")
        p["target"]["contact"] = "Opps@Example.Com"
        p["action"]["route"] = "mailto:OPPS@example.com"
        d = fw.evaluate_historical(
            p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
        )
        self.assertNotIn("ACTION_ROUTE_CONTACT_MISMATCH", d.blockers)

    def test_email_route_contact_mismatch_holds(self):
        p = load("qualified_owner_review.json")
        p["action"]["route"] = "other@example.com"
        d = fw.evaluate_historical(
            p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
        )
        self.assertIn("ACTION_ROUTE_CONTACT_MISMATCH", d.blockers)

    def test_zero_or_nonfinite_economics_are_rejected(self):
        for amount in ("0", "Infinity"):
            p = load("qualified_owner_review.json")
            p["economics"]["amount"] = amount
            with self.subTest(amount=amount), self.assertRaises(fw.PacketError):
                fw.evaluate_historical(
                    p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
                )

    def test_unbounded_scope_is_rejected(self):
        p = load("qualified_owner_review.json")
        p["economics"]["bounded_scope"] = "   "
        with self.assertRaisesRegex(fw.PacketError, "non-empty"):
            fw.evaluate_historical(
                p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
            )

    def test_unknown_payment_path_holds(self):
        p = load("qualified_owner_review.json")
        p["economics"]["payment_path_state"] = "UNKNOWN"
        d = fw.evaluate_historical(
            p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
        )
        self.assertIn("PAYMENT_PATH_NOT_PROVEN", d.blockers)

    def test_duplicate_prior_action_holds_across_email_aliases(self):
        p = load("qualified_owner_review.json")
        baseline = fw.evaluate_historical(
            p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
        )
        p["target"]["contact"] = "Opps@Example.Com"
        p["action"]["route"] = "mailto:OPPS@example.com"
        p["prior_actions"] = [{"dedupe_key": baseline.dedupe_key, "state": "SENT"}]
        d = fw.evaluate_historical(
            p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
        )
        self.assertIn("DUPLICATE_PRIOR_ACTION:SENT", d.blockers)

    def test_short_runway_fixture_is_held(self):
        d = fw.evaluate_historical(
            load("held_short_runway.json"),
            at_utc="2026-09-17T19:00:00Z",
            writer="Z-Palisade-1445",
        )
        self.assertFalse(d.qualified_for_owner_review)
        self.assertIn("RUNWAY_BELOW_MINIMUM", d.blockers)

    def test_deadline_boundary_is_deterministic(self):
        p = load("qualified_owner_review.json")
        p["opportunity"]["deadline_utc"] = "2026-09-19T19:00:00Z"
        p["opportunity"]["min_runway_hours"] = 48
        d = fw.evaluate_historical(
            p, at_utc="2026-09-17T19:00:00Z", writer="Z-Palisade-1445"
        )
        self.assertTrue(d.qualified_for_owner_review)
        self.assertEqual(d.runway_seconds, 48 * 3600)
        self.assertIn("RUNWAY_EXACTLY_AT_MINIMUM", d.warnings)

    def test_retained_source_file_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td) / "retained_sources"
            shutil.copytree(HERE / "retained_sources", tmp)
            (tmp / "files" / "source_authority.json").write_text(
                '{"authority":"retained","opportunity":"DEMO-1","revision":"ATTACK"}\n',
                encoding="utf-8",
            )
            with mock.patch.object(fw, "SOURCE_ROOT", tmp):
                with self.assertRaisesRegex(fw.PacketError, "retained source digest mismatch"):
                    fw.evaluate_historical(
                        load("qualified_owner_review.json"),
                        at_utc="2026-09-17T19:00:00Z",
                        writer="Z-Palisade-1445",
                    )

    def test_retained_source_index_reseal_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td) / "retained_sources"
            shutil.copytree(HERE / "retained_sources", tmp)
            index = tmp / "index.json"
            index.write_text(index.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with mock.patch.object(fw, "SOURCE_ROOT", tmp):
                with self.assertRaisesRegex(fw.PacketError, "root digest mismatch"):
                    fw.evaluate_historical(
                        load("qualified_owner_review.json"),
                        at_utc="2026-09-17T19:00:00Z",
                        writer="Z-Palisade-1445",
                    )

    def test_retained_authority_receipt_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td) / "retained_authority"
            shutil.copytree(HERE / "retained_authority", tmp)
            receipt = tmp / "owner" / "demo-owner-approval-v1.json"
            receipt.write_text(receipt.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with mock.patch.object(fw, "AUTHORITY_ROOT", tmp):
                with self.assertRaisesRegex(fw.PacketError, "retained owner receipt digest mismatch"):
                    fw.evaluate_current(load("authorized_example.json"), writer="Z-Palisade-1445")

    def test_hard_link_alias_is_rejected_by_retained_reader(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            os.link(target, root / "alias.json")
            with self.assertRaisesRegex(fw.PacketError, "exactly one hard link"):
                fw._read_retained_file(root, "target.json", name="hardlink")

    def test_symlink_leaf_and_parent_are_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "real").mkdir()
            (root / "real" / "leaf").write_text("ok", encoding="utf-8")
            os.symlink(root / "real" / "leaf", root / "leaf-link")
            with self.assertRaises(fw.PacketError):
                fw._read_retained_file(root, "leaf-link", name="leaf symlink")
            os.symlink(root / "real", root / "parent-link")
            with self.assertRaises(fw.PacketError):
                fw._read_retained_file(root, "parent-link/leaf", name="parent symlink")

    def test_parent_swap_after_dirfd_open_cannot_redirect_leaf(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            original_dir = root / "nested"
            original_dir.mkdir()
            (original_dir / "leaf.json").write_text("ORIGINAL", encoding="utf-8")

            real_open = os.open
            swapped = {"done": False}

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                fd = real_open(path, flags, mode, dir_fd=dir_fd)
                if (
                    path == "nested"
                    and dir_fd is not None
                    and flags & os.O_DIRECTORY
                    and not swapped["done"]
                ):
                    swapped["done"] = True
                    original_dir.rename(root / "nested.old")
                    replacement = root / "nested"
                    replacement.mkdir()
                    (replacement / "leaf.json").write_text("ATTACKER", encoding="utf-8")
                return fd

            with mock.patch.object(fw.os, "open", side_effect=racing_open):
                data = fw._read_retained_file(root, "nested/leaf.json", name="parent swap")
            self.assertTrue(swapped["done"])
            self.assertEqual(data, b"ORIGINAL")

    def test_relative_escape_is_rejected_before_open(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(fw.PacketError, "path is invalid"):
                fw._read_retained_file(pathlib.Path(td), "../outside", name="escape")


if __name__ == "__main__":
    unittest.main(verbosity=2)
