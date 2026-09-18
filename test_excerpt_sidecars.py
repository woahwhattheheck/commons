#!/usr/bin/env python3
"""A sidecar that names a .mno without that file is not a land."""

from __future__ import annotations

import hashlib
import json
import os
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excerpts")


class TestExcerptSidecars(unittest.TestCase):
    def test_every_sidecar_has_its_container(self):
        found = 0
        for dirpath, _dirs, files in os.walk(ROOT):
            for name in files:
                if not name.endswith("_circuits.json"):
                    continue
                found += 1
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                self.assertTrue(data, path + " is empty")
                for key, row in data.items():
                    container = row.get("container")
                    self.assertTrue(container, key + " sidecar has no container")
                    excerpt = os.path.join(dirpath, container)
                    self.assertTrue(
                        os.path.isfile(excerpt),
                        "%s names %s but the excerpt is missing" % (path, container),
                    )
                    expected = row.get("sha256")
                    if expected:
                        with open(excerpt, "rb") as raw:
                            digest = hashlib.sha256(raw.read()).hexdigest()
                        self.assertEqual(
                            digest,
                            expected,
                            "%s sha256 does not match sidecar" % excerpt,
                        )
                    expected_len = row.get("len")
                    if expected_len:
                        self.assertEqual(os.path.getsize(excerpt), expected_len)
        self.assertGreaterEqual(found, 1, "no excerpt sidecars found")


if __name__ == "__main__":
    unittest.main()
