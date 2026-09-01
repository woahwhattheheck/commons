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
    PathBoundaryError,
)
from charttrace.app.evidence import seal_sources
from charttrace.app.ipc import (
    IpcDisabledError,
    JsonIpcError,
    LocalIpcServer,
    PRODUCT_IPC_ENABLED,
    decode_json_message,
    encode_json_message,
)
from charttrace.app.offline_counsel import CounselImportError
from charttrace.app.paths import validate_local_file, validate_local_output_path
from charttrace.legal import ConsentLedger, LegalState


def accept_current_terms(controller: ChartTraceController) -> None:
    blank = controller.consent.blank_acknowledgements()
    controller.accept_legal({key: True for key in blank}, "Synthetic operator")


class SyntheticVaultTests(unittest.TestCase):
    def test_plaintext_state_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "charttrace-state.json"
            state_path.write_text(json.dumps({"schema_version": 1, "cases": []}), encoding="utf-8")
            with self.assertRaises(PermissionError):
                ChartTraceController(data_dir=Path(directory))

    def test_wrong_secret_cannot_unlock_authenticated_synthetic_vault(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            original = ChartTraceController(data_dir=data_dir)
            original.unlock("correct-secret", "Synthetic operator")
            created = original.create_case("Synthetic vault test")
            original.lock()
            wrong = ChartTraceController(data_dir=data_dir)
            with self.assertRaises(ApplicationLockedError):
                wrong.unlock("wrong-secret", "Synthetic operator")
            self.assertFalse(wrong.unlocked)
            restored = ChartTraceController(data_dir=data_dir)
            restored.unlock("correct-secret", "Synthetic operator")
            self.assertEqual(created.case_id, restored.list_cases()[0].case_id)
            envelope_text = (data_dir / "charttrace-state.json").read_text(encoding="utf-8")
            self.assertNotIn("Synthetic vault test", envelope_text)
            envelope = json.loads(envelope_text)
            self.assertFalse(envelope["production_crypto"])
            self.assertEqual("authenticated-obfuscation-not-production-encryption", envelope["security_model"])

    def test_tampered_vault_payload_cannot_unlock(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            controller = ChartTraceController(data_dir=data_dir)
            controller.unlock("correct-secret", "Synthetic operator")
            controller.lock()
            state_path = data_dir / "charttrace-state.json"
            envelope = json.loads(state_path.read_text(encoding="utf-8"))
            payload = envelope["payload_b64"]
            envelope["payload_b64"] = ("A" if payload[0] != "A" else "B") + payload[1:]
            state_path.write_text(json.dumps(envelope), encoding="utf-8")
            restored = ChartTraceController(data_dir=data_dir)
            with self.assertRaises(ApplicationLockedError):
                restored.unlock("correct-secret", "Synthetic operator")


class CounselAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.controller = ChartTraceController(persist=False)
        self.controller.unlock("synthetic-secret", "Synthetic operator")
        accept_current_terms(self.controller)
        self.case = self.controller.create_case("Synthetic counsel test")

    def _advance_to_human_review(self):
        self.controller.secure_ingest(self.case.case_id, [("source.txt", b"synthetic")])
        self.controller.run_peer_analysis(self.case.case_id)
        self.controller.complete_internal_qa(self.case.case_id)
        self.assertEqual(CaseLifecycle.HUMAN_RELEASE_REVIEW, self.case.lifecycle)

    def test_unsigned_counsel_approval_is_non_authoritative(self):
        self._advance_to_human_review()
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "review.json"
            bundle.write_text(json.dumps({
                "mode": "offline_counsel_review", "case_id": self.case.case_id,
                "reviewed_by": "Reported reviewer", "decision": "approve",
            }), encoding="utf-8")
            imported = self.controller.import_offline_counsel_review(self.case.case_id, bundle)
        self.assertFalse(imported["authoritative"])
        self.assertEqual("unsigned", imported["signature_state"])
        self.assertEqual("approve", imported["reported_decision"])
        self.assertEqual(CaseLifecycle.HUMAN_RELEASE_REVIEW, self.case.lifecycle)
        self.assertIsNone(self.case.human_reviewed_by)

    def test_unsigned_bundle_cannot_self_assert_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "review.json"
            bundle.write_text(json.dumps({
                "mode": "offline_counsel_review", "case_id": self.case.case_id,
                "reviewed_by": "Self asserted", "decision": "approve",
                "approved": True, "authoritative": True,
            }), encoding="utf-8")
            with self.assertRaises(CounselImportError):
                self.controller.import_offline_counsel_review(self.case.case_id, bundle)

    def test_authority_hold_and_terms_change_revoke_transfer(self):
        self.controller.set_recipient(self.case.case_id, "Synthetic recipient", "attorney")
        self.controller.authorize_recipient_transfer(self.case.case_id, True, "Synthetic operator")
        first_acceptance = self.controller.consent.acceptance_id
        self.assertEqual(LegalState.TRANSFER_AUTHORIZED, self.case.transfer_state)
        self.controller.place_authority_hold("Authority disputed")
        self.assertEqual(LegalState.TRANSFER_NOT_AUTHORIZED, self.case.transfer_state)
        self.controller.clear_authority_hold()
        accept_current_terms(self.controller)
        self.assertNotEqual(first_acceptance, self.controller.consent.acceptance_id)
        self.controller.authorize_recipient_transfer(self.case.case_id, True, "Synthetic operator")
        self.controller.require_terms_reacceptance("Instrument changed")
        self.assertEqual(LegalState.TRANSFER_NOT_AUTHORIZED, self.case.transfer_state)
        self.assertEqual(LegalState.REACCEPT_REQUIRED, self.controller.legal_state)

    def test_consent_ledger_itself_revokes_transfer_on_legal_change(self):
        ledger = ConsentLedger()
        blank = ledger.blank_acknowledgements()
        ledger.accept({key: True for key in blank}, "Synthetic operator")
        ledger.set_recipient("Synthetic recipient", "attorney")
        ledger.authorize_transfer(True, "Synthetic operator")
        self.assertEqual(LegalState.TRANSFER_AUTHORIZED, ledger.transfer_state)
        ledger.place_authority_hold("Authority changed")
        self.assertEqual(LegalState.TRANSFER_NOT_AUTHORIZED, ledger.transfer_state)


class JsonIpcTests(unittest.TestCase):
    def test_json_codec_rejects_unsafe_or_ambiguous_payloads(self):
        self.assertEqual({"type": "ping"}, decode_json_message(b'{"type":"ping"}'))
        self.assertEqual(b'{"ok":true}', encode_json_message({"ok": True}))
        for payload in (
            b"\x80\x04unsafe-object", b'{"duplicate":1,"duplicate":2}',
            b'{"value":NaN}', b'["not-an-object"]',
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(JsonIpcError):
                    decode_json_message(payload)

    def test_product_ipc_is_retired_and_excluded(self):
        source = Path(__file__).with_name("ipc.py").read_text(encoding="utf-8")
        self.assertNotIn("multiprocessing", source)
        self.assertNotIn("import pickle", source)
        self.assertFalse(PRODUCT_IPC_ENABLED)
        self.assertIn("DISABLED_NOT_PRODUCT", source)
        with self.assertRaises(IpcDisabledError):
            LocalIpcServer("json-ipc-test")

    def test_retired_ipc_has_no_product_call_site(self):
        roots = [
            Path(__file__).with_name("controller.py"),
            Path(__file__).with_name("secure_controller.py"),
            Path(__file__).parents[1] / "launcher.py",
            Path(__file__).parents[1] / "ui" / "tk_app.py",
        ]
        for path in roots:
            self.assertNotIn("charttrace.app.ipc", path.read_text(encoding="utf-8"))


class LocalPathBoundaryTests(unittest.TestCase):
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

    def test_unc_and_uri_paths_are_rejected(self):
        for path in (r"\\server\share\record.pdf", "//server/share/record.pdf", "file://server/share/record.pdf", "https://example.invalid/record.pdf"):
            with self.subTest(path=path):
                with self.assertRaises(PathBoundaryError):
                    validate_local_file(path)

    def test_symlink_or_junction_source_and_output_parent_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "real-source"
            source_dir.mkdir()
            source = source_dir / "source.txt"
            source.write_bytes(b"synthetic")
            source_link = root / "source-link"
            self._link_directory(source_link, source_dir)
            with self.assertRaises(PathBoundaryError):
                seal_sources([source_link / "source.txt"])
            real_output = root / "real-output"
            real_output.mkdir()
            output_link = root / "output-link"
            self._link_directory(output_link, real_output)
            with self.assertRaises(PathBoundaryError):
                validate_local_output_path(output_link / "release.json")


class PackagingTruthTests(unittest.TestCase):
    def test_unsigned_package_metadata_cannot_claim_release_or_crypto(self):
        package_root = Path(__file__).parents[1] / "packaging"
        manifest = json.loads((package_root / "build_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("UNSIGNED_SYNTHETIC", manifest["artifact_label"])
        self.assertEqual("unsigned", manifest["signing_state"])
        self.assertEqual("source-config-only-not-built", manifest["package_state"])
        self.assertFalse(manifest["clean_vm_verified"])
        self.assertFalse(manifest["production_distribution_authorized"])
        self.assertFalse(manifest["production_crypto"])
        self.assertFalse(manifest["synthetic_released"])
        installer = (package_root / "ChartTrace.iss").read_text(encoding="utf-8")
        self.assertIn("SignedUninstaller=no", installer)
        self.assertNotIn("SignTool=", installer)
        build_script = (package_root / "build_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("pip install", build_script)
        self.assertIn("Pinned PyInstaller", build_script)
        self.assertIn("Get-AuthenticodeSignature", build_script)


if __name__ == "__main__":
    unittest.main()

