# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

import bind_opponents as binding


class FrozenSourceTests(unittest.TestCase):
    def test_published_freeze_matches_every_exact_file(self):
        rows = binding.source_inventory()
        self.assertEqual(len(rows), len(binding.EXPECTED_FILES))
        indexed = {row["path"]: row for row in rows}
        self.assertEqual(set(indexed), set(binding.EXPECTED_FILES))
        for path, expected in binding.EXPECTED_FILES.items():
            self.assertEqual(indexed[path]["bytes"], expected["bytes"])
            self.assertEqual(indexed[path]["sha256"], expected["sha256"])

    def test_real_private_wrappers_build_probe_and_reverify(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "opponents"
            receipt = binding.build_binding(output, "a" * 40)
            verified = binding.verify_binding(output, receipt, "a" * 40)
        self.assertTrue(verified["verified"])
        self.assertEqual(
            verified["binding_object_sha256"], binding.object_sha256(receipt)
        )
        self.assertEqual(
            receipt["opponents"]["v1"]["probe"]["binding"]["verified_origins"],
            {
                "entry": "candidate.py",
                "mechanics": "mechanics.py",
                "scheduler": "scheduler.py",
                "scheduler.parent": "reference/next-panel/vendor/arlene.py",
                "scheduler.receipt_math": "reference/decision/decision.py",
            },
        )
        self.assertNotEqual(
            receipt["opponents"]["v1"]["wrapper"]["sha256"],
            receipt["opponents"]["v1"]["source_entry"]["sha256"],
        )

    def test_post_panel_verifier_rejects_scheduler_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "opponents"
            receipt = binding.build_binding(output, "b" * 40)
            scheduler = output / "v1" / "payload" / "scheduler.py"
            scheduler.write_bytes(scheduler.read_bytes() + b"\n# drift\n")
            with self.assertRaisesRegex(
                binding.BindingError, "private payload receipt drift"
            ):
                binding.verify_binding(output, receipt, "b" * 40)

    def test_post_panel_verifier_rejects_extra_payload_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "opponents"
            receipt = binding.build_binding(output, "c" * 40)
            (output / "v1" / "payload" / "ambient.py").write_text(
                "raise RuntimeError('ambient')\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                binding.BindingError, "private payload receipt drift"
            ):
                binding.verify_binding(output, receipt, "c" * 40)

    def test_post_panel_verifier_rejects_receipt_rebinding(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "opponents"
            receipt = binding.build_binding(output, "d" * 40)
            forged = copy.deepcopy(receipt)
            forged["opponents"]["v1"]["source_entry"] = copy.deepcopy(
                forged["opponents"]["arlene"]["source_entry"]
            )
            with self.assertRaisesRegex(
                binding.BindingError, "source entry receipt drift"
            ):
                binding.verify_binding(output, forged, "d" * 40)


class PredecessorKillingWrapperTests(unittest.TestCase):
    ENTRY = "from scheduler import agent\n"

    def _make_arm(self, parent: Path, quantity: int) -> tuple[Path, str, str]:
        arm = parent / f"arm-{quantity}"
        payload = arm / "payload"
        payload.mkdir(parents=True)
        (payload / "candidate.py").write_text(self.ENTRY, encoding="utf-8")
        (payload / "scheduler.py").write_text(
            "def agent(obs, config):\n"
            "    return {'farmer': ['PASS'], 'hands': [], "
            f"'market': [['SELL', 'WHEAT', {quantity}]]}}\n",
            encoding="utf-8",
        )
        rows = binding._inventory(payload, f"synthetic arm {quantity}")
        closure = binding.closure_sha256(rows)
        source = binding._wrapper_source(
            label=f"synthetic_{quantity}",
            entry_name="candidate.py",
            expected_files={
                row["path"]: {
                    "bytes": row["bytes"],
                    "sha256": row["sha256"],
                }
                for row in rows
            },
            expected_closure=closure,
            module_origins={"scheduler": "scheduler.py"},
            attribute_origins={},
            git_head="e" * 40,
        )
        wrapper = arm / "candidate.py"
        wrapper.write_text(source, encoding="utf-8")
        return wrapper, closure, hashlib.sha256(self.ENTRY.encode()).hexdigest()

    @staticmethod
    def _call(wrapper: Path) -> dict:
        script = r'''
import importlib.util
import json
from pathlib import Path
import sys
path = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("witness", path)
module = importlib.util.module_from_spec(spec)
sys.modules["witness"] = module
spec.loader.exec_module(module)
print(json.dumps(module.agent({}, {}), sort_keys=True))
'''
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        process = subprocess.run(
            [sys.executable, "-I", "-c", script, str(wrapper)],
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=20,
            check=True,
        )
        return json.loads(process.stdout)

    def test_same_entry_hash_different_scheduler_emits_different_action(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left, left_closure, left_entry = self._make_arm(root, 1)
            right, right_closure, right_entry = self._make_arm(root, 2)
            self.assertEqual(left_entry, right_entry)
            self.assertNotEqual(left_closure, right_closure)
            self.assertNotEqual(
                hashlib.sha256(left.read_bytes()).hexdigest(),
                hashlib.sha256(right.read_bytes()).hexdigest(),
            )
            self.assertNotEqual(self._call(left), self._call(right))

    def test_wrapper_rejects_dependency_drift_before_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            wrapper, _closure, _entry = self._make_arm(Path(temporary), 1)
            scheduler = wrapper.parent / "payload" / "scheduler.py"
            scheduler.write_text(
                "def agent(obs, config): return {'forged': True}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                binding.BindingError, "wrapper probe failed"
            ):
                binding._probe_wrapper(wrapper, "synthetic_1")

    def test_wrapper_rejects_preloaded_scheduler(self):
        with tempfile.TemporaryDirectory() as temporary:
            wrapper, _closure, _entry = self._make_arm(Path(temporary), 1)
            script = r'''
import importlib.util
from pathlib import Path
import sys
import types
sys.modules["scheduler"] = types.ModuleType("scheduler")
path = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("witness", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
'''
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            process = subprocess.run(
                [sys.executable, "-I", "-c", script, str(wrapper)],
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=20,
                check=False,
            )
            self.assertNotEqual(process.returncode, 0)
            self.assertIn("ambient local module collision", process.stderr)

    def test_wrapper_rejects_extra_regular_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            wrapper, _closure, _entry = self._make_arm(Path(temporary), 1)
            (wrapper.parent / "payload" / "extra.py").write_text(
                "pass\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                binding.BindingError, "wrapper probe failed"
            ):
                binding._probe_wrapper(wrapper, "synthetic_1")


class ParserTests(unittest.TestCase):
    def test_duplicate_json_key_fails_closed(self):
        with self.assertRaisesRegex(binding.BindingError, "duplicate JSON key"):
            binding.strict_object_bytes(b'{"x":1,"x":2}', "fixture")

    def test_boolean_or_negative_byte_count_is_not_closure_data(self):
        for value in (True, -1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(binding.BindingError, "byte count"):
                    binding.closure_sha256(
                        [{"path": "x", "bytes": value, "sha256": "a" * 64}]
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
