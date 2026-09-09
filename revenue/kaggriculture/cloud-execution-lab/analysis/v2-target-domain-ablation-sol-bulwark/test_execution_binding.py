# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import bound_compare
import execution_bind

V2_CANDIDATE = b"# SPDX-License-Identifier: Apache-2.0\nfrom scheduler import agent\n"


def write_package(root: Path, marker: str) -> None:
    root.mkdir(parents=True)
    (root / "candidate.py").write_bytes(V2_CANDIDATE)
    (root / "scheduler.py").write_text(
        "def agent(observation=None, configuration=None):\n"
        f"    return {{'farmer':['PASS'],'hands':[],'market':[],'marker':'{marker}'}}\n",
        encoding="utf-8",
    )
    (root / "reference.txt").write_text("unchanged\n", encoding="utf-8")


def closure(root: Path) -> str:
    return execution_bind.closure_sha256(execution_bind.inventory(root))


def receipt(source: Path, candidate: Path):
    return {
        "schema_version": 1,
        "operation": execution_bind.OPERATION,
        "source": {"closure_sha256": closure(source)},
        "ablation": {
            "closure_sha256": closure(candidate),
            "changed_files": ["scheduler.py"],
        },
    }


def import_wrapper(path: Path) -> subprocess.CompletedProcess[str]:
    script = (
        "import importlib.util,json;"
        f"p={str(path)!r};"
        "s=importlib.util.spec_from_file_location('probe',p);"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        "print(json.dumps(m.agent({},{}),sort_keys=True))"
    )
    return subprocess.run(
        [sys.executable, "-I", "-S", "-c", script],
        text=True,
        capture_output=True,
        check=False,
    )


class ExecutionBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.candidate = self.root / "out" / "candidate"
        write_package(self.source, "control")
        shutil.copytree(self.source, self.candidate)
        (self.candidate / "scheduler.py").write_text(
            "def agent(observation=None, configuration=None):\n"
            "    return {'farmer':['PASS'],'hands':[],'market':[],'marker':'candidate'}\n",
            encoding="utf-8",
        )
        self.receipt = receipt(self.source, self.candidate)
        self.binding = execution_bind.build(
            self.source, self.candidate, self.root / "out", self.receipt
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_generated_entries_are_distinct_names_with_same_verified_bytes(self):
        verified = execution_bind.verify(
            self.root / "out", self.binding, self.receipt
        )
        self.assertNotEqual(verified["control"]["entry"], verified["candidate"]["entry"])
        self.assertEqual(
            verified["control"]["wrapper_sha256"],
            verified["candidate"]["wrapper_sha256"],
        )
        control = import_wrapper(self.root / "out" / "control_entry.py")
        candidate = import_wrapper(self.root / "out" / "candidate_entry.py")
        self.assertEqual(control.returncode, 0, control.stderr)
        self.assertEqual(candidate.returncode, 0, candidate.stderr)
        self.assertIn('"marker": "control"', control.stdout)
        self.assertIn('"marker": "candidate"', candidate.stdout)

    def test_dependency_drift_fails_inside_measured_entrypoint(self):
        path = self.root / "out" / "candidate" / "scheduler.py"
        path.write_text(path.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
        result = import_wrapper(self.root / "out" / "candidate_entry.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("package closure mismatch", result.stderr)

    def test_verifier_rejects_sidecar_rebinding(self):
        path = self.root / "out" / "candidate.binding.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["closure_sha256"] = self.receipt["source"]["closure_sha256"]
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(execution_bind.BindingError, "sidecar digest"):
            execution_bind.verify(self.root / "out", self.binding, self.receipt)

    def test_reports_must_name_the_two_bound_entries(self):
        normalized = execution_bind.verify(
            self.root / "out", self.binding, self.receipt
        )
        wrapper = normalized["wrapper_source_sha256"]
        control = {
            "candidate": {
                "entry": "control_entry.py",
                "callable": "agent",
                "sha256": wrapper,
            }
        }
        candidate = {
            "candidate": {
                "entry": "candidate_entry.py",
                "callable": "agent",
                "sha256": wrapper,
            }
        }
        self.assertEqual(
            bound_compare.validate_reports(control, candidate, normalized), wrapper
        )
        predecessor = copy.deepcopy(candidate)
        predecessor["candidate"] = {
            "entry": "candidate.py",
            "callable": "agent",
            "sha256": execution_bind.V2_ENTRY_SHA256,
        }
        with self.assertRaisesRegex(
            bound_compare.BoundCompareError, "not bound"
        ):
            bound_compare.validate_reports(control, predecessor, normalized)

    def test_candidate_entry_bytes_are_frozen(self):
        self.assertEqual(hashlib.sha256(V2_CANDIDATE).hexdigest(), execution_bind.V2_ENTRY_SHA256)
        (self.candidate / "candidate.py").write_text("def agent(): pass\n", encoding="utf-8")
        bad = receipt(self.source, self.candidate)
        with self.assertRaisesRegex(execution_bind.BindingError, "candidate.py"):
            execution_bind.build(self.source, self.candidate, self.root / "other", bad)


if __name__ == "__main__":
    unittest.main()
