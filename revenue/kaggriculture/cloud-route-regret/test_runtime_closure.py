# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import importlib.machinery
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

import runtime_closure

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / "cloud-execution-lab"


def metadata(data: bytes) -> dict[str, object]:
    return {
        "git_blob": hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        ).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def receipt(
    source_data: bytes,
    scheduler_data: bytes = b"# scheduler fixture\n",
) -> dict[str, object]:
    return {
        "import_bindings": {
            runtime_closure.MODULE_NAME: runtime_closure.SOURCE_KEY,
        },
        "git_blobs": {
            runtime_closure.SOURCE_KEY: metadata(source_data),
            runtime_closure.SCHEDULER_KEY: metadata(scheduler_data),
        },
    }


class PrivateImportClosureTests(unittest.TestCase):
    def tearDown(self):
        runtime_closure._reset_for_tests()
        sys.modules.pop("scheduler", None)

    def test_exact_source_is_exclusively_staged_and_preloaded(self):
        source_data = (
            b"from copy import deepcopy\n"
            b"def detached_json_value(value):\n    return deepcopy(value)\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.py"
            source.write_bytes(source_data)
            private = root / "private"
            with mock.patch.object(runtime_closure, "source_path", return_value=source):
                record = runtime_closure.install(receipt(source_data), private_root=private)
            destination = private / "observed_clone.py"
            self.assertEqual(destination.read_bytes(), source_data)
            self.assertEqual(record["private_path"], str(destination.resolve()))
            self.assertEqual(record["git_blob"], metadata(source_data)["git_blob"])
            self.assertEqual(record["sha256"], metadata(source_data)["sha256"])
            module = sys.modules["observed_clone"]
            self.assertEqual(Path(module.__file__).resolve(), destination.resolve())
            self.assertEqual(module.detached_json_value({"x": [1]}), {"x": [1]})

    def test_scheduler_attestation_binds_bytes_function_and_both_origins(self):
        source_data = b"def detached_json_value(value):\n    return value\n"
        scheduler_data = b"# scheduler fixture\n"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.py"
            scheduler_source = root / "scheduler.py"
            source.write_bytes(source_data)
            scheduler_source.write_bytes(scheduler_data)

            def resolve(key: str) -> Path:
                if key == runtime_closure.SOURCE_KEY:
                    return source
                if key == runtime_closure.SCHEDULER_KEY:
                    return scheduler_source
                raise AssertionError(key)

            with mock.patch.object(runtime_closure, "source_path", side_effect=resolve):
                runtime_closure.install(receipt(source_data, scheduler_data),
                    private_root=root / "private",
                )
                scheduler = types.ModuleType("scheduler")
                scheduler.__file__ = str(scheduler_source)
                scheduler.detached_json_value = sys.modules[
                    "observed_clone"
                ].detached_json_value
                sys.modules["scheduler"] = scheduler
                attestation = runtime_closure.attest_scheduler()
            self.assertIs(attestation["identity_bound"], True)
            self.assertEqual(attestation["scheduler_path"], str(scheduler_source.resolve()))
            self.assertEqual(
                attestation["scheduler_git_blob"], metadata(scheduler_data)["git_blob"]
            )

    def test_ambient_module_is_rejected_before_any_private_copy(self):
        source_data = b"def detached_json_value(value):\n    return value\n"
        ambient = types.ModuleType("observed_clone")
        ambient.__file__ = "/ambient/observed_clone.py"
        sys.modules["observed_clone"] = ambient
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.py"
            source.write_bytes(source_data)
            private = Path(td) / "private"
            with mock.patch.object(runtime_closure, "source_path", return_value=source):
                with self.assertRaisesRegex(ValueError, "ambient module"):
                    runtime_closure.install(receipt(source_data), private_root=private)
            self.assertFalse(private.exists())

    def test_source_drift_and_preexisting_root_fail_closed(self):
        source_data = b"def detached_json_value(value):\n    return value\n"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.py"
            source.write_bytes(source_data + b"# drift\n")
            with mock.patch.object(runtime_closure, "source_path", return_value=source):
                with self.assertRaisesRegex(ValueError, "mismatch"):
                    runtime_closure.install(receipt(source_data), private_root=root / "private")
            runtime_closure._reset_for_tests()
            source.write_bytes(source_data)
            private = root / "private-existing"
            private.mkdir()
            destination = private / "observed_clone.py"
            destination.write_text("attacker\n", encoding="utf-8")
            with mock.patch.object(runtime_closure, "source_path", return_value=source):
                with self.assertRaises(FileExistsError):
                    runtime_closure.install(receipt(source_data), private_root=private)
            self.assertEqual(destination.read_text(encoding="utf-8"), "attacker\n")

    def test_idempotence_is_limited_to_exact_normalized_root_and_bytes(self):
        source_data = b"def detached_json_value(value):\n    return value\n"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.py"
            source.write_bytes(source_data)
            first_root = root / "nested" / ".." / "first"
            (root / "nested").mkdir()
            with mock.patch.object(runtime_closure, "source_path", return_value=source):
                first = runtime_closure.install(receipt(source_data), private_root=first_root)
                second = runtime_closure.install(
                    receipt(source_data), private_root=root / "first"
                )
                with self.assertRaisesRegex(ValueError, "already installed"):
                    runtime_closure.install(
                        receipt(source_data), private_root=root / "second"
                    )
            self.assertEqual(first, second)

    def test_scheduler_byte_drift_is_rejected_even_with_same_module_object(self):
        source_data = b"def detached_json_value(value):\n    return value\n"
        scheduler_data = b"# scheduler fixture\n"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.py"
            scheduler_source = root / "scheduler.py"
            source.write_bytes(source_data)
            scheduler_source.write_bytes(scheduler_data)

            def resolve(key: str) -> Path:
                return source if key == runtime_closure.SOURCE_KEY else scheduler_source

            with mock.patch.object(runtime_closure, "source_path", side_effect=resolve):
                runtime_closure.install(
                    receipt(source_data, scheduler_data), private_root=root / "private"
                )
                scheduler = types.ModuleType("scheduler")
                scheduler.__file__ = str(scheduler_source)
                scheduler.detached_json_value = sys.modules[
                    "observed_clone"
                ].detached_json_value
                sys.modules["scheduler"] = scheduler
                scheduler_source.write_bytes(scheduler_data + b"# drift\n")
                with self.assertRaisesRegex(ValueError, "mismatch"):
                    runtime_closure.attest_scheduler()


@unittest.skipUnless(
    (LAB / "scheduler.py").is_file()
    and (HERE.parent / "cloud-runtime-pulse/observed_clone.py").is_file(),
    "requires the complete Kaggriculture source tree",
)
class CurrentTreeImportProbeTests(unittest.TestCase):
    def test_predecessor_path_is_unresolvable_but_bound_private_stage_imports(self):
        # PathFinder with an explicit search path proves the predecessor root
        # itself cannot satisfy scheduler.py's top-level observed_clone import.
        self.assertFalse((LAB / "observed_clone.py").exists())
        self.assertIsNone(
            importlib.machinery.PathFinder.find_spec("observed_clone", [str(LAB)])
        )
        script = r'''
import importlib
import inspect
import json
from pathlib import Path
import sys
case = Path(sys.argv[1]).resolve(strict=True)
lab = Path(sys.argv[2]).resolve(strict=True)
private = Path.cwd() / "sealed"
sys.path.insert(0, str(case))
from source_contract import verify_source_contract
import runtime_closure
receipt = verify_source_contract()
staged = runtime_closure.install(receipt, private_root=private)
sys.path.insert(0, str(lab))
scheduler = importlib.import_module("scheduler")
attested = runtime_closure.attest_scheduler()
assert scheduler.detached_json_value is sys.modules["observed_clone"].detached_json_value
assert (
    Path(inspect.getsourcefile(scheduler.detached_json_value)).resolve()
    == Path(staged["private_path"])
)
print(json.dumps({"staged": staged, "attested": attested}, sort_keys=True))
'''
        with tempfile.TemporaryDirectory() as td:
            env = {
                "PATH": os.defpath,
                "HOME": td,
                "LANG": "C.UTF-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
            }
            completed = subprocess.run(
                [sys.executable, "-I", "-B", "-c", script, str(HERE), str(LAB)],
                cwd=td,
                env=env,
                check=True,
                text=True,
                capture_output=True,
                timeout=30,
            )
            report = json.loads(completed.stdout)
            self.assertIs(report["attested"]["identity_bound"], True)
            self.assertTrue(
                Path(report["staged"]["private_path"]).is_relative_to(Path(td))
            )


if __name__ == "__main__":
    unittest.main()
