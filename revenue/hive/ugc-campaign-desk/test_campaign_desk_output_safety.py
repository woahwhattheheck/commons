#!/usr/bin/env python3
"""Exclusive-output regressions for PR10664's campaign packet builder."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import campaign_desk as d

ROOT = Path(__file__).resolve().parent
SAMPLE = json.loads((ROOT / "sample_campaign.json").read_text(encoding="utf-8"))


class OutputSafetyTests(unittest.TestCase):
    def variants(self) -> tuple[dict, dict]:
        first = deepcopy(SAMPLE)
        second = deepcopy(SAMPLE)
        first["campaign"]["id"] = "fictional-alpha-campaign"
        first["campaign"]["product"] = "Fictional Alpha Product"
        second["campaign"]["id"] = "fictional-bravo-campaign"
        second["campaign"]["product"] = "Fictional Bravo Product"
        return first, second

    def test_concurrent_distinct_publishers_leave_one_complete_winner(self) -> None:
        first, second = self.variants()
        expected = (d.build_zip(first), d.build_zip(second))
        self.assertNotEqual(*expected)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = (root / "first.json", root / "second.json")
            for path, document in zip(inputs, (first, second)):
                path.write_text(json.dumps(document), encoding="utf-8")
            output = root / "shared.zip"
            link_barrier = threading.Barrier(2)
            original_link = d.os.link
            results: list[int | None] = [None, None]

            def synchronized_link(source, destination, *args, **kwargs):
                if Path(destination) == output:
                    link_barrier.wait(timeout=5)
                return original_link(source, destination, *args, **kwargs)

            def run(slot: int) -> None:
                results[slot] = d.main([str(inputs[slot]), str(output)])

            with patch.object(d.os, "link", synchronized_link), patch("builtins.print"):
                workers = [threading.Thread(target=run, args=(slot,)) for slot in range(2)]
                for worker in workers:
                    worker.start()
                for worker in workers:
                    worker.join(timeout=10)
            self.assertFalse(any(worker.is_alive() for worker in workers))
            self.assertEqual(sorted(results), [0, 1])
            self.assertIn(output.read_bytes(), expected)
            self.assertEqual(list(root.glob(".ugc-campaign-*.tmp")), [])

    def test_broken_output_symlink_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "campaign.json"
            source.write_text(json.dumps(SAMPLE), encoding="utf-8")
            target = root / "outside.zip"
            output = root / "packet.zip"
            output.symlink_to(target)
            with patch("builtins.print"):
                status = d.main([str(source), str(output)])
            self.assertEqual(status, 1)
            self.assertTrue(output.is_symlink())
            self.assertFalse(target.exists())
            self.assertEqual(list(root.glob(".ugc-campaign-*.tmp")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
