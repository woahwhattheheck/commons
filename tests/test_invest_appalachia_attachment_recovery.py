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
    PROVENANCE_LOCAL,
    PROVENANCE_OFFICIAL_FETCH,
    SOURCE_URL,
    analyze_zip,
    fetch_and_analyze_official_zip,
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

    def test_local_exact_a_d_is_explicitly_unverified_provenance(self):
        receipt = analyze_zip(self.exact_zip())
        self.assertEqual(receipt["schema"], "invest_appalachia_framer_lms.attachment_recovery_receipt.v2")
        self.assertEqual(receipt["provenance_mode"], PROVENANCE_LOCAL)
        self.assertIsNone(receipt["source_url"])
        self.assertIsNone(receipt["retrieved_at_utc"])
        self.assertEqual(receipt["attachment_labels_found"], ["A", "B", "C", "D"])
        self.assertEqual(receipt["missing_attachment_labels"], [])
        self.assertEqual(receipt["unexpected_members"], [])
        self.assertEqual(receipt["member_set_status"], "LOCAL_BYTES_EXACT_A_D_UNVERIFIED_PROVENANCE")
        self.assertEqual(len(receipt["members"]), 4)
        self.assertFalse(receipt["attachments_complete_authorized"])
        self.assertFalse(receipt["qualification_or_budget_promotion_authorized"])
        self.assertFalse(receipt["external_contact_or_submission_authorized"])
        self.assertEqual(len(receipt["zip_sha256"]), 64)
        self.assertEqual(len(receipt["receipt_sha256"]), 64)

    def test_local_receipt_is_deterministic_for_same_bytes(self):
        data = self.exact_zip()
        left = analyze_zip(data)
        right = analyze_zip(data)
        self.assertEqual(left, right)
        json.dumps(left, sort_keys=True, allow_nan=False)

    def test_missing_attachment_holds(self):
        data = make_zip([
            ("Attachment A - Functional Requirements.xlsx", b"A"),
            ("Attachment B - Selection Rubric.xlsx", b"B"),
            ("Attachment C - Budget Template.xlsx", b"C"),
        ])
        receipt = analyze_zip(data)
        self.assertEqual(receipt["member_set_status"], "LOCAL_BYTES_MEMBER_SET_HOLD")
        self.assertEqual(receipt["missing_attachment_labels"], ["D"])

    def test_unexpected_regular_member_holds(self):
        data = make_zip([
            ("Attachment A.xlsx", b"A"),
            ("Attachment B.xlsx", b"B"),
            ("Attachment C.xlsx", b"C"),
            ("Attachment D.docx", b"D"),
            ("notes.txt", b"do not silently trust me"),
        ])
        receipt = analyze_zip(data)
        self.assertEqual(receipt["member_set_status"], "LOCAL_BYTES_MEMBER_SET_HOLD")
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
            analyze_zip(data)

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
            analyze_zip(data)

    def test_path_traversal_fails_closed(self):
        data = make_zip([
            ("../Attachment A.xlsx", b"A"),
            ("Attachment B.xlsx", b"B"),
            ("Attachment C.xlsx", b"C"),
            ("Attachment D.docx", b"D"),
        ])
        with self.assertRaises(AttachmentRecoveryError):
            analyze_zip(data)

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
            analyze_zip(data)

    def test_local_api_rejects_caller_asserted_official_metadata(self):
        for kwargs in (
            {"source_url": SOURCE_URL},
            {"retrieved_at_utc": "2026-09-17T07:00:00Z"},
            {"source_url": SOURCE_URL, "retrieved_at_utc": "2026-09-17T07:00:00Z"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(
                AttachmentRecoveryError, "cannot assert official-source provenance"
            ):
                analyze_zip(self.exact_zip(), **kwargs)

    def test_successful_fetch_binds_exact_url_and_code_observed_time(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = SOURCE_URL
        response.read.return_value = self.exact_zip()
        with mock.patch.object(recovery.urllib.request, "urlopen", return_value=response) as urlopen, mock.patch.object(
            recovery, "_observed_utc_now", return_value="2026-09-17T07:31:02Z"
        ):
            receipt = fetch_and_analyze_official_zip(timeout_seconds=7.0)
        urlopen.assert_called_once()
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 7.0)
        self.assertEqual(receipt["provenance_mode"], PROVENANCE_OFFICIAL_FETCH)
        self.assertEqual(receipt["source_url"], SOURCE_URL)
        self.assertEqual(receipt["retrieved_at_utc"], "2026-09-17T07:31:02Z")
        self.assertEqual(receipt["member_set_status"], "OFFICIAL_FETCH_EXACT_A_D_UNREVIEWED")
        self.assertFalse(receipt["attachments_complete_authorized"])

    def test_fetch_redirect_fails_closed_before_official_receipt(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = "https://example.invalid/copied.zip"
        response.read.return_value = self.exact_zip()
        with mock.patch.object(recovery.urllib.request, "urlopen", return_value=response):
            with self.assertRaisesRegex(AttachmentRecoveryError, "unexpected redirect target"):
                fetch_and_analyze_official_zip()

    def test_timestamp_validator_rejects_impossible_or_noncanonical_utc(self):
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
                recovery._validate_retrieved_at(bad)

    def test_member_count_is_bounded_before_payload_reads(self):
        data = self.exact_zip()
        with mock.patch.object(recovery, "MAX_REGULAR_MEMBERS", 3):
            with self.assertRaisesRegex(AttachmentRecoveryError, "too many regular members"):
                analyze_zip(data)

    def test_cumulative_uncompressed_size_is_bounded_before_payload_reads(self):
        data = make_zip([
            ("Attachment A.xlsx", b"AA"),
            ("Attachment B.xlsx", b"BB"),
            ("Attachment C.xlsx", b"CC"),
            ("Attachment D.docx", b"DD"),
        ])
        with mock.patch.object(recovery, "MAX_TOTAL_UNCOMPRESSED_BYTES", 7):
            with self.assertRaisesRegex(AttachmentRecoveryError, "cumulative uncompressed"):
                analyze_zip(data)

    def test_existing_receipt_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zip_path = root / "local.zip"
            output = root / "receipt.json"
            zip_path.write_bytes(self.exact_zip())
            output.write_text("sentinel\n", encoding="utf-8")
            with self.assertRaises(AttachmentRecoveryError):
                recovery.main(["--zip", str(zip_path), "--output", str(output)])
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel\n")

    def test_write_failure_removes_own_partial_final_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zip_path = root / "local.zip"
            output = root / "receipt.json"
            zip_path.write_bytes(self.exact_zip())
            with mock.patch.object(recovery.os, "fsync", side_effect=OSError("synthetic fsync failure")):
                with self.assertRaisesRegex(AttachmentRecoveryError, "cannot write receipt"):
                    recovery.main(["--zip", str(zip_path), "--output", str(output)])
            self.assertFalse(output.exists())

    def test_non_zip_fails_closed(self):
        with self.assertRaises(AttachmentRecoveryError):
            analyze_zip(b"not a zip")


if __name__ == "__main__":
    unittest.main()
