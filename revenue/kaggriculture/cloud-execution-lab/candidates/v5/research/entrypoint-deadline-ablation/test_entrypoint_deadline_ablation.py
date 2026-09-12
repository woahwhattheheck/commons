# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import entrypoint_deadline_ablation as ab


SYNTHETIC_V4 = b'''# SPDX-License-Identifier: Apache-2.0
_INSTANCE = None

def _new_instance(root, feature_data):
    town_procurement = feature_data.get("town_procurement")
    class FinalPressureAgent:
        pass
    return FinalPressureAgent()

def agent(observation, configuration=None):
    global _INSTANCE
    import time
    entry_started = time.perf_counter()
    cfg = dict(configuration or {})
    step = int(observation["step"])
    replace = _INSTANCE is None or step == 0
    instance = None if replace else _INSTANCE
    feature_data = {"town_procurement": True} if replace else None
    town_enabled = bool(feature_data.get("town_procurement", False)) if replace else False
    if town_enabled:
        town_procurement = True
    from titan_runtime import deadline
    budget = 1.0
    remaining = budget-(time.perf_counter()-entry_started)
    timer = deadline._DeadlineTimer(remaining)
    try:
        with timer:
            if replace:
                instance = _new_instance(None, feature_data)
                _INSTANCE = instance
            output = instance.act(observation, cfg, entry_started=entry_started)
    except deadline.DeadlineExceeded as error:
        if error is not timer.expired:
            raise
        return {"farmer": ["PASS"], "hands": [], "market": []}
    return output
'''


class EntrypointDeadlineAblationTests(unittest.TestCase):
    def test_git_blob_hash_is_content_addressed(self):
        self.assertEqual(
            ab.git_blob_sha1(b"hello\n"),
            "ce013625030ba8dba906f756967f9e9ca394464a",
        )

    def test_ablation_removes_only_guard_suffix_and_keeps_v4_prefix(self):
        expected = ab.git_blob_sha1(SYNTHETIC_V4)
        treated, receipt = ab.ablate_v4_main(SYNTHETIC_V4, expected_blob=expected)
        source = SYNTHETIC_V4.decode("utf-8")
        result = treated.decode("utf-8")
        start = source.index("    from titan_runtime import deadline\n")
        self.assertEqual(result[:start], source[:start])
        self.assertIn("class FinalPressureAgent", result)
        self.assertIn("town_procurement", result)
        self.assertIn(
            "return instance.act(observation, cfg, entry_started=entry_started)",
            result,
        )
        self.assertNotIn("_DeadlineTimer", result)
        self.assertNotIn("except deadline.DeadlineExceeded", result)
        self.assertFalse(receipt["production_activation"])
        self.assertEqual(receipt["input_main_git_blob"], expected)
        self.assertEqual(receipt["output_main_git_blob"], ab.git_blob_sha1(treated))

    def test_wrong_input_blob_fails_closed(self):
        with self.assertRaises(ab.SourceMismatch):
            ab.ablate_v4_main(SYNTHETIC_V4, expected_blob="0" * 40)

    def test_duplicate_splice_anchor_fails_closed(self):
        poisoned = SYNTHETIC_V4.replace(
            b"    from titan_runtime import deadline\n",
            b"    from titan_runtime import deadline\n    from titan_runtime import deadline\n",
        )
        with self.assertRaises(ab.SourceMismatch):
            ab.ablate_v4_main(poisoned, expected_blob=ab.git_blob_sha1(poisoned))

    def test_existing_output_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "main.py"
            target.write_bytes(b"sentinel")
            with self.assertRaises(FileExistsError):
                ab._write_new(str(target), b"replacement")
            self.assertEqual(target.read_bytes(), b"sentinel")

    def test_existing_receipt_blocks_treatment_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "treated-main.py"
            receipt = Path(directory) / "receipt.json"
            receipt.write_bytes(b"sentinel")
            with self.assertRaises(FileExistsError):
                ab._write_materialization(
                    str(output),
                    b"treated",
                    str(receipt),
                    b"receipt",
                )
            self.assertFalse(output.exists())
            self.assertEqual(receipt.read_bytes(), b"sentinel")

    def test_materialization_outputs_must_be_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "same"
            with self.assertRaises(ValueError):
                ab._write_materialization(str(target), b"a", str(target), b"b")
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
