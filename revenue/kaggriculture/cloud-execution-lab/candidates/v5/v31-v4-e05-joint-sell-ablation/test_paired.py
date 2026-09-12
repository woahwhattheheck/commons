# SPDX-License-Identifier: Apache-2.0
"""Aggregate the unchanged causal-runner contracts with custody-shell contracts."""
from test_paired_core import *  # noqa: F401,F403
from test_engine_custody import *  # noqa: F401,F403

if __name__ == "__main__":
    import unittest
    unittest.main()
