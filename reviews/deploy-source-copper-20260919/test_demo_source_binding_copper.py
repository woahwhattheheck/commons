"""Source-receipt checks against an isolated copy of the actual rehearsal.

Each case copies the exact package bytes once and imports them in a fresh Python
process. Only temporary copies are edited; the checkout is never modified.
No provider I/O or deployment occurs.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.deploy_transport_preflight import demo

ROOT = Path(demo.__file__).resolve().parent
FILES = ("__init__.py", "preflight.py", "demo.py")
PROBE = r'''
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from tools.deploy_transport_preflight import demo, preflight

name = sys.argv[2]
if name:
    path = root / "tools" / "deploy_transport_preflight" / name
    invalid_source = b"This is deliberately not Python syntax !!!\n"
    try:
        compile(invalid_source, str(path), "exec")
    except SyntaxError:
        pass
    else:
        raise RuntimeError("negative-control source unexpectedly compiles")
    # The real published modules are already imported. No callable is replaced.
    path.write_bytes(invalid_source)
try:
    result = demo.run_demo()
except preflight.DomainError:
    print(json.dumps({"rejected_source_drift": True}))
else:
    print(json.dumps({
        "rejected_source_drift": False,
        "source_sha256": result["source_sha256"],
        "case_count": len(result["cases"]),
        "all_authority_false": all(
            value is False
            for case in result["cases"]
            for value in case["report"]["external_authority"].values()
        ),
    }))
'''


class DemoSourceBindingTests(unittest.TestCase):
    def execute_case(self, changed_name=""):
        # The expected identities and copied files use the same captured bytes.
        captured = {name: (ROOT / name).read_bytes() for name in FILES}
        expected = {
            name: hashlib.sha256(captured[name]).hexdigest()
            for name in ("preflight.py", "demo.py")
        }
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "tools" / "deploy_transport_preflight"
            target.mkdir(parents=True)
            for name, payload in captured.items():
                (target / name).write_bytes(payload)
            flags = ["-" + "O" * sys.flags.optimize] if sys.flags.optimize else []
            run = subprocess.run(
                [sys.executable, *flags, "-c", PROBE, directory, changed_name],
                cwd=directory, capture_output=True, text=True, timeout=15,
                check=False,
            )
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertEqual("", run.stderr)
            return expected, json.loads(run.stdout)

    def test_control_unchanged_sources_and_five_cases(self):
        expected, result = self.execute_case()
        self.assertFalse(result["rejected_source_drift"])
        self.assertEqual(expected, result["source_sha256"])
        self.assertEqual(5, result["case_count"])
        self.assertTrue(result["all_authority_false"])

    def check_later_unexecutable_bytes_are_not_named_as_executed(self, name):
        expected, result = self.execute_case(name)
        if result["rejected_source_drift"]:
            return
        self.assertEqual(5, result["case_count"])
        self.assertEqual(
            expected[name], result["source_sha256"][name],
            "receipt names later unexecutable bytes, not the imported source",
        )

    def test_runtime_receipt_does_not_name_later_unexecutable_source(self):
        self.check_later_unexecutable_bytes_are_not_named_as_executed("preflight.py")

    def test_rehearsal_receipt_does_not_name_later_unexecutable_source(self):
        self.check_later_unexecutable_bytes_are_not_named_as_executed("demo.py")


if __name__ == "__main__":
    unittest.main()
