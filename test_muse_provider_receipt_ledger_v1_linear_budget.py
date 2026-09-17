from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest import mock

from tools.outbound_send_guard import muse_provider_receipt_ledger_v1 as ledger
from test_muse_provider_receipt_ledger_v1 import FakeGitHub, request_and_receipt

TOKEN = "provider-test-token"
SEEDS = "abcdef012345"
GENERATION = len(SEEDS)


class LedgerLinearBudgetTests(unittest.TestCase):
    def build_generation(self):
        provider = FakeGitHub()
        patch = mock.patch.object(ledger, "_api", side_effect=provider.api)
        patch.start()
        self.addCleanup(patch.stop)
        ledger.initialize_remote_ledger(token=TOKEN)
        for seed in SEEDS:
            _, receipt = request_and_receipt(seed)
            ledger.append_receipt(receipt, token=TOKEN)
        return provider

    def test_exact_provider_work_is_linear_at_generation_twelve(self):
        provider = self.build_generation()
        provider.reset_work_counters()
        with mock.patch.object(ledger, "_validate_entry", wraps=ledger._validate_entry) as validate_entry:
            state = ledger.verify_remote_complete_prefix(token=TOKEN)
        self.assertEqual(state["manifest"]["generation"], GENERATION)
        self.assertEqual(len(state["manifest"]["entries"]), GENERATION)
        self.assertEqual(validate_entry.call_count, GENERATION)
        self.assertEqual(provider.get_tree_calls, 0)
        self.assertEqual(provider.contents_reads, (GENERATION + 1) + GENERATION)
        self.assertEqual(provider.receipt_reads, GENERATION)
        self.assertEqual(provider.compare_rows, 1 + (2 * GENERATION))
        self.assertEqual(provider.api_calls, 4 * GENERATION + 5)
        self.assertLessEqual(provider.manifest_bytes, (GENERATION + 1) * 3072)

    def test_provider_manifest_is_fixed_size_delta_not_cumulative_prefix(self):
        provider = self.build_generation()
        sizes = []
        for generation in range(GENERATION + 1):
            head = provider.generation_commit(generation)
            tree = provider.trees[provider.commits[head]["tree"]]
            raw = provider.blobs[tree[ledger.MANIFEST_PATH]]
            sizes.append(len(raw))
        self.assertLess(max(sizes[1:]) - min(sizes[1:]), 256)
        self.assertLess(max(sizes), 3072)

    @unittest.skipIf(os.environ.get("MUSE_LEDGER_OPT_CHILD") == "1", "parent-only optimized launcher")
    def test_real_python_O_executes_linear_work_predecessor(self):
        env = dict(os.environ)
        env["MUSE_LEDGER_OPT_CHILD"] = "1"
        proc = subprocess.run(
            [sys.executable, "-O", "-m", "unittest", "-q",
             "test_muse_provider_receipt_ledger_v1_linear_budget.LedgerLinearBudgetTests.test_exact_provider_work_is_linear_at_generation_twelve"],
            cwd=os.path.dirname(__file__) or ".",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
        self.assertIn("OK", proc.stderr)


if __name__ == "__main__":
    unittest.main()
