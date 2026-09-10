#!/usr/bin/env python3
"""Run PR #12018's original tests with the unittest descriptor bug corrected.

The parent test module extracts plain functions from scheduler source and stores
them directly on a unittest.TestCase class. Access through ``self`` then binds
an unintended TestCase argument. This successor changes no parent source or
test bytes: it wraps only those three extracted callables as static methods
after the parent's own setUpClass has run, then loads and executes every
original test from that module.
"""
from __future__ import annotations

import unittest

import test_materialize as parent_tests


def main() -> int:
    original_setup = parent_tests.ExactSourceTests.setUpClass.__func__

    @classmethod
    def fixed_setup(cls):
        original_setup(cls)
        for name in ("legacy_profile", "prefix", "candidate_profile"):
            raw = cls.__dict__[name]
            if isinstance(raw, staticmethod):
                raw = raw.__func__
            setattr(cls, name, staticmethod(raw))

    parent_tests.ExactSourceTests.setUpClass = fixed_setup
    suite = unittest.defaultTestLoader.loadTestsFromModule(parent_tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
