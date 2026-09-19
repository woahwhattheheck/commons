"""Source-receipt consistency checks using the actual imported rehearsal.

No provider I/O or deployment occurs. Temporary edits are restored in finally;
only the isolated checkout used for this test should be supplied to the runner.
"""
import hashlib
import unittest
from pathlib import Path

from tools.deploy_transport_preflight import demo
from tools.deploy_transport_preflight import preflight

ROOT = Path(demo.__file__).resolve().parent
INVALID_SOURCE = b"This is deliberately not Python syntax !!!\n"


class DemoSourceBindingTests(unittest.TestCase):
    def test_control_unchanged_sources_and_five_cases(self):
        expected = {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("preflight.py", "demo.py")
        }
        result = demo.run_demo()
        self.assertEqual(expected, result["source_sha256"])
        self.assertEqual(5, len(result["cases"]))
        for row in result["cases"]:
            self.assertTrue(all(value is False for value in row["report"]["external_authority"].values()))

    def check_later_unexecutable_bytes_are_not_named_as_executed(self, name):
        path = ROOT / name
        original = path.read_bytes()
        original_sha = hashlib.sha256(original).hexdigest()
        with self.assertRaises(SyntaxError):
            compile(INVALID_SOURCE, str(path), "exec")
        try:
            # The published modules were already imported above. Neither is
            # reloaded or monkeypatched; only its later disk bytes change.
            path.write_bytes(INVALID_SOURCE)
            try:
                result = demo.run_demo()
            except preflight.DomainError:
                # Explicitly rejecting source drift is also a safe outcome.
                return
            self.assertEqual(5, len(result["cases"]))
            self.assertEqual(
                original_sha, result["source_sha256"][name],
                "receipt names later unexecutable bytes, not the imported source",
            )
        finally:
            path.write_bytes(original)

    def test_runtime_receipt_does_not_name_later_unexecutable_source(self):
        self.check_later_unexecutable_bytes_are_not_named_as_executed("preflight.py")

    def test_rehearsal_receipt_does_not_name_later_unexecutable_source(self):
        self.check_later_unexecutable_bytes_are_not_named_as_executed("demo.py")


if __name__ == "__main__":
    unittest.main()
