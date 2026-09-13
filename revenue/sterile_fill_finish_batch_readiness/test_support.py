from __future__ import annotations

import copy
import unittest

from .acceptance import AS_OF, EXPECTED_HOLD_COUNTS, packet, run_acceptance
from .gate import HOLD_STATUS, READY_STATUS, ReadinessError, canonical_json, compile_readiness, verify_readiness_package


class BatchReadinessTestBase(unittest.TestCase):
    def compile(self, raw=None):
        return compile_readiness(packet(1) if raw is None else raw, as_of=AS_OF)

    def hold_codes(self, compiled):
        return [row["code"] for row in compiled["receipt"]["holds"]]
