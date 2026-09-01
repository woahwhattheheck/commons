import json
from pathlib import Path
import tempfile
import unittest

from charttrace.storage.vault import (
    PUBLIC_TCP_LISTENER,
    VAULT_NETWORK_POLICY,
    VAULT_SECURITY_LABEL,
    VAULT_SIGNATURE_STATE,
    LocalCaseVault,
    VaultIntegrityError,
    VaultLockedError,
)


class LocalCaseVaultTests(unittest.TestCase):
    def test_wrapped_case_key_authenticated_encryption_and_truthful_label(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "vault"
            plaintext = b"SYNTH-CASE-001 synthetic evidence only"
            vault = LocalCaseVault.create(
                root,
                case_id="SYNTH-CASE-001",
                unlock_secret="synthetic-local-secret",
            )
            sealed = vault.seal_bytes("originals/SYNTH-DOC-001.pdf", plaintext)
            metadata = json.loads((root / "vault.json").read_text("ascii"))

            self.assertEqual(metadata["security_label"], VAULT_SECURITY_LABEL)
            self.assertEqual(metadata["signature_state"], VAULT_SIGNATURE_STATE)
            self.assertEqual(metadata["network_policy"], VAULT_NETWORK_POLICY)
            self.assertIs(metadata["public_tcp_listener"], PUBLIC_TCP_LISTENER)
            self.assertIn("wrapped_case_key", metadata)
            self.assertNotIn(b"synthetic-local-secret", (root / "vault.json").read_bytes())
            self.assertNotIn(plaintext, sealed.read_bytes())
            self.assertEqual(
                vault.open_bytes("originals/SYNTH-DOC-001.pdf"), plaintext
            )
            vault.lock()
            with self.assertRaises(VaultLockedError):
                vault.open_bytes("originals/SYNTH-DOC-001.pdf")

            reopened = LocalCaseVault.unlock(
                root, unlock_secret="synthetic-local-secret"
            )
            self.assertEqual(
                reopened.open_bytes("originals/SYNTH-DOC-001.pdf"), plaintext
            )

    def test_wrong_secret_and_modified_ciphertext_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "vault"
            vault = LocalCaseVault.create(
                root,
                case_id="SYNTH-CASE-001",
                unlock_secret=b"correct-synthetic-secret",
            )
            sealed = vault.seal_bytes("evidence.json", b'{"synthetic":true}')
            vault.lock()
            with self.assertRaises(VaultIntegrityError):
                LocalCaseVault.unlock(
                    root, unlock_secret=b"wrong-synthetic-secret"
                )

            reopened = LocalCaseVault.unlock(
                root, unlock_secret=b"correct-synthetic-secret"
            )
            changed = bytearray(sealed.read_bytes())
            changed[-33] ^= 1
            sealed.write_bytes(changed)
            with self.assertRaises(VaultIntegrityError):
                reopened.open_bytes("evidence.json")

    def test_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            vault = LocalCaseVault.create(
                Path(temporary) / "vault",
                case_id="SYNTH-CASE-001",
                unlock_secret="synthetic-local-secret",
            )
            with self.assertRaises(ValueError):
                vault.seal_bytes("../outside", b"synthetic")


if __name__ == "__main__":
    unittest.main()
