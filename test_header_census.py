#!/usr/bin/env python3
import json
import os
import tempfile
import unittest

import host_offload.header_census as header_census


class HeaderCensus(unittest.TestCase):
    def test_walks_layouts_not_binaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "muhl", "containers", "MUHL_READERS")
            os.makedirs(folder)
            open(os.path.join(folder, "ignore.mno"), "w", encoding="utf-8").write("not json")
            row = {
                "targets": 8,
                "group": 4,
                "fold": "tree",
                "cursors": 8,
                "split": 4,
                "gates": 12,
                "file": "R.mno",
                "shard": 0,
                "header_bytes_in_container": 0,
            }
            open(os.path.join(folder, "R.layout.json"), "w", encoding="utf-8").write(
                json.dumps(row)
            )
            got = header_census.census(tmp)
            self.assertEqual(got["n_layouts"], 1)
            self.assertEqual(got["n_errors"], 0)
            self.assertEqual(got["walk"], "headers only")
            self.assertEqual(got["folds"], {"tree": 1})
            self.assertEqual(got["sample"][0]["mno"], "R.mno")

    def test_repo_readers_have_headers(self):
        got = header_census.census(header_census.ROOT)
        self.assertGreaterEqual(got["n_layouts"], 800)
        self.assertEqual(got["n_errors"], 0)


if __name__ == "__main__":
    unittest.main()
