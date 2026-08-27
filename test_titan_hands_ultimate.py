#!/usr/bin/env python3
"""CI battery entry for the one-tool TITAN Hands dispatcher."""

from host.titan_hands.tests.test_runtime import RuntimeTests

__all__ = ["RuntimeTests"]


if __name__ == "__main__":
    import unittest

    unittest.main()
