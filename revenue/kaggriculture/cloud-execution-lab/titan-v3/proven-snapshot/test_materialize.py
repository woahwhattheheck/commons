# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import unittest

from support import fixture, restore, sha


class MaterializeTests(unittest.TestCase):
    def test_runnable_alias_receipt_and_exact_source_bytes(self):
        fx = fixture(self)
        output = fx.root / "out" / "candidate.tar.gz"
        receipt_path = fx.root / "out" / "receipt.json"
        receipt = restore.materialize(fx.root, output=output, receipt_path=receipt_path, pin=fx.pin)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["candidate"]["entrypoint"], "main.py::agent")
        self.assertEqual(receipt["candidate"]["sha256"], sha(output.read_bytes()))
        parsed = restore._read_archive(output.read_bytes())
        self.assertEqual(parsed["main.py"], restore.MAIN_BYTES)
        self.assertEqual(set(parsed), set(fx.members) | {"main.py"})
        for name, payload in fx.members.items():
            self.assertEqual(parsed[name], payload, name)
        self.assertEqual(json.loads(receipt_path.read_text()), receipt)

    def test_output_is_byte_deterministic_across_directories(self):
        left = fixture(self)
        right = fixture(self)
        a = restore.materialize(left.root, pin=left.pin, run_smoke=False)
        b = restore.materialize(right.root, pin=right.pin, run_smoke=False)
        self.assertEqual(a["candidate"]["sha256"], b["candidate"]["sha256"])
        self.assertEqual(a["candidate"]["bytes"], b["candidate"]["bytes"])

    def test_refuses_existing_output_and_preserves_it(self):
        fx = fixture(self)
        output = fx.root / "candidate.tar.gz"
        output.write_bytes(b"do-not-touch")
        with self.assertRaisesRegex(restore.SnapshotError, "refusing to overwrite"):
            restore.materialize(fx.root, output=output, pin=fx.pin, run_smoke=False)
        self.assertEqual(output.read_bytes(), b"do-not-touch")

    def test_receipt_conflict_precedes_output_publication(self):
        fx = fixture(self)
        output = fx.root / "candidate.tar.gz"
        receipt = fx.root / "receipt.json"
        receipt.write_bytes(b"existing")
        with self.assertRaisesRegex(restore.SnapshotError, "existing receipt"):
            restore.materialize(
                fx.root,
                output=output,
                receipt_path=receipt,
                pin=fx.pin,
                run_smoke=False,
            )
        self.assertFalse(output.exists())
        self.assertEqual(receipt.read_bytes(), b"existing")


if __name__ == "__main__":
    unittest.main()
