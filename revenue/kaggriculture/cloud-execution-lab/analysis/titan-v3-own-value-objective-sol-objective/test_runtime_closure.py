# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import runtime_closure

CASE = Path(__file__).resolve().parent
LAB = CASE.parent.parent
EXPECTED_EXTERNAL_ROOTS = {
    "seller_snapshot.py",
    "observed_clone.py",
    "plant_suffix.py",
    "sell_priority.py",
    "pressure_priority.py",
    "seed_retry.py",
    "funded_payback.py",
}


class PathGuardTests(unittest.TestCase):
    def test_archive_member_escape_forms_fail_closed(self):
        for value in (
            "../escape.py",
            "a/../escape.py",
            "/absolute.py",
            "a//b.py",
            "a/./b.py",
            r"a\b.py",
            "",
        ):
            with self.subTest(value=value):
                with self.assertRaises(runtime_closure.RuntimeClosureError):
                    runtime_closure._member_name(value)

    def test_declared_source_cannot_escape_kaggriculture_boundary(self):
        with self.assertRaisesRegex(
            runtime_closure.RuntimeClosureError,
            "escapes Kaggriculture boundary",
        ):
            runtime_closure._source_path(
                LAB.resolve(),
                "../../outside.py",
                LAB.parent.resolve(),
            )

    def test_existing_output_fails_before_materialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "closure"
            output.mkdir()
            with self.assertRaisesRegex(
                runtime_closure.RuntimeClosureError,
                "output already exists",
            ):
                runtime_closure.materialize_runtime_closure(LAB, output)


class ExactRepositoryClosureTests(unittest.TestCase):
    def test_exact_archive_source_map_is_executable_in_fresh_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "runtime"
            receipt = runtime_closure.materialize_runtime_closure(LAB, output)

            self.assertEqual(receipt["schema"], "titan-runtime-closure/v1")
            self.assertFalse(receipt["canonical_mutation"])
            self.assertEqual(receipt["entrypoint"], "main.py::agent")
            self.assertEqual(
                receipt["closure"]["members"],
                receipt["archive"]["runtime_files"] + 1,
            )
            external = set(receipt["closure"]["external_root_members"])
            self.assertTrue(EXPECTED_EXTERNAL_ROOTS.issubset(external))

            rows = {row["member"]: row for row in receipt["source_files"]}
            self.assertEqual(
                rows["observed_clone.py"]["declared_source"],
                "../cloud-runtime-pulse/observed_clone.py",
            )
            for member in EXPECTED_EXTERNAL_ROOTS | {"main.py"}:
                path = output / member
                self.assertTrue(path.is_file(), member)
                self.assertFalse(path.is_symlink(), member)
                self.assertEqual(
                    runtime_closure.git_blob_sha1(path.read_bytes()),
                    rows[member]["git_blob_sha1"],
                )

            script = r'''
import importlib
import json
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
names = [
    "main",
    "observed_clone",
    "seller_snapshot",
    "plant_suffix",
    "sell_priority",
    "pressure_priority",
    "seed_retry",
    "funded_payback",
]
loaded = {}
for name in names:
    module = importlib.import_module(name)
    path = Path(getattr(module, "__file__", "")).resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise SystemExit(f"{name} escaped closure: {path}") from exc
    loaded[name] = relative
if not callable(getattr(importlib.import_module("main"), "agent", None)):
    raise SystemExit("canonical main.agent is not callable")
print(json.dumps(loaded, sort_keys=True))
'''
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            process = subprocess.run(
                [sys.executable, "-I", "-c", script, str(output)],
                cwd=output,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            loaded = json.loads(process.stdout)
            self.assertEqual(loaded["main"], "main.py")
            self.assertEqual(loaded["observed_clone"], "observed_clone.py")
            self.assertEqual(set(loaded), {
                "main",
                "observed_clone",
                "seller_snapshot",
                "plant_suffix",
                "sell_priority",
                "pressure_priority",
                "seed_retry",
                "funded_payback",
            })

            # The materializer is read-only with respect to the canonical lab.
            builder, _, _ = runtime_closure._load_builder(LAB)
            _, manifest, canonical_receipt = builder.render()
            self.assertEqual(
                receipt["archive"]["sha256"],
                canonical_receipt["sha256"],
            )
            self.assertEqual(
                receipt["archive"]["source_manifest_sha256"],
                runtime_closure.sha256(manifest),
            )


if __name__ == "__main__":
    unittest.main()
