import unittest

from charttrace.storage.vault_contract import (
    ArtifactKind,
    VaultArtifact,
    derivative_manifest,
    exact_original_manifest,
    validate_case_manifest,
    verify_exact_bytes,
)


class VaultContractTests(unittest.TestCase):
    def test_original_bytes_are_exact_and_read_only(self) -> None:
        content = b"synthetic document bytes"
        artifact = exact_original_manifest("original-01", "case-01", content)
        self.assertEqual(artifact.kind, ArtifactKind.ORIGINAL)
        self.assertTrue(artifact.read_only)
        verify_exact_bytes(artifact, content)
        with self.assertRaises(ValueError):
            verify_exact_bytes(artifact, content + b"!")

    def test_derivative_is_separate_and_bound_to_original(self) -> None:
        original = exact_original_manifest("original-01", "case-01", b"synthetic original")
        derivative = derivative_manifest("ocr-01", "case-01", b"synthetic derivative", original)
        self.assertEqual(derivative.source_sha256, original.sha256)
        validate_case_manifest((original, derivative))
        with self.assertRaises(ValueError):
            derivative_manifest("ocr-02", "case-02", b"other", original)

    def test_unencrypted_or_writable_artifact_fails_closed(self) -> None:
        base = dict(
            artifact_id="original-01", case_id="case-01", kind=ArtifactKind.ORIGINAL,
            sha256="d" * 64, byte_length=1, source_sha256=None,
        )
        with self.assertRaises(ValueError):
            VaultArtifact(encryption_state="PLAINTEXT", read_only=True, **base)
        with self.assertRaises(ValueError):
            VaultArtifact(encryption_state="CALLER_VERIFIED_ENCRYPTED", read_only=False, **base)

    def test_manifest_cannot_cross_cases_or_orphan_derivative(self) -> None:
        first = exact_original_manifest("original-01", "case-01", b"one")
        other = exact_original_manifest("original-02", "case-02", b"two")
        with self.assertRaises(ValueError):
            validate_case_manifest((first, other))
        orphan = VaultArtifact(
            artifact_id="ocr-01", case_id="case-01", kind=ArtifactKind.DERIVATIVE,
            sha256="e" * 64, byte_length=3, source_sha256="f" * 64,
            encryption_state="CALLER_VERIFIED_ENCRYPTED", read_only=True,
        )
        with self.assertRaises(ValueError):
            validate_case_manifest((first, orphan))


if __name__ == "__main__":
    unittest.main()
