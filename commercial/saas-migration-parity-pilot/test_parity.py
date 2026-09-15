from __future__ import annotations

import copy
import contextlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import parity  # noqa: E402
import secure_io  # noqa: E402
import synthetic_fixture  # noqa: E402

FIXTURE_RAW = synthetic_fixture.fixture_bytes()


def fixture_obj():
    return parity.loads_strict(FIXTURE_RAW)


def raw_of(obj):
    return parity.canonical_bytes(obj)


class CompileTests(unittest.TestCase):
    def test_golden_fixture_counts_and_offer(self):
        report, markdown = parity.compile_bytes(FIXTURE_RAW)
        self.assertEqual(report["summary"]["union_key_count"], 505)
        self.assertEqual(report["summary"]["counts"], {
            "PARITY": 490,
            "MISSING_TARGET": 5,
            "UNEXPECTED_TARGET": 5,
            "FIELD_MISMATCH": 5,
            "STALE_EVIDENCE": 0,
            "DUPLICATE_KEY": 0,
            "INVALID_EVIDENCE": 0,
        })
        self.assertEqual(report["offer"]["diagnostic_price_usd_cents"], 500_000)
        self.assertEqual(report["offer"]["optional_integration_sprint_usd_cents"], 1_000_000)
        self.assertFalse(report["offer"]["custom_adapter_included"])
        self.assertIn("$5,000", markdown)
        self.assertIn("$10,000", markdown)

    def test_authority_is_all_false(self):
        report, _ = parity.compile_bytes(FIXTURE_RAW)
        self.assertTrue(report["authority"])
        self.assertTrue(all(value is False for value in report["authority"].values()))

    def test_row_projection_does_not_leak_raw_ids_or_values(self):
        report, markdown = parity.compile_bytes(FIXTURE_RAW)
        encoded_rows = parity.canonical_bytes(report["rows"])
        self.assertNotIn(b"R0001", encoded_rows)
        self.assertNotIn(b"Customer 0001", encoded_rows)
        self.assertNotIn(b"Customer 0491", encoded_rows)
        self.assertNotIn("R0001", markdown)
        mismatch = next(r for r in report["rows"] if r["classification"] == "FIELD_MISMATCH")
        self.assertIn("source_value_sha256", mismatch["mismatch_fields"][0])
        self.assertIn("target_value_sha256", mismatch["mismatch_fields"][0])

    def test_record_order_changes_raw_digest_not_semantics(self):
        obj = fixture_obj()
        report_a, _ = parity.compile_bytes(raw_of(obj))
        obj["source_snapshot"]["records"].reverse()
        obj["target_snapshot"]["records"].reverse()
        report_b, _ = parity.compile_bytes(raw_of(obj))
        self.assertNotEqual(report_a["input"]["raw_input_sha256"], report_b["input"]["raw_input_sha256"])
        self.assertEqual(report_a["input"]["semantic_manifest_sha256"], report_b["input"]["semantic_manifest_sha256"])
        self.assertEqual(report_a["summary"], report_b["summary"])
        self.assertEqual(report_a["rows"], report_b["rows"])

    def test_whitespace_changes_raw_digest_not_semantic_digest(self):
        obj = fixture_obj()
        compact = raw_of(obj)
        pretty = (json.dumps(obj, sort_keys=True, indent=2) + "\n").encode()
        a, _ = parity.compile_bytes(compact)
        b, _ = parity.compile_bytes(pretty)
        self.assertNotEqual(a["input"]["raw_input_sha256"], b["input"]["raw_input_sha256"])
        self.assertEqual(a["input"]["semantic_manifest_sha256"], b["input"]["semantic_manifest_sha256"])

    def test_duplicate_source_key_is_hold(self):
        obj = fixture_obj()
        src = obj["source_snapshot"]["records"]
        src[-1] = copy.deepcopy(src[0])
        report, _ = parity.compile_bytes(raw_of(obj))
        self.assertGreaterEqual(report["summary"]["counts"]["DUPLICATE_KEY"], 1)
        self.assertTrue(any("DUPLICATE_SOURCE_KEY" in r["reason_codes"] for r in report["rows"]))

    def test_duplicate_target_key_is_hold(self):
        obj = fixture_obj()
        dst = obj["target_snapshot"]["records"]
        dst[-1] = copy.deepcopy(dst[0])
        report, _ = parity.compile_bytes(raw_of(obj))
        self.assertGreaterEqual(report["summary"]["counts"]["DUPLICATE_KEY"], 1)
        self.assertTrue(any("DUPLICATE_TARGET_KEY" in r["reason_codes"] for r in report["rows"]))

    def test_incomplete_snapshot_marks_rows_invalid(self):
        obj = fixture_obj()
        obj["target_snapshot"]["complete"] = False
        report, _ = parity.compile_bytes(raw_of(obj))
        self.assertEqual(report["summary"]["counts"]["INVALID_EVIDENCE"], 505)
        self.assertEqual(report["summary"]["diagnostic_state"], "DIFFERENCES_OR_HOLDS_FOUND")

    def test_missing_mapped_field_is_invalid_evidence(self):
        obj = fixture_obj()
        del obj["target_snapshot"]["records"][0]["fields"]["name"]
        report, _ = parity.compile_bytes(raw_of(obj))
        self.assertGreaterEqual(report["summary"]["counts"]["INVALID_EVIDENCE"], 1)
        self.assertTrue(any("MAPPED_FIELD_MISSING_OR_WRONG_TYPE" in r["reason_codes"] for r in report["rows"]))

    def test_bool_does_not_alias_integer(self):
        obj = fixture_obj()
        obj["target_snapshot"]["records"][0]["fields"]["balance_cents"] = True
        report, _ = parity.compile_bytes(raw_of(obj))
        self.assertGreaterEqual(report["summary"]["counts"]["INVALID_EVIDENCE"], 1)

    def test_age_exact_boundary_fresh_and_plus_one_stale(self):
        obj = fixture_obj()
        obj["max_snapshot_age_seconds"] = 86400
        obj["source_snapshot"]["captured_at_utc"] = "2026-09-14T18:00:00Z"
        obj["target_snapshot"]["captured_at_utc"] = "2026-09-14T18:00:00Z"
        at_boundary, _ = parity.compile_bytes(raw_of(obj))
        self.assertEqual(at_boundary["summary"]["counts"]["STALE_EVIDENCE"], 0)
        obj["source_snapshot"]["captured_at_utc"] = "2026-09-14T17:59:59Z"
        stale, _ = parity.compile_bytes(raw_of(obj))
        self.assertEqual(stale["summary"]["counts"]["STALE_EVIDENCE"], 505)

    def test_future_snapshot_is_stale_not_fresh(self):
        obj = fixture_obj()
        obj["target_snapshot"]["captured_at_utc"] = "2026-09-15T18:00:01Z"
        report, _ = parity.compile_bytes(raw_of(obj))
        self.assertEqual(report["summary"]["counts"]["STALE_EVIDENCE"], 505)
        self.assertFalse(report["target_snapshot"]["fresh_at_cutover"])

    def test_all_parity_can_confirm_only_equal_complete_fresh_sets(self):
        obj = fixture_obj()
        # Restrict both sides to the same 490 records and remove intentional mismatches.
        obj["source_snapshot"]["records"] = obj["source_snapshot"]["records"][:490]
        obj["target_snapshot"]["records"] = obj["target_snapshot"]["records"][:490]
        report, _ = parity.compile_bytes(raw_of(obj))
        self.assertEqual(report["summary"]["counts"]["PARITY"], 490)
        self.assertEqual(report["summary"]["diagnostic_state"], "PARITY_CONFIRMED")


