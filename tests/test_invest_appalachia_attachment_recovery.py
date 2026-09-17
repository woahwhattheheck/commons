import io
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import warnings
import zipfile

from opportunities.invest_appalachia_framer_lms import attachment_recovery as recovery
from opportunities.invest_appalachia_framer_lms.attachment_recovery import (
    AttachmentRecoveryError,
    SOURCE_URL,
    analyze_zip,
)


def make_zip(entries):
    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, payload in entries:
                archive.writestr(name, payload)
    return buffer.getvalue()


class AttachmentRecoveryTests(unittest.TestCase):
    def exact_zip(self):
        return make_zip([
            ("Attachment A - Functional Requirements.xlsx", b"A"),
            ("Attachment B - Selection Rubric.xlsx", b"B"),
            ("Attachment C - Budget Template.xlsx", b"C"),
            ("Attachment D - Optional Proposal Response Template.docx", b"D"),
        ])

    def test_exact_a_d_receipt_is_hashed_but_does_not_promote_authority(self):
        receipt = analyze_zip(self.exact_zip(), retrieved_at_utc="2026-09-17T07:00:00Z")
        self.assertEqual(receipt["source_url"], SOURCE_URL)
        self.assertEqual(receipt["attachment_labels_found"], ["A", "B", "C", "D"])
        self.assertEqual(receipt["missing_attachment_labels"], [])
        self.assertEqual(receipt["unexpected_members"], [])
        self.assertEqual(receipt["member_set_status"], "RECOVERED_EXACT_A_D_UNREVIEWED")
        self.assertEqual(len(receipt["members"]), 4)
        self.assertFalse(receipt["attachments_complete_authorized"])
        self.assertFalse(receipt["qualification_or_budget_promotion_authorized"])
        self.assertFalse(receipt["external_contact_or_submission_authorized"])
        self.assertEqual(len(receipt["zip_sha256"]), 64)
        self.assertEqual(len(receipt["receipt_sha256"]), 64)

    def test_receipt_is_deterministic_for_same_bytes_and_timestamp(self):
        data = self.exact_zip()
        left = analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")
        right = analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")
        self.assertEqual(left, right)
        json.dumps(left, sort_keys=True, allow_nan=False)

    def test_missing_attachment_holds(self):
        data = make_zip([
            ("Attachment A - Functional Requirements.xlsx", b"A"),
            ("Attachment B - Selection Rubric.xlsx", b"B"),
            ("Attachment C - Budget Template.xlsx", b"C"),
        ])
        receipt = analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")
        self.assertEqual(receipt["member_set_status"], "RECOVERED_MEMBER_SET_HOLD")
        self.assertEqual(receipt["missing_attachment_labels"], ["D"])

    def test_unexpected_regular_member_holds(self):
        data = make_zip([
            ("Attachment A.xlsx", b"A"),
            ("Attachment B.xlsx", b"B"),
            ("Attachment C.xlsx", b"C"),
            ("Attachment D.docx", b"D"),
            ("notes.txt", b"do not silently trust me"),
        ])
        receipt = analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")
        self.assertEqual(receipt["member_set_status"], "RECOVERED_MEMBER_SET_HOLD")
        self.assertEqual(receipt["unexpected_members"], ["notes.txt"])

    def test_duplicate_attachment_label_fails_closed(self):
        data = make_zip([
            ("Attachment A one.xlsx", b"A1"),
            ("Attachment A two.xlsx", b"A2"),
            ("Attachment B.xlsx", b"B"),
            ("Attachment C.xlsx", b"C"),
            ("Attachment D.docx", b"D"),
        ])
        with self.assertRaises(AttachmentRecoveryError):
            analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")

    def test_path_equivalent_duplicate_member_fails_closed(self):
        data = make_zip([
            ("notes.txt", b"one"),
            ("./notes.txt", b"two"),
            ("Attachment A.xlsx", b"A"),
            ("Attachment B.xlsx", b"B"),
            ("Attachment C.xlsx", b"C"),
            ("Attachment D.docx", b"D"),
        ])
        with self.assertRaisesRegex(AttachmentRecoveryError, "duplicate ZIP member path"):
            analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")

    def test_path_traversal_fails_closed(self):
        data = make_zip([
            ("../Attachment A.xlsx", b"A"),
            ("Attachment B.xlsx", b"B"),
            ("Attachment C.xlsx", b"C"),
            ("Attachment D.docx", b"D"),
        ])
        with self.assertRaises(AttachmentRecoveryError):
            analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")

    def test_unix_symlink_member_fails_closed(self):
        symlink = zipfile.ZipInfo("Attachment A.xlsx")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        data = make_zip([
            (symlink, b"target.xlsx"),
            ("Attachment B.xlsx", b"B"),
            ("Attachment C.xlsx", b"C"),
            ("Attachment D.docx", b"D"),
        ])
        with self.assertRaises(AttachmentRecoveryError):
            analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")

    def test_source_url_is_immutable(self):
        with self.assertRaises(AttachmentRecoveryError):
            analyze_zip(
                self.exact_zip(),
                retrieved_at_utc="2026-09-17T07:00:00Z",
                source_url="https://example.invalid/fake.zip",
            )

    def test_timestamp_must_be_real_exact_utc(self):
        for bad in (
            "2026-09-17",
            "2026-09-17T07:00:00+00:00",
            "2026-13-17T07:00:00Z",
            "2026-09-31T07:00:00Z",
            "2026-09-17T25:00:00Z",
            "",
            None,
        ):
            with self.subTest(bad=bad), self.assertRaises(AttachmentRecoveryError):
                analyze_zip(self.exact_zip(), retrieved_at_utc=bad)

    def test_member_count_is_bounded_before_payload_reads(self):
        data = self.exact_zip()
        with mock.patch.object(recovery, "MAX_REGULAR_MEMBERS", 3):
            with self.assertRaisesRegex(AttachmentRecoveryError, "too many regular members"):
                analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")

    def test_cumulative_uncompressed_size_is_bounded_before_payload_reads(self):
        data = make_zip([
            ("Attachment A.xlsx", b"AA"),
            ("Attachment B.xlsx", b"BB"),
            ("Attachment C.xlsx", b"CC"),
            ("Attachment D.docx", b"DD"),
        ])
        with mock.patch.object(recovery, "MAX_TOTAL_UNCOMPRESSED_BYTES", 7):
            with self.assertRaisesRegex(AttachmentRecoveryError, "cumulative uncompressed"):
                analyze_zip(data, retrieved_at_utc="2026-09-17T07:00:00Z")

    def test_existing_receipt_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zip_path = root / "official.zip"
            output = root / "receipt.json"
            zip_path.write_bytes(self.exact_zip())
            output.write_text("sentinel\n", encoding="utf-8")
            with self.assertRaises(AttachmentRecoveryError):
                recovery.main([
                    "--zip", str(zip_path),
                    "--retrieved-at-utc", "2026-09-17T07:00:00Z",
                    "--output", str(output),
                ])
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel\n")

    def test_non_zip_fails_closed(self):
        with self.assertRaises(AttachmentRecoveryError):
            analyze_zip(b"not a zip", retrieved_at_utc="2026-09-17T07:00:00Z")


if __name__ == "__main__":
    unittest.main()
