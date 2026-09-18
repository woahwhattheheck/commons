from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from revenue.revenue_experiment_allocator import engine


class RevenueExperimentAllocatorInputRaceTests(unittest.TestCase):
    def test_stable_input_still_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_bytes(b'{"value":1}')
            self.assertEqual(engine.load_json_strict(path), {"value": 1})

    def test_same_size_inplace_mutation_fails_closed(self) -> None:
        original = b'{"value":1}'
        replacement = b'{"value":2}'
        self.assertEqual(len(original), len(replacement))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_bytes(original)
            real_read = engine.os.read
            mutated = False

            def racing_read(fd: int, size: int) -> bytes:
                nonlocal mutated
                chunk = real_read(fd, size)
                if chunk and not mutated:
                    mutated = True
                    path.write_bytes(replacement)
                return chunk

            with patch.object(engine.os, "read", side_effect=racing_read):
                with self.assertRaisesRegex(engine.AllocationError, "input changed while reading"):
                    engine.load_json_strict(path)
            self.assertTrue(mutated)

    def test_replay_detects_race_even_if_stat_metadata_is_masked(self) -> None:
        original = b'{"value":1}'
        replacement = b'{"value":2}'

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_bytes(original)
            stable_stat = path.stat()
            real_read = engine.os.read
            mutated = False

            def racing_read(fd: int, size: int) -> bytes:
                nonlocal mutated
                chunk = real_read(fd, size)
                if chunk and not mutated:
                    mutated = True
                    path.write_bytes(replacement)
                return chunk

            with (
                patch.object(engine.os, "fstat", return_value=stable_stat),
                patch.object(engine.os, "read", side_effect=racing_read),
            ):
                with self.assertRaisesRegex(engine.AllocationError, "input changed while reading"):
                    engine.load_json_strict(path)
            self.assertTrue(mutated)


if __name__ == "__main__":
    unittest.main()
