#!/usr/bin/env python3
"""CI entry for host/demand_survive.py --self-test."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from host.demand_survive import self_test  # noqa: E402


def test_demand_survive_scenarios():
    assert self_test() == 0


if __name__ == "__main__":
    raise SystemExit(self_test())
