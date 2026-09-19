"""Native-engine CLI acceptance plus process/stdin smoke; no fake persistence."""
from __future__ import annotations

import json
import contextlib
import io
import operate
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
OPT = ["-O"] if sys.flags.optimize else []


class OperatorCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "shift.sqlite3"
        self.call("init")

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, command, payload=None, *, code=0, raw=None, database=None, stdin=False, spawn=False):
        args = [sys.executable, *OPT, str(HERE / "operate.py"), str(database or self.db), command]
        data = raw if raw is not None else (None if payload is None else json.dumps(payload).encode())
        if data is not None:
            source = self.root / "input.json"
            source.write_bytes(data)
            args += ["--input", "-" if stdin else str(source)]
        if stdin or spawn:
            process = subprocess.run(args, input=data if stdin else None, capture_output=True, timeout=15)
            self.assertEqual(process.returncode, code, process.stderr.decode(errors="replace"))
            output = process.stdout if code == 0 else process.stderr
        else:
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result_code = operate.main(args[2 + len(OPT):])
            self.assertEqual(result_code, code, stderr.getvalue())
            output = stdout.getvalue() if code == 0 else stderr.getvalue()
        try:
            result = json.loads(output)
        except (ValueError, TypeError) as exc:
            raise AssertionError(f"command={command} output={output!r}") from exc
        self.assertTrue(all(v is False for v in result["authority"].values()))
        if data is not None:
            self.assertEqual((self.root / "input.json").read_bytes(), data)
        return result

    def count(self):
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def customer(self, name="Synthetic laundry account", op="customer-1"):
        return {"operation_key": op, "customer_id": "c1", "name": name}

    def prepare(self):
        self.call("customer", self.customer())
        self.call("site", {"operation_key": "site-1", "site_id": "s1", "customer_id": "c1", "name": "Synthetic site"})
        self.call("agreement", {"operation_key": "agreement-1", "agreement_id": "a1", "site_id": "s1",
            "item_code": "towel", "unit_price_cents": 95, "active_from": "2026-01-01"})
        self.call("plan", {"operation_key": "plan-1", "plan_id": "p1", "site_id": "s1", "route_code": "r1",
            "weekday": 0, "stop_sequence": 10, "active_from": "2026-01-01", "active_to": None})
        result = self.call("manifest", {"operation_key": "manifest-1", "service_date": "2026-09-21", "route_code": "r1"})
        return result["result"]["route_id"], result["result"]["stops"][0]["stop_id"]

    def read(self, *args):
        p = subprocess.run([sys.executable, *OPT, str(HERE / "cli.py"), str(self.db), *args], capture_output=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def test_init_never_overwrites(self):
        before = self.db.read_bytes()
        self.call("init", code=2)
        self.assertEqual(self.db.read_bytes(), before)

    def test_init_does_not_create_parents(self):
        path = self.root / "missing" / "nested" / "db.sqlite3"
        self.call("init", code=2, database=path)
        self.assertFalse(path.parent.parent.exists())

    def test_init_rejects_payload_before_creation(self):
        path = self.root / "fresh.sqlite3"
        self.call("init", {}, database=path, code=2)
        self.assertFalse(path.exists())

    def test_record_requires_existing_database(self):
        path = self.root / "absent.sqlite3"
        self.call("customer", self.customer(), database=path, code=2)
        self.assertFalse(path.exists())

    def test_unrelated_database_is_not_initialized(self):
        path = self.root / "foreign.sqlite3"
        with contextlib.closing(sqlite3.connect(path)) as conn:
            conn.execute("CREATE TABLE keep(value TEXT)")
            conn.execute("INSERT INTO keep VALUES ('unchanged')")
            conn.commit()
        before = path.read_bytes()
        self.call("customer", self.customer(), database=path, code=2)
        self.assertEqual(path.read_bytes(), before)

    def test_symlink_database_is_refused(self):
        link = self.root / "link.sqlite3"
        try:
            os.symlink(self.db, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unsupported by this platform")
        self.call("customer", self.customer(), database=link, code=2)
        self.assertEqual(self.count(), 0)

    def test_missing_payload_is_rejected(self):
        self.call("customer", code=2)
        self.assertEqual(self.count(), 0)

    def test_duplicate_json_keys_are_rejected(self):
        for raw in [b'{"operation_key":"a","operation_key":"b","customer_id":"c1","name":"Name"}',
                    b'{"x":{"count":1,"count":2}}']:
            with self.subTest(raw=raw):
                self.call("customer", raw=raw, code=2)
        self.assertEqual(self.count(), 0)

    def test_fractional_and_nonfinite_json_numbers_are_rejected(self):
        for number in [b"1.0", b"1e0", b"NaN", b"Infinity", b"-Infinity"]:
            with self.subTest(number=number):
                self.call("customer", raw=b'{"name":'+number+b'}', code=2)
        self.assertEqual(self.count(), 0)

    def test_boolean_null_and_wrong_types_are_rejected(self):
        cases = [("customer", {**self.customer(), "name": None}),
                 ("customer", {**self.customer(), "customer_id": 1}),
                 ("agreement", {"operation_key": "a", "agreement_id": "a", "site_id": "s", "item_code": "x",
                     "unit_price_cents": True, "active_from": "2026-01-01"}),
                 ("pickup", {"operation_key": "b", "stop_id": "s", "linen_counts": {"x": True}, "container_ids": ["x"]}),
                 ("pickup", {"operation_key": "b", "stop_id": "s", "linen_counts": {"x": 1}, "container_ids": [False]}),
                 ("process", {"operation_key": "p", "stop_id": "s", "processed_counts": {"x": 1}, "damaged_counts": False})]
        for command, payload in cases:
            with self.subTest(command=command, payload=payload):
                self.call(command, payload, code=2)
        self.assertEqual(self.count(), 0)

    def test_unknown_and_missing_fields_are_rejected(self):
        for payload in [{**self.customer(), "authority": True}, {**self.customer(), "method": "_connect"}, {"operation_key": "a"}]:
            with self.subTest(payload=payload):
                self.call("customer", payload, code=2)
        self.assertEqual(self.count(), 0)

    def test_batches_and_nonobjects_are_rejected(self):
        for raw in [b"[]", b"null", b'"text"', b"true", b"42"]:
            with self.subTest(raw=raw):
                self.call("customer", raw=raw, code=2)
        self.assertEqual(self.count(), 0)

    def test_oversized_input_is_rejected(self):
        self.call("customer", raw=b" " * 1_048_577, code=2)
        self.assertEqual(self.count(), 0)

    def test_excessive_nesting_and_nodes_are_rejected(self):
        self.call("customer", raw=b'{"x":'+b"["*40+b"0"+b"]"*40+b"}", code=2)
        self.call("customer", {"x": [0] * 10_001}, code=2)
        self.assertEqual(self.count(), 0)

    def test_invalid_unicode_is_rejected(self):
        for raw in [b"\xff", b'{"operation_key":"a","customer_id":"c","name":"\\ud800"}', b'{"\\ud800":1}']:
            with self.subTest(raw=raw):
                self.call("customer", raw=raw, code=2)
        self.assertEqual(self.count(), 0)

    def test_utf8_bom_and_unicode_names_are_preserved(self):
        payload = self.customer("Synthetic Café Linen")
        self.call("customer", raw=b"\xef\xbb\xbf" + json.dumps(payload, ensure_ascii=False).encode())
        self.assertEqual(self.read("customer-snapshot", "c1")["name"], payload["name"])

    def test_real_process_replay_and_restart(self):
        self.call("customer", self.customer(), spawn=True)
        result = self.call("customer", self.customer(), spawn=True)
        self.assertEqual(result["status"], "REPLAYED")
        self.assertEqual(self.read("customer-snapshot", "c1")["name"], self.customer()["name"])
        self.assertEqual(self.count(), 1)

    def test_stdin_input_uses_the_same_engine(self):
        result = self.call("customer", self.customer(), stdin=True)
        self.assertEqual(result["status"], "APPLIED")
        self.assertEqual(self.count(), 1)

    def test_exact_replay_and_changed_content_conflict(self):
        self.call("customer", self.customer())
        replay = self.call("customer", self.customer())
        self.assertEqual(replay["status"], "REPLAYED")
        self.assertFalse(replay["operation_appended"])
        rejected = self.call("customer", self.customer("Changed name"), code=2)
        self.assertEqual(rejected["error_type"], "IdempotencyConflict")
        self.assertEqual(self.count(), 1)

    def test_complete_shift_invoice_draft_and_readonly_handoff(self):
        route, stop = self.prepare()
        self.call("pickup", {"operation_key": "pick", "stop_id": stop, "linen_counts": {"towel": 3}, "container_ids": ["bag1"]})
        self.call("process", {"operation_key": "process", "stop_id": stop, "processed_counts": {"towel": 3}})
        self.call("deliver", {"operation_key": "deliver", "stop_id": stop, "delivered_counts": {"towel": 3}, "container_ids": ["bag1"]})
        result = self.call("invoice-draft", {"operation_key": "draft", "stop_id": stop})
        self.assertEqual(result["result"]["total_cents"], 285)
        self.assertEqual(result["result"]["state"], "DRAFT")
        snapshot = self.read("route-snapshot", route)
        self.assertEqual(snapshot["state"], "COMPLETE")
        self.assertEqual(snapshot["stops"][0]["state"], "INVOICE_DRAFTED")
        before = self.db.read_bytes()
        proof = self.read("integrity")
        self.assertEqual(proof["events"], 9)
        self.assertEqual(proof["status"], "PASS")
        bundle = self.read("export-route", route, str(self.root / "handoff"))
        self.assertEqual(set(bundle["created"]), {"json", "csv", "markdown"})
        self.assertEqual(self.db.read_bytes(), before)
        for path in bundle["created"].values():
            self.assertTrue(Path(path).is_file())
        self.call("invoice-draft", {"operation_key": "duplicate", "stop_id": stop}, code=2)
        self.assertEqual(self.count(), 9)

    def test_exceptions_block_draft_until_explicit_resolution(self):
        route, stop = self.prepare()
        self.call("pickup", {"operation_key": "pick", "stop_id": stop, "linen_counts": {"towel": 4}, "container_ids": ["bag1"]})
        processed = self.call("process", {"operation_key": "process", "stop_id": stop, "processed_counts": {"towel": 3}, "damaged_counts": {"towel": 1}})
        delivered = self.call("deliver", {"operation_key": "deliver", "stop_id": stop, "delivered_counts": {"towel": 2}, "container_ids": ["bag2"]})
        ids = processed["result"]["open_exception_ids"] + delivered["result"]["open_exception_ids"]
        self.assertEqual(len(ids), 4)
        before = self.count()
        rejected = self.call("invoice-draft", {"operation_key": "draft", "stop_id": stop}, code=2)
        self.assertEqual(rejected["error_type"], "InvoiceBlocked")
        self.assertEqual(self.count(), before)
        for i, identity in enumerate(ids):
            self.call("resolve", {"operation_key": f"resolve-{i}", "exception_id": identity,
                "resolution_code": "OPERATOR_REVIEWED", "note": "Synthetic test disposition, not a quality certification"})
        result = self.call("invoice-draft", {"operation_key": "draft", "stop_id": stop})
        self.assertEqual(result["result"]["total_cents"], 190)
        self.assertEqual(self.count(), before + 5)
        self.assertTrue(all(e["status"] == "RESOLVED" for e in self.read("route-snapshot", route)["stops"][0]["exceptions"]))

    def test_native_semantic_rejections_do_not_append(self):
        self.call("customer", {**self.customer(), "customer_id": "bad id"}, code=2)
        self.call("customer", self.customer("control\ntext"), code=2)
        self.assertEqual(self.count(), 0)


if __name__ == "__main__":
    unittest.main()
