"""Real-file JSONL and index integration regressions; no network or live ledgers."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parent / "host" / "lm_gtm_index.py"
SPEC = importlib.util.spec_from_file_location("lm_gtm_index_jsonl_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
idx = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(idx)


class JsonlUnicodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "records.jsonl"

    def roundtrip(self, rows: list[dict]) -> bytes:
        idx.write_jsonl(self.path, rows)
        before = self.path.read_bytes()
        self.assertEqual(idx.load_jsonl(self.path), rows)
        self.assertEqual(self.path.read_bytes(), before)
        return before

    def test_ascii_roundtrip(self) -> None:
        self.roundtrip([{"id": "one", "n": 3}, {"id": "two", "enabled": True}])

    def test_next_line_character_in_string(self) -> None:
        raw = self.roundtrip([{"body": "before\u0085after"}])
        self.assertIn("\u0085".encode("utf-8"), raw)

    def test_line_separator_in_string(self) -> None:
        raw = self.roundtrip([{"body": "before\u2028after"}])
        self.assertIn("\u2028".encode("utf-8"), raw)

    def test_paragraph_separator_in_string(self) -> None:
        raw = self.roundtrip([{"body": "before\u2029after"}])
        self.assertIn("\u2029".encode("utf-8"), raw)

    def test_separators_in_object_keys(self) -> None:
        self.roundtrip([{f"a{c}b": c for c in "\u0085\u2028\u2029"}])

    def test_nested_values_multiple_records(self) -> None:
        self.roundtrip([
            {"nested": [None, "\u2028", {"body": "a\u2029b\u0085c"}], "n": 1},
            {"body": "second record", "flags": [True, False]},
            {"body": "\u2029\u2028\u0085"},
        ])

    def test_control_characters_written_as_json_escapes(self) -> None:
        raw = self.roundtrip([{"body": "\n\r\v\f\t\x1c\x1d\x1e\x00"}])
        self.assertEqual(raw.count(b"\n"), 1)
        self.assertIn(b"\\n", raw)

    def test_ascii_escaped_separators_remain_accepted(self) -> None:
        rows = [{"body": "\u0085\u2028\u2029"}]
        self.path.write_text(json.dumps(rows[0], ensure_ascii=True) + "\n", encoding="utf-8")
        self.assertEqual(idx.load_jsonl(self.path), rows)

    def test_no_terminal_newline(self) -> None:
        self.path.write_text('{"body":"a\u2028b"}\n{"n":2}', encoding="utf-8")
        self.assertEqual(idx.load_jsonl(self.path), [{"body": "a\u2028b"}, {"n": 2}])

    def test_crlf_record_delimiters(self) -> None:
        self.path.write_bytes('{"body":"a\u2029b"}\r\n{"n":2}\r\n'.encode("utf-8"))
        self.assertEqual(idx.load_jsonl(self.path), [{"body": "a\u2029b"}, {"n": 2}])

    def test_existing_cr_translation_behavior_preserved(self) -> None:
        self.path.write_bytes(b'{"n":1}\r{"n":2}\r')
        self.assertEqual(idx.load_jsonl(self.path), [{"n": 1}, {"n": 2}])

    def test_blank_ascii_lines(self) -> None:
        self.path.write_text('\n \t\n{"n":1}\n\n{"n":2}\n', encoding="utf-8")
        self.assertEqual(idx.load_jsonl(self.path), [{"n": 1}, {"n": 2}])

    def test_missing_file(self) -> None:
        self.assertEqual(idx.load_jsonl(self.path), [])
        self.assertFalse(self.path.exists())

    def test_empty_file(self) -> None:
        self.path.write_bytes(b"")
        self.assertEqual(idx.load_jsonl(self.path), [])

    def test_whitespace_only_file(self) -> None:
        self.path.write_bytes(b" \t\r\n\n")
        self.assertEqual(idx.load_jsonl(self.path), [])

    def test_empty_writer_output(self) -> None:
        self.roundtrip([])
        self.assertEqual(self.path.read_bytes(), b"")

    def test_writer_creates_parent_directories(self) -> None:
        self.path = self.root / "a" / "b" / "records.jsonl"
        self.roundtrip([{"body": "nested\u0085directory"}])

    def test_malformed_record_reports_physical_line(self) -> None:
        self.path.write_text('{"body":"a\u2028b\u2029c\u0085d"}\n\n{"bad":}\n', encoding="utf-8")
        with self.assertRaises(idx.IndexError_) as caught:
            idx.load_jsonl(self.path)
        self.assertIn(f"{self.path}:3 is not JSONL:", str(caught.exception))
        self.assertIsInstance(caught.exception.__cause__, json.JSONDecodeError)

    def test_nonobject_reports_physical_line(self) -> None:
        self.path.write_text('{"body":"a\u2029b"}\n[1,2]\n', encoding="utf-8")
        with self.assertRaises(idx.IndexError_) as caught:
            idx.load_jsonl(self.path)
        self.assertEqual(str(caught.exception), f"{self.path}:2 must be a JSON object")

    def test_unicode_separator_is_not_a_record_delimiter(self) -> None:
        for separator in "\u0085\u2028\u2029":
            with self.subTest(separator=hex(ord(separator))):
                self.path.write_text('{"n":1}' + separator + '{"n":2}\n', encoding="utf-8")
                with self.assertRaises(idx.IndexError_):
                    idx.load_jsonl(self.path)

    def test_raw_json_control_is_not_a_record_delimiter(self) -> None:
        for separator in "\v\f\x1c\x1d\x1e":
            with self.subTest(separator=hex(ord(separator))):
                self.path.write_text('{"n":1}' + separator + '{"n":2}\n', encoding="utf-8")
                with self.assertRaises(idx.IndexError_):
                    idx.load_jsonl(self.path)

    def test_invalid_json_does_not_change_file(self) -> None:
        self.path.write_text('{"n":1}\n{"bad":}\n', encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(idx.IndexError_):
            idx.load_jsonl(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_utf8_bom_rejection_preserved(self) -> None:
        self.path.write_bytes(b'\xef\xbb\xbf{"n":1}\n')
        with self.assertRaises(idx.IndexError_):
            idx.load_jsonl(self.path)

    def test_invalid_utf8_behavior_preserved(self) -> None:
        self.path.write_bytes(b'{"body":"\xff"}\n')
        with self.assertRaises(UnicodeDecodeError):
            idx.load_jsonl(self.path)

    def test_emit_jsonl_is_readable(self) -> None:
        rows = [{"body": "emitted\u2028text"}, {"n": 2}]
        self.path.write_text(idx.emit_jsonl(rows), encoding="utf-8")
        self.assertEqual(idx.load_jsonl(self.path), rows)

    def test_unicode_scalar_sweep_roundtrip(self) -> None:
        # Every Unicode scalar value, including noncharacters. Surrogates are
        # excluded because standalone surrogate code points are not UTF-8.
        chars = "".join(chr(n) for n in range(0x110000) if not 0xD800 <= n <= 0xDFFF)
        self.assertEqual(len(chars), 1112064)
        rows = [{"start": start, "text": chars[start:start + 4096]}
                for start in range(0, len(chars), 4096)]
        self.roundtrip(rows)


class IndexUnicodeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = idx.default_paths(self.root)
        stamp = "2026-09-08T00:00:00Z"
        sources = {
            "loop": {
                "schema_version": "commons-website-people-email-book/v2",
                "generated_at": stamp,
                "prospects": [{"prospect_id": "unicode-fixture", "organization": "Test fixture",
                               "decision": "READY_TO_DRAFT", "next_action": "local fixture"}],
                "seller_contacts": [],
                "truth": {"calls_booked": 0, "mailbox": "NEEDS_OWNER_MAILBOX"},
            },
            "candidates": {"generated_at": stamp, "prospects": []},
            "funnel": {"measured_at": stamp, "contacts": []},
            "pipeline": {"observed_at": stamp, "current": {"research_entities": 0}},
            "inboxes": {"measured_at": stamp, "transport": {"state": "TEST_ONLY"}},
        }
        for key, value in sources.items():
            self.paths[key].parent.mkdir(parents=True, exist_ok=True)
            self.paths[key].write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
        self.paths["receipts"].mkdir(parents=True)
        idx.write_index(self.paths)
        self.source_bytes = {key: self.paths[key].read_bytes() for key in sources}

    def assert_sources_unchanged(self) -> None:
        for key, payload in self.source_bytes.items():
            self.assertEqual(self.paths[key].read_bytes(), payload, key)

    def test_append_unicode_note_then_rebuild_and_validate(self) -> None:
        body = "First\u2028second\u2029third\u0085fourth"
        result = idx.append_event(subject_id="unicode-fixture", event_id="unicode-event-one",
                                  body=body, speaker="TEST", ts="2026-09-08T01:00:00Z",
                                  paths=self.paths)
        self.assertEqual(result["event"]["body"], body)
        self.assertEqual(idx.load_events(self.paths)[0]["body"], body)
        self.assertEqual(idx.validate_index(self.paths)["events"][0]["body"], body)
        idx.append_event(subject_id="unicode-fixture", event_id="unicode-event-two",
                         body="Next local note", speaker="TEST", ts="2026-09-08T02:00:00Z",
                         paths=self.paths)
        built = idx.validate_index(self.paths)
        self.assertEqual([e["id"] for e in built["events"]], ["unicode-event-one", "unicode-event-two"])
        self.assertEqual(built["state"]["truth"]["overlay_events"], 2)
        self.assertEqual(built["state"]["truth"]["transport_actions"], 0)
        self.assertEqual(built["state"]["truth"]["cash_usd"], 0)
        self.assert_sources_unchanged()

    def test_existing_unicode_status_propagates_without_normalization(self) -> None:
        action = "Review\u2028local\u2029fixture\u0085only"
        event = {"schema_version": idx.SCHEMA_VERSION, "kind": idx.KIND_EVENT,
                 "id": "unicode-status-one", "subject_id": "unicode-fixture",
                 "ts": "2026-09-08T01:00:00Z", "type": "STATUS", "cash_usd": 0,
                 "transport": "NONE", "next_action": action}
        idx.write_jsonl(self.paths["events"], [event])
        built = idx.write_index(self.paths)
        self.assertEqual(idx.show_subject("unicode-fixture", self.paths)["next_action"], action)
        self.assertEqual(idx.validate_index(self.paths)["rows"], built["rows"])
        self.assertEqual(idx.load_jsonl(self.paths["index"])[1]["next_action"], action)
        self.assert_sources_unchanged()

    def test_freshness_reads_header_when_unicode_exists_in_later_row(self) -> None:
        stamp = "2026-09-08T01:00:00Z"
        idx.write_jsonl(self.paths["index"], [
            {"kind": idx.KIND_HEADER, "composed_at": stamp},
            {"kind": idx.KIND_ROW, "body": "a\u2028b\u2029c\u0085d"},
        ])
        self.assertEqual(idx.read_committed_composed_at(self.paths), stamp)
        result = idx.composed_at_freshness(self.paths, now=dt.datetime(2026, 9, 8, 2, tzinfo=dt.timezone.utc))
        self.assertEqual(result["status"], "FRESH")
        self.assertEqual(result["age_hours"], 1.0)
        self.assert_sources_unchanged()

    def test_duplicate_event_id_remains_rejected(self) -> None:
        idx.append_event(subject_id="unicode-fixture", event_id="ascii-event-one",
                         body="Existing fixture note", paths=self.paths,
                         ts="2026-09-08T01:00:00Z")
        before = self.paths["events"].read_bytes()
        with self.assertRaises(idx.IndexError_):
            idx.append_event(subject_id="unicode-fixture", event_id="ascii-event-one",
                             body="Not appended", paths=self.paths,
                             ts="2026-09-08T02:00:00Z")
        self.assertEqual(self.paths["events"].read_bytes(), before)
        self.assert_sources_unchanged()


    def cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        script = self.root / "host" / "lm_gtm_index.py"
        script.parent.mkdir(exist_ok=True)
        shutil.copyfile(MODULE_PATH, script)
        return subprocess.run([sys.executable, "-B", str(script), *arguments],
                              cwd=self.root, capture_output=True, text=True,
                              encoding="utf-8", timeout=10, check=False)

    def test_cli_append_unicode_then_validate(self) -> None:
        body = "CLI\u2028note\u2029with\u0085separators"
        appended = self.cli("append-event", "--subject", "unicode-fixture",
                            "--id", "unicode-cli-event-one", "--body", body,
                            "--from", "TEST", "--ts", "2026-09-08T01:00:00Z")
        self.assertEqual(appended.returncode, 0, appended.stderr)
        self.assertEqual(json.loads(appended.stdout)["body"], body)
        checked = self.cli("validate")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn("1 overlay-events", checked.stdout)
        self.assert_sources_unchanged()

    def test_cli_freshness_unicode_later_row(self) -> None:
        idx.write_jsonl(self.paths["index"], [
            {"kind": idx.KIND_HEADER, "composed_at": "2026-09-08T01:00:00Z"},
            {"kind": idx.KIND_ROW, "body": "CLI\u2028row\u2029text"},
        ])
        checked = self.cli("freshness", "--as-of", "2026-09-08T02:00:00Z")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["status"], "FRESH")
        self.assert_sources_unchanged()

    def test_cli_malformed_record_preserves_saved_outputs(self) -> None:
        self.paths["events"].write_text('{"body":"a\u2028b"}\n\n{"bad":}\n', encoding="utf-8")
        before = {key: self.paths[key].read_bytes() for key in ("events", "index", "state")}
        checked = self.cli("snapshot")
        self.assertEqual(checked.returncode, 1)
        self.assertIn(f"{self.paths['events']}:3 is not JSONL:", checked.stderr)
        self.assertNotIn("Traceback", checked.stderr)
        self.assertEqual(checked.stdout, "")
        for key, payload in before.items():
            self.assertEqual(self.paths[key].read_bytes(), payload)
        self.assert_sources_unchanged()


if __name__ == "__main__":
    unittest.main(verbosity=2)
