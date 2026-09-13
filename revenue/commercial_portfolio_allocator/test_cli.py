from __future__ import annotations

import json
import os
import tempfile
import unittest

from .acceptance import base_packet
from .cli import _read_json
from .engine import ContractError


class CliIngressTests(unittest.TestCase):
    def test_duplicate_json_keys_rejected(self):
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            handle.write('{"a":1,"a":2}')
            path = handle.name
        try:
            with self.assertRaises(ContractError):
                _read_json(path)
        finally:
            os.unlink(path)

    def test_regular_packet_reads(self):
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            json.dump(base_packet("read"), handle)
            path = handle.name
        try:
            self.assertEqual(_read_json(path)["portfolio_id"], "portfolio-read")
        finally:
            os.unlink(path)

    def test_final_component_symlink_rejected_when_supported(self):
        if not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("O_NOFOLLOW unavailable")
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, "packet.json")
            link = os.path.join(directory, "link.json")
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(base_packet("symlink"), handle)
            os.symlink(target, link)
            with self.assertRaises(OSError):
                _read_json(link)


if __name__ == "__main__":
    unittest.main()
