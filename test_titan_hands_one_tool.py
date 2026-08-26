#!/usr/bin/env python3
"""Root battery entry for the one-tool TITAN Hands MCP surface."""

from __future__ import annotations

import unittest

from host.titan_hands.tests import test_one_tool


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromModule(test_one_tool)


if __name__ == "__main__":
    unittest.main(verbosity=2)
