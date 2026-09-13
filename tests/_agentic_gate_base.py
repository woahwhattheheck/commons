from __future__ import annotations

import unittest
from datetime import datetime, timezone

from revenue.agentic_genai_evaluation_gate.gate import compile_receipt
from revenue.agentic_genai_evaluation_gate.golden import build_golden_packet


EVAL_AT = datetime(2026, 9, 13, 14, 0, 0, tzinfo=timezone.utc)


class AgenticGateCase(unittest.TestCase):
    def packet(self):
        return build_golden_packet()

    def compile(self, packet=None, *, at=EVAL_AT):
        return compile_receipt(
            self.packet() if packet is None else packet,
            evaluated_at=at,
        )
