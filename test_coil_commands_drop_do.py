#!/usr/bin/env python3
"""Hermetic: commands.json /drop do[] forbids titan.gguf and commons.mno smash."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsDropDoTest(unittest.TestCase):
    def test_drop_do(self) -> None:
        drop = next(c for c in json.loads(COMMANDS.read_text(encoding="utf-8"))["commands"] if c.get("id") == "drop")
        blob = " ".join(drop["do"])
        self.assertIn("titan.gguf", blob.lower() or blob)
        self.assertIn("commons.mno", blob)
        self.assertGreaterEqual(len(drop["do"]), 2)


if __name__ == "__main__":
    unittest.main()
