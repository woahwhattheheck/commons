#!/usr/bin/env python3
"""Root battery entry for the TITAN Hands paid-session hook."""

from __future__ import annotations

import unittest

from host.titan_hands.tests import test_pay


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromModule(test_pay)


if __name__ == "__main__":
    unittest.main(verbosity=2)
