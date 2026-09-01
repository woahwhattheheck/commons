"""Adversarial tests for the Lane C HOLD/REPAIR order."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from charttrace.app import (
    ApplicationLockedError,
    CaseLifecycle,
    ChartTraceController,
    ReleaseBlockedError,
    SYNTHETIC_RELEASED,
)
from charttrace.app.ipc import (
    IpcDisabledError,
    IpcProtocolError,
    LocalIpcServer,
    PRODUCT_IPC_ENABLED,
    decode_frame,
    encode_frame,
    sign_message,
)
from charttrace.app.offline_counsel import CounselImportError, import_counsel_review
from charttrace.app.paths import PathEgressError, assert_local_filesystem_path
from charttrace.app.vault import VAULT_MODE, VaultError
from charttrace.legal import LegalState
from charttrace.packaging.unsigned_artifact import build_unsigned_artifact
from charttrace.packaging.unsigned_pe import build_unsigned_pe_bytes


class VaultFailClosedTests(unittest.TestCase):
    def test_wrong_secret_fails_and_plaintext_cannot_unlock(self):
        self.assertFalse(SYNTHETIC_RELEASED)
        with tempfile.TemporaryDirectory() as directory:
            first = ChartTraceController(data_dir=Path(directory), persist=True)
            first.unlock("correct-secret", "Test operator")
            first.create_case("Synthetic vault case")
            state_path = Path(directory) / "charttrace-state.json"
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(VAULT_MODE, payload["vault_mode"])
            self.assertFalse(payload["encryption_claimed"])
            self.assertFalse(payload["can_unlock_protected_data"])
            self.assertFalse(payload["synthetic_released"])
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

    def test_claimed_encryption_and_protected_flags_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            first = ChartTraceController(data_dir=Path(directory), persist=True)
            first.unlock("correct-secret", "Test operator")
            state_path = Path(directory) / "charttrace-state.json"
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            payload["encryption_claimed"] = True
            state_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(VaultError):
                ChartTraceController(data_dir=Path(directory), persist=True)

        with tempfile.TemporaryDirectory() as directory:
            first = ChartTraceController(data_dir=Path(directory), persist=True)
            first.unlock("correct-secret", "Test operator")
            state_path = Path(directory) / "charttrace-state.json"
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            payload["protected_data_present"] = True
            state_path.write_text(json.dumps(payload), encoding="utf-8")
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
        self.assertIsNone(case.human_reviewed_by)

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
        self.assertFalse(record["applies_human_approval"])
        self.assertEqual(CaseLifecycle.HUMAN_RELEASE_REVIEW, case.lifecycle)
        self.assertIsNone(case.human_reviewed_by)

    def test_nested_and_unknown_counsel_fields_are_rejected(self):
        controller = self._ready_controller()
        case = controller.create_case("Synthetic counsel case")
        with tempfile.TemporaryDirectory() as directory:
            nested = Path(directory) / "nested.json"
            nested.write_text(
                json.dumps(
                    {
                        "mode": "offline_counsel_review",
                        "case_id": case.case_id,
                        "reviewed_by": "Nested Forger",
                        "decision": "approve",
                        "notes": {"approved": True},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(CounselImportError):
                import_counsel_review(nested, case.case_id)
            extra = Path(directory) / "extra.json"
            extra.write_text(
                json.dumps(
                    {
                        "mode": "offline_counsel_review",
                        "case_id": case.case_id,
                        "reviewed_by": "Licensed Counsel",
                        "decision": "approve",
                        "licensed_counsel": True,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(CounselImportError):
                import_counsel_review(extra, case.case_id)


class StaleTransferAuthTests(unittest.TestCase):
    def _ready_release_case(self, controller):
        case = controller.create_case("Synthetic release case")
        controller.secure_ingest(case.case_id, [("source.bin", b"synthetic")])
        controller.run_peer_analysis(case.case_id)
        controller.complete_internal_qa(case.case_id)
        controller.complete_human_review(case.case_id, "Named reviewer", approved=True)
        controller.set_recipient(case.case_id, "Named recipient", "attorney")
        controller.authorize_recipient_transfer(case.case_id, True, "Test operator")
        return case

    def test_authority_hold_invalidates_named_recipient_authorization(self):
        controller = ChartTraceController(persist=False)
        controller.unlock("test-only-secret", "Test operator")
        acknowledgements = controller.consent.blank_acknowledgements()
        controller.accept_legal({key: True for key in acknowledgements}, "Test operator")
        case = self._ready_release_case(controller)
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

    def test_terms_reaccept_invalidates_stale_transfer_authorization(self):
        controller = ChartTraceController(persist=False)
        controller.unlock("test-only-secret", "Test operator")
        acknowledgements = controller.consent.blank_acknowledgements()
        controller.accept_legal({key: True for key in acknowledgements}, "Test operator")
        case = self._ready_release_case(controller)
        prior_epoch = case.recipient.authorization_epoch
        controller.accept_legal({key: True for key in acknowledgements}, "Test operator")
        self.assertEqual(LegalState.TRANSFER_NOT_AUTHORIZED, case.transfer_state)
        self.assertIsNone(case.recipient.authorized_at)
        self.assertNotEqual(prior_epoch, controller.consent.authority_epoch)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "release.json"
            with self.assertRaises(ReleaseBlockedError):
                controller.build_release(case.case_id, destination)


class JsonIpcTests(unittest.TestCase):
    def test_pickle_and_object_input_are_rejected(self):
        with self.assertRaises(IpcProtocolError):
            decode_frame(b"\x80\x04junk", b"\x00" * 32, set())

    def test_signed_json_round_trip_and_replay_fail(self):
        session_key = b"k" * 32
        payload = {"v": 1, "op": "ping", "nonce": "nonce-1"}
        payload["mac"] = sign_message(session_key, payload)
        frame = encode_frame(payload)
        seen = set()
        decoded = decode_frame(frame, session_key, seen)
        self.assertEqual("ping", decoded["op"])
        with self.assertRaises(IpcProtocolError):
            decode_frame(frame, session_key, seen)

    def test_ipc_source_has_no_socket_listener_or_pickle(self):
        source = Path(__file__).with_name("ipc.py").read_text(encoding="utf-8")
        self.assertNotIn("multiprocessing", source)
        self.assertNotIn("from multiprocessing", source)
        self.assertNotIn("Listener", source)
        self.assertNotIn("import pickle", source)
        self.assertNotIn("import socket", source)
        self.assertNotIn("AF_INET", source)
        self.assertFalse(PRODUCT_IPC_ENABLED)
        self.assertIn("DISABLED_NOT_PRODUCT", source)
        with self.assertRaises(IpcDisabledError):
            LocalIpcServer("disabled-proof")

    def test_oversized_and_unsigned_frames_fail(self):
        unsigned = encode_frame(
            {"v": 1, "op": "ping", "nonce": "x", "mac": "00"}
        )
        with self.assertRaises(IpcProtocolError):
            decode_frame(unsigned, b"k" * 32, set())
        oversized = b"CTJ1" + (70_000).to_bytes(4, "big") + b"x" * 16
        with self.assertRaises(IpcProtocolError):
            decode_frame(oversized, b"k" * 32, set())


class PathEgressTests(unittest.TestCase):
    def _link_directory(self, link: Path, target: Path) -> None:
        try:
            link.symlink_to(target, target_is_directory=True)
            return
        except OSError as error:
            if os.name != "nt" or getattr(error, "winerror", None) != 1314:
                raise
        completed = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            self.skipTest(f"Windows reparse-point creation failed: {completed.stderr}")

    def test_unc_device_symlink_and_traversal_are_rejected(self):
        rejected = (
            r"\\fileserver\share\out.json",
            "//fileserver/share/out.json",
            r"\\?\UNC\fileserver\share\out.json",
            r"\\.\pipe\charttrace",
            "NUL",
            "COM1",
            "../escape/out.json",
            "foo/../../etc/passwd",
            "smb://fileserver/share/out.json",
            "file:///tmp/out.json",
            "C:relative",
        )
        for raw in rejected:
            with self.subTest(path=raw):
                with self.assertRaises(PathEgressError):
                    assert_local_filesystem_path(raw)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.mkdir()
            link = Path(directory) / "link"
            self._link_directory(link, target)
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
    def test_stub_generation_is_retired(self):
        with self.assertRaises(RuntimeError):
            build_unsigned_pe_bytes()

    def test_receipter_rejects_stub_sized_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "not-charttrace.exe"
            fake.write_bytes(b"MZ" + b"x" * 1534)
            with self.assertRaises(ValueError):
                build_unsigned_artifact(fake, root / "receipt")

    def test_receipter_never_substitutes_host_python_launcher(self):
        source = (
            Path(__file__).parents[1] / "packaging" / "unsigned_artifact.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("launcher_main", source)
        self.assertNotIn("write_unsigned_pe", source)
        self.assertIn("host_python_smoke_used", source)


if __name__ == "__main__":
    unittest.main()