class StrictSchemaTests(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        raw = b'{"schema":"a","schema":"b"}'
        with self.assertRaises(parity.ParityError):
            parity.loads_strict(raw)

    def test_float_and_nonfinite_rejected(self):
        with self.assertRaises(parity.ParityError):
            parity.loads_strict(b'{"x":1.25}')
        with self.assertRaises(parity.ParityError):
            parity.loads_strict(b'{"x":NaN}')

    def test_unknown_top_level_key_rejected(self):
        obj = fixture_obj()
        obj["caller_pass"] = True
        with self.assertRaises(parity.ParityError):
            parity.compile_bytes(raw_of(obj))

    def test_over_500_records_rejected(self):
        obj = fixture_obj()
        obj["source_snapshot"]["records"].append(copy.deepcopy(obj["source_snapshot"]["records"][0]))
        with self.assertRaises(parity.ParityError):
            parity.compile_bytes(raw_of(obj))

    def test_duplicate_mapping_field_rejected(self):
        obj = fixture_obj()
        obj["field_map"].append({"source":"amount_cents","target":"other","type":"integer"})
        with self.assertRaises(parity.ParityError):
            parity.compile_bytes(raw_of(obj))

    def test_boolean_key_mapping_rejected(self):
        obj = fixture_obj()
        obj["key_map"] = [{"source":"active","target":"enabled","type":"boolean"}]
        with self.assertRaises(parity.ParityError):
            parity.compile_bytes(raw_of(obj))

    def test_same_snapshot_identity_rejected(self):
        obj = fixture_obj()
        obj["target_snapshot"]["snapshot_id"] = obj["source_snapshot"]["snapshot_id"]
        with self.assertRaises(parity.ParityError):
            parity.compile_bytes(raw_of(obj))

    def test_invalid_key_field_becomes_invalid_evidence_without_raw_key(self):
        obj = fixture_obj()
        del obj["source_snapshot"]["records"][0]["fields"]["legacy_id"]
        report, _ = parity.compile_bytes(raw_of(obj))
        self.assertEqual(report["summary"]["source_invalid_key_records"], 1)
        row = next(r for r in report["rows"] if "INVALID_RECORD_KEY" in r["reason_codes"])
        self.assertRegex(row["key_commitment"], r"^[0-9a-f]{64}$")


class VerificationTests(unittest.TestCase):
    def test_exact_canonical_report_verifies(self):
        input_raw = FIXTURE_RAW
        report, _ = parity.compile_bytes(input_raw)
        ok, detail = parity.verify_bytes(input_raw, parity.canonical_bytes(report))
        self.assertTrue(ok)
        self.assertEqual(detail, report["receipt"]["report_core_sha256"])

    def test_report_tamper_fails_verification(self):
        input_raw = FIXTURE_RAW
        report, _ = parity.compile_bytes(input_raw)
        report["summary"]["counts"]["PARITY"] += 1
        ok, _ = parity.verify_bytes(input_raw, parity.canonical_bytes(report))
        self.assertFalse(ok)

    def test_noncanonical_report_bytes_fail_verification(self):
        input_raw = FIXTURE_RAW
        report, _ = parity.compile_bytes(input_raw)
        pretty = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
        ok, _ = parity.verify_bytes(input_raw, pretty)
        self.assertFalse(ok)

    def test_markdown_is_deterministic(self):
        report, md_a = parity.compile_bytes(FIXTURE_RAW)
        md_b = parity.render_markdown(report)
        self.assertEqual(md_a, md_b)
        self.assertIn("does **not** mutate either SaaS system", md_a)


class FileAndCliTests(unittest.TestCase):
    def test_input_directory_and_final_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            with self.assertRaises(parity.ParityError):
                secure_io.read_bounded_regular(td, parity.MAX_INPUT_BYTES)
            real = td / "real.json"
            real.write_bytes(FIXTURE_RAW)
            link = td / "link.json"
            try:
                link.symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unsupported")
            with self.assertRaises(parity.ParityError):
                secure_io.read_bounded_regular(link, parity.MAX_INPUT_BYTES)

    def test_symlink_ancestor_is_rejected_for_input_and_output(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "real"
            real.mkdir()
            (real / "input.json").write_bytes(FIXTURE_RAW)
            link = td / "link"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unsupported")
            with self.assertRaises(parity.ParityError):
                secure_io.read_bounded_regular(link / "input.json", parity.MAX_INPUT_BYTES)
            with self.assertRaises(parity.ParityError):
                secure_io.write_pair_exclusive(link / "report.json", b"json", link / "report.md", b"md")
            self.assertFalse((real / "report.json").exists())
            self.assertFalse((real / "report.md").exists())

    def test_parent_replacement_cannot_redirect_publication_or_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            parent = td / "out"
            held = td / "held"
            parent.mkdir()
            calls = 0
            original = secure_io._write_all

            def swapping_write(fd, data):
                nonlocal calls
                original(fd, data)
                calls += 1
                if calls == 1:
                    parent.rename(held)
                    parent.mkdir()
                    (parent / "foreign.txt").write_text("foreign", encoding="utf-8")

            with mock.patch.object(secure_io, "_write_all", side_effect=swapping_write):
                with self.assertRaises(parity.ParityError):
                    secure_io.write_pair_exclusive(parent / "report.json", b"json", parent / "report.md", b"md")
            self.assertEqual((parent / "foreign.txt").read_text(), "foreign")
            self.assertFalse((parent / "report.json").exists())
            self.assertFalse((parent / "report.md").exists())
            self.assertFalse((held / "report.json").exists())
            self.assertFalse((held / "report.md").exists())

    def test_output_overwrite_refused_and_sentinel_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            first = td / "report.json"
            second = td / "report.md"
            first.write_text("sentinel", encoding="utf-8")
            with self.assertRaises(parity.ParityError):
                secure_io.write_pair_exclusive(first, b"new", second, b"md")
            self.assertEqual(first.read_text(), "sentinel")
            self.assertFalse(second.exists())

    def test_output_final_symlink_refused_and_target_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            target = td / "target.txt"
            target.write_text("sentinel", encoding="utf-8")
            link = td / "report.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unsupported")
            md = td / "report.md"
            with self.assertRaises(parity.ParityError):
                secure_io.write_pair_exclusive(link, b"new", md, b"md")
            self.assertEqual(target.read_text(), "sentinel")
            self.assertFalse(md.exists())

    def test_cli_compile_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inp = td / "input.json"
            report = td / "report.json"
            md = td / "report.md"
            inp.write_bytes(FIXTURE_RAW)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = parity.cli(["compile", "--input", str(inp), "--report-json", str(report), "--report-md", str(md)])
            self.assertEqual(rc, 0)
            status = json.loads(out.getvalue())
            self.assertEqual(status["state"], "DIFFERENCES_OR_HOLDS_FOUND")
            self.assertFalse(status["network_calls_performed"])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = parity.cli(["verify", "--input", str(inp), "--report-json", str(report)])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(out.getvalue())["verified"])

    def test_cli_refuses_existing_second_output_without_leaving_first(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inp = td / "input.json"
            report = td / "report.json"
            md = td / "report.md"
            inp.write_bytes(FIXTURE_RAW)
            md.write_text("occupied", encoding="utf-8")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = parity.cli(["compile", "--input", str(inp), "--report-json", str(report), "--report-md", str(md)])
            self.assertEqual(rc, 2)
            self.assertFalse(report.exists())
            self.assertEqual(md.read_text(), "occupied")


if __name__ == "__main__":
    unittest.main()
