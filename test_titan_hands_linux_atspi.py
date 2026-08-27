#!/usr/bin/env python3
"""Root battery entry for the Linux AT-SPI TITAN Hands adapter."""

from __future__ import annotations

import unittest

from host.titan_hands.tests import test_linux_atspi


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromModule(test_linux_atspi)


if __name__ == "__main__":
    unittest.main(verbosity=2)
