"""Adversarial tests for the Lane C HOLD/REPAIR order."""

from __future__ import annotations

import json
import os
import pickle
import tempfile
import threading
import unittest
from pathlib import Path

from charttrace.app import (
    ApplicationLockedError,
    CaseLifecycle,
    ChartTraceController,
    ReleaseBlockedError,
)
from charttrace.app.ipc import (
    IpcProtocolError,
    LocalIpcServer,
    encode_frame,
    send_raw,
    send_signed,
)
from charttrace.app.offline_counsel import CounselImportError, import_counsel_review
from charttrace.app.paths import PathEgressError, assert_local_filesystem_path
from charttrace.app.vault import VAULT_MODE, VaultError
from charttrace.legal import LegalState
from charttrace.packaging.unsigned_artifact import build_unsigned_artifact


class VaultFailClosedTests(unittest.TestCase):
    def test_wrong_secret_fails_and_plaintext_cannot_unlock(self):
        with tempfile.TemporaryDirectory() as directory:
            first = ChartTraceController(data_dir=Path(directory), persist=True)
            first.unlock("correct-secret", "Test operator")
            first.create_case("Synthetic vault case")
            state_path = Path(directory) / "charttrace-state.json"
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(VAULT_MODE, payload["vault_mode"])
            self.assertFalse(payload["encryption_claimed"])
            self.assertFalse(payload["can_unlock_protected_data"])
            self.assertEqual("", payload["cases"][0]["name"])
            self.assertEqual([], payload["cases"][0]["sources"])

            locked = ChartTraceController(data_dir=Path(directory), persist=True)
            with self.assertRaises(ApplicationLockedError):
                locked.unlock("wrong-secret", "Attacker")
            self.assertFalse(locked.unlocked)

            empty = ChartTraceController(data_dir=Path(directory), persist=True)
            with self.assertRaises(ApplicationLockedError):
                empty.unlock("", "Attacker")

    def test_legacy_plaintext_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "charttrace-state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "cases": [
                            {
                                "name": "phi-adjacent",
                                "case_id": "x",
                                "lifecycle": "DRAFT",
                                "sources": [{"display_name": "note.pdf"}],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(VaultError):
                ChartTraceController(data_dir=Path(directory), persist=True)


class CounselNonAuthoritativeTests(unittest.TestCase):
    def _ready_controller(self):
        controller = ChartTraceController(persist=False)
        controller.unlock("test-only-secret", "Test operator")
        acknowledgements = controller.consent.blank_acknowledgements()
        controller.accept_legal({key: True for key in acknowledgements}, "Test operator")
        return controller

    def test_forged_counsel_file_cannot_approve_or_clear_hold(self):
        controller = self._ready_controller()
        case = controller.create_case("Synthetic counsel case")
        controller.secure_ingest(case.case_id, [("source.txt", b"synthetic")])
        controller.run_peer_analysis(case.case_id)
        controller.complete_internal_qa(case.case_id)
        controller.place_authority_hold("Authority dispute")
        with tempfile.TemporaryDirectory() as directory:
            forged = Path(directory) / "forged.json"
            forged.write_text(
                json.dumps(
                    {
                        "mode": "offline_counsel_review",
                        "case_id": case.case_id,
                        "reviewed_by": "Self Attested Counsel",
                        "decision": "approve",
                        "approval_authoritative": True,
                        "clears_legal_hold": True,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(CounselImportError):
                controller.import_offline_counsel_review(case.case_id, forged)
        self.assertEqual(LegalState.AUTHORITY_HOLD, controller.legal_state)
        self.assertEqual(CaseLifecycle.HUMAN_RELEASE_REVIEW, case.lifecycle)

    def test_unsigned_four_field_json_is_non_authoritative(self):
        controller = self._ready_controller()
        case = controller.create_case("Synthetic counsel case")
        controller.secure_ingest(case.case_id, [("source.txt", b"synthetic")])
        controller.run_peer_analysis(case.case_id)
        controller.complete_internal_qa(case.case_id)
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "review.json"
            bundle.write_text(
                json.dumps(
                    {
                        "mode": "offline_counsel_review",
                        "case_id": case.case_id,
                        "reviewed_by": "Unsigned Reviewer",
                        "decision": "approve",
                    }
                ),
                encoding="utf-8",
            )
            record = controller.import_offline_counsel_review(case.case_id, bundle)
        self.assertEqual("NON_AUTHORITATIVE_REVIEW_RECORD", record["kind"])
        self.assertFalse(record["authoritative"])
        self.assertFalse(record["clears_legal_hold"])
        self.assertEqual(CaseLifecycle.HUMAN_RELEASE_REVIEW, case.lifecycle)


class StaleTransferAuthTests(unittest.TestCase):
    def test_authority_hold_invalidates_named_recipient_authorization(self):
        controller = ChartTraceController(persist=False)
        controller.unlock("test-only-secret", "Test operator")
        acknowledgements = controller.consent.blank_acknowledgements()
        controller.accept_legal({key: True for key in acknowledgements}, "Test operator")
        case = controller.create_case("Synthetic release case")
        controller.secure_ingest(case.case_id, [("source.bin", b"synthetic")])
        controller.run_peer_analysis(case.case_id)
        controller.complete_internal_qa(case.case_id)
        controller.complete_human_review(case.case_id, "Named reviewer", approved=True)
        controller.set_recipient(case.case_id, "Named recipient", "attorney")
        controller.authorize_recipient_transfer(case.case_id, True, "Test operator")
        self.assertEqual(LegalState.TRANSFER_AUTHORIZED, case.transfer_state)
        controller.place_authority_hold("Authority requires confirmation")
        self.assertEqual(LegalState.TRANSFER_NOT_AUTHORIZED, case.transfer_state)
        self.assertIsNone(case.recipient.authorized_at)
        controller.clear_authority_hold()
        controller.accept_legal({key: True for key in acknowledgements}, "Test operator")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "release.json"
            with self.assertRaises(ReleaseBlockedError):
                controller.build_release(case.case_id, destination)
            controller.authorize_recipient_transfer(case.case_id, True, "Test operator")
            controller.build_release(case.case_id, destination)
            self.assertTrue(destination.is_file())


class JsonIpcTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "Filesystem-domain sockets are the Unix proof.")
    def test_pickle_and_object_input_are_rejected(self):
        server = LocalIpcServer("pickle-proof")
        server.start()
        errors = []

        def attack() -> None:
            try:
                send_raw(server.address, pickle.dumps({"op": "ping"}))
            except OSError as error:
                errors.append(error)

        try:
            worker = threading.Thread(target=attack)
            worker.start()
            with self.assertRaises(IpcProtocolError):
                server.receive_once()
            worker.join(timeout=2)
        finally:
            server.close()

    @unittest.skipIf(os.name == "nt", "Filesystem-domain sockets are the Unix proof.")
    def test_signed_json_round_trip_and_replay_fail(self):
        server = LocalIpcServer("json-proof")
        server.start()
        try:
            def send() -> None:
                send_signed("json-proof", server.address, "ping", "nonce-1")

            worker = threading.Thread(target=send)
            worker.start()
            payload = server.receive_once()
            worker.join(timeout=2)
            self.assertEqual("ping", payload["op"])

            def replay() -> None:
                send_signed("json-proof", server.address, "ping", "nonce-1")

            worker = threading.Thread(target=replay)
            worker.start()
            with self.assertRaises(IpcProtocolError):
                server.receive_once()
            worker.join(timeout=2)
        finally:
            server.close()

    def test_ipc_source_has_no_listener_or_pickle(self):
        source = Path(__file__).with_name("ipc.py").read_text(encoding="utf-8")
        self.assertNotIn("multiprocessing", source)
        self.assertNotIn("from multiprocessing", source)
        self.assertNotIn("Listener", source)
        self.assertNotIn("import pickle", source)


class PathEgressTests(unittest.TestCase):
    def test_unc_device_symlink_and_traversal_are_rejected(self):
        with self.assertRaises(PathEgressError):
            assert_local_filesystem_path(r"\\fileserver\share\out.json")
        with self.assertRaises(PathEgressError):
            assert_local_filesystem_path("//fileserver/share/out.json")
        with self.assertRaises(PathEgressError):
            assert_local_filesystem_path("NUL")
        with self.assertRaises(PathEgressError):
            assert_local_filesystem_path("../escape/out.json")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.mkdir()
            link = Path(directory) / "link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation is unavailable")
            with self.assertRaises(PathEgressError):
                assert_local_filesystem_path(link / "out.json")

    def test_release_rejects_unc_destination(self):
        controller = ChartTraceController(persist=False)
        controller.unlock("test-only-secret", "Test operator")
        acknowledgements = controller.consent.blank_acknowledgements()
        controller.accept_legal({key: True for key in acknowledgements}, "Test operator")
        case = controller.create_case("Synthetic path case")
        controller.secure_ingest(case.case_id, [("source.bin", b"synthetic")])
        controller.run_peer_analysis(case.case_id)
        controller.complete_internal_qa(case.case_id)
        controller.complete_human_review(case.case_id, "Named reviewer", approved=True)
        controller.set_recipient(case.case_id, "Named recipient", "attorney")
        controller.authorize_recipient_transfer(case.case_id, True, "Test operator")
        with self.assertRaises(PathEgressError):
            controller.build_release(case.case_id, Path(r"\\fileserver\share\out.json"))


class WindowsPackagingReadbackTests(unittest.TestCase):
    def test_unsigned_artifact_receipt_is_truthful(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = build_unsigned_artifact(Path(directory))
            self.assertEqual("UNSIGNED_SYNTHETIC", receipt["artifact_label"])
            self.assertEqual("unsigned", receipt["signing_state"])
            self.assertFalse(receipt["production"])
            self.assertFalse(receipt["windows_pe_built"])
            self.assertEqual(0, receipt["smoke"]["returncode"])
            self.assertIn("UNSIGNED_SYNTHETIC", receipt["smoke"]["startup"]["build_label"])
            self.assertTrue(Path(receipt["bundle_path"]).is_file())
            self.assertEqual(64, len(receipt["bundle_sha256"]))


if __name__ == "__main__":
    unittest.main()
