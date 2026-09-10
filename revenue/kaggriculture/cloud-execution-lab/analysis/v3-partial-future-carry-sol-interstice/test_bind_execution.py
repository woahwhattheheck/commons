# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import bind_execution as binding
import materialize as lane

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parents[1] / "runtime" / "variants" / "v2"
PARENT_MATERIALIZER = (
    HERE.parent / "v2-forced-feasibility-ablation-sol-keel" / "materialize.py"
)


def source_path() -> Path:
    return Path(os.environ.get("TITAN_V2_SOURCE", DEFAULT_SOURCE)).resolve()


def load_parent_materializer():
    spec = importlib.util.spec_from_file_location(
        "sol_interstice_parent_strict_materializer", PARENT_MATERIALIZER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {PARENT_MATERIALIZER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def fixtures():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = source_path()
        repair = root / "repair"
        repair_receipt_path = root / "REPAIR-MATERIALIZATION.json"
        repair_receipt = lane.materialize(source, repair)
        repair_receipt_path.write_text(
            json.dumps(repair_receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        strict_env = os.environ.get("TITAN_STRICT_ROOT")
        receipt_env = os.environ.get("TITAN_STRICT_RECEIPT")
        if strict_env and receipt_env:
            strict = Path(strict_env).resolve()
            strict_receipt_path = Path(receipt_env).resolve()
        else:
            parent = load_parent_materializer()
            strict = root / "strict"
            strict_receipt_path = root / "STRICT-MATERIALIZATION.json"
            strict_receipt = parent.materialize(source, strict)
            strict_receipt_path.write_text(
                json.dumps(strict_receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        yield root, source, strict, repair, strict_receipt_path, repair_receipt_path


def import_wrapper(path: Path) -> subprocess.CompletedProcess[str]:
    code = (
        "import importlib.util;"
        "s=importlib.util.spec_from_file_location('bound','bound_entry.py');"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        "assert callable(m.agent);print(m.ARM)"
    )
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=path,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class BindingTests(unittest.TestCase):
    def test_three_exact_arms_bind_and_import(self):
        with fixtures() as values:
            root, source, strict, repair, strict_receipt, repair_receipt = values
            output = root / "arms"
            receipt = binding.bind_execution(
                source,
                strict,
                repair,
                strict_receipt,
                repair_receipt,
                output,
            )
            self.assertEqual(set(receipt["arms"]), {"control", "strict", "repair"})
            self.assertEqual(
                receipt["arms"]["repair"]["payload_closure_sha256"],
                binding.EXPECTED_REPAIR_CLOSURE,
            )
            wrappers = {
                row["wrapper_sha256"] for row in receipt["arms"].values()
            }
            self.assertEqual(len(wrappers), 3)
            for arm in ("control", "strict", "repair"):
                result = import_wrapper(output / arm)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), arm)

    def test_tampered_source_payload_fails_before_copy(self):
        with fixtures() as values:
            root, source, strict, repair, strict_receipt, repair_receipt = values
            corrupt = root / "corrupt-control"
            shutil.copytree(source, corrupt)
            scheduler = corrupt / "scheduler.py"
            scheduler.write_bytes(scheduler.read_bytes() + b"\n")
            with self.assertRaisesRegex(binding.BindingError, "control payload closure"):
                binding.bind_execution(
                    corrupt,
                    strict,
                    repair,
                    strict_receipt,
                    repair_receipt,
                    root / "arms",
                )

    def test_tampered_bound_payload_rejects_import(self):
        with fixtures() as values:
            root, source, strict, repair, strict_receipt, repair_receipt = values
            output = root / "arms"
            binding.bind_execution(
                source,
                strict,
                repair,
                strict_receipt,
                repair_receipt,
                output,
            )
            scheduler = output / "repair" / "payload" / "scheduler.py"
            scheduler.write_bytes(scheduler.read_bytes() + b"\n")
            result = import_wrapper(output / "repair")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("closure mismatch", result.stderr)

    def test_output_inside_source_is_rejected_without_mutation(self):
        with fixtures() as values:
            _root, source, strict, repair, strict_receipt, repair_receipt = values
            before = lane.inventory(source)
            with self.assertRaisesRegex(binding.BindingError, "nested inside control"):
                binding.bind_execution(
                    source,
                    strict,
                    repair,
                    strict_receipt,
                    repair_receipt,
                    source / "forbidden-bound-arms",
                )
            self.assertEqual(lane.inventory(source), before)
            self.assertFalse((source / "forbidden-bound-arms").exists())

    def test_tampered_repair_marker_receipt_is_rejected(self):
        with fixtures() as values:
            root, source, strict, repair, strict_receipt, repair_receipt = values
            value = json.loads(repair_receipt.read_text(encoding="utf-8"))
            value["candidate"]["preserved_v2_markers"][
                "forced_feasibility_priority"
            ] = False
            bad = root / "bad-repair-marker.json"
            bad.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(binding.BindingError, "marker custody"):
                binding.bind_execution(
                    source,
                    strict,
                    repair,
                    strict_receipt,
                    bad,
                    root / "arms",
                )

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":1}\n')
            with self.assertRaisesRegex(binding.BindingError, "duplicate JSON key"):
                binding.strict_object(path)

    def test_wrong_repair_operation_is_rejected(self):
        with fixtures() as values:
            root, source, strict, repair, strict_receipt, repair_receipt = values
            value = json.loads(repair_receipt.read_text(encoding="utf-8"))
            value["operation"] = "wrong"
            bad = root / "bad-repair.json"
            bad.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(binding.BindingError, "identity mismatch"):
                binding.bind_execution(
                    source,
                    strict,
                    repair,
                    strict_receipt,
                    bad,
                    root / "arms",
                )


if __name__ == "__main__":
    unittest.main()
