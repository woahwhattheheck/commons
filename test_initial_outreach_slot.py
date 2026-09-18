#!/usr/bin/env python3
"""Root battery entry for the initial-outreach one-shot slot."""

from __future__ import annotations

import unittest

from revenue.initial_outreach_slot import test_slot


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromModule(test_slot)


if __name__ == "__main__":
    unittest.main(verbosity=2)
