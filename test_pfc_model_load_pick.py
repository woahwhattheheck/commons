#!/usr/bin/env python3
"""Exact canary for the section-20 PFC model/load choice."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
MODEL = "C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf"
RECEIPT = "p/demon-pick-pfc-model-load-20260830-01.md"


class PfcModelLoadPickTests(unittest.TestCase):
    def test_directive_and_todo_name_the_pick(self):
        directives = (ROOT / "DIRECTIVES.md").read_text(encoding="utf-8")
        self.assertIn("exact PFC model/load choice — **PICKED:** `" + MODEL + "`", directives)
        self.assertIn("Host work remains address/fire/read/display", directives)
        todo = (ROOT / "todo.html").read_text(encoding="utf-8")
        self.assertIn(
            "inbox path and exact PFC model/load choice PICKED 2026-08-30 CODEX",
            todo,
        )

    def test_current_loader_and_harness_agree(self):
        loader = (ROOT / "host/pfc_load.py").read_text(encoding="utf-8")
        harness = (ROOT / "host/pfc_harness.py").read_text(encoding="utf-8")
        self.assertIn("python host/pfc_load.py " + MODEL, loader)
        self.assertIn('MAGIC = b"PFCLOAD1"', loader)
        self.assertIn('else "' + MODEL + '"', loader)
        self.assertIn("python host/pfc_harness.py connect " + MODEL, harness)
        self.assertIn('else "' + MODEL + '"', harness)
        self.assertIn("does NO model forward-pass compute", harness)

    def test_receipt_refuses_execution_claims(self):
        receipt = (ROOT / RECEIPT).read_text(encoding="utf-8")
        for declaration in (
            "state: `CHOICE_ONLY`",
            "live_load_executed: `NO`",
            "model_or_titan_bytes_written: `NO`",
            "inference_executed: `NO`",
            "host_forward_pass: `NO`",
        ):
            self.assertIn(declaration, receipt)
        self.assertIn("does not run `pfc_load.py` or `pfc_harness.py`", receipt)


if __name__ == "__main__":
    unittest.main()
