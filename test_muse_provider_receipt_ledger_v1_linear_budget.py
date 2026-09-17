from __future__ import annotations

import os
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from tools.outbound_send_guard import muse_election_v2 as gate
from tools.outbound_send_guard import muse_provider_receipt_ledger_v1 as ledger
from test_muse_provider_receipt_ledger_v1 import FakeGitHub, candidate


TOKEN = "provider-test-token"
SEEDS = "abcdef012345"


def _receipt(seed: str, index: int):
    base = datetime(2026, 9, 17, 1, 0, tzinfo=timezone.utc) + timedelta(minutes=index)
    request = gate.prepare_request(
        candidate(seed),
        request_id=f"req-linear-budget-{index:04d}-{seed}",
        requested_at=base.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    snapshot = {
        "schema_version": gate.SNAPSHOT_SCHEMA,
        "complete": True,
        "channel_id": gate.MUSE_DM_CONVERSATION_ID,
        "coverage_started_at": (base - timedelta(seconds=600)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "captured_at": (base + timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "messages": [
            {
                "message_ts": f"{int((base + timedelta(seconds=1)).timestamp())}.000001",
                "author_user_id": "U0BSAL3CZ4Y",
                "text": request["message"],
            }
        ],
    }
    receipt = gate.compile_receipt(request, snapshot, prior_receipts=(), ledger_complete=True)
    if not gate.verify_receipt(receipt):
        raise AssertionError("budget fixture receipt failed canonical verification")
    return receipt


class LinearProviderBudgetTests(unittest.TestCase):
    def _built_provider(self):
        provider = FakeGitHub()
        patcher = mock.patch.object(ledger, "_api", side_effect=provider.api)
        api = patcher.start()
        self.addCleanup(patcher.stop)
        ledger.initialize_remote_ledger(token=TOKEN)
        for index, seed in enumerate(SEEDS):
            ledger.append_receipt(_receipt(seed, index), token=TOKEN)
        return provider, api

    def test_provider_reads_are_linear_in_generation_count(self):
        _provider, api = self._built_provider()
        generation = len(SEEDS)
        api.reset_mock()

        state = ledger.verify_remote_complete_prefix(token=TOKEN)

        self.assertEqual(state["manifest"]["generation"], generation)
        blob_gets = 0
        for call in api.call_args_list:
            if len(call.args) >= 2 and call.args[0] == "GET" and "/git/blobs/" in call.args[1]:
                blob_gets += 1
        # One manifest blob per generation (including generation zero), plus
        # each current receipt body exactly once. No historical receipt-body
        # rereads are permitted.
        self.assertLessEqual(blob_gets, (2 * generation) + 2)
        # Two ref reads + one commit/tree/manifest triplet per generation +
        # current receipt bodies. This bound is intentionally loose but linear;
        # the predecessor's triangular rereads exceed it at generation 12.
        self.assertLessEqual(api.call_count, (4 * generation) + 10)

    def test_historical_receipt_blob_swap_is_rejected_from_tree_identity(self):
        provider, _api = self._built_provider()
        head = provider.refs[ledger.PROVIDER_BRANCH]
        current = provider.commits[head]
        parent = current["parent"]
        parent_commit = provider.commits[parent]
        parent_paths = provider.trees[parent_commit["tree"]]
        receipt_path = sorted(p for p in parent_paths if p.startswith(ledger.RECEIPT_PREFIX))[0]
        foreign_blob = provider._blob(b"{}\n")
        parent_paths[receipt_path] = foreign_blob

        with self.assertRaisesRegex(ledger.MuseProviderReceiptLedgerError, "historical receipt blob changed"):
            ledger.verify_remote_complete_prefix(token=TOKEN)

    def test_provider_read_budget_runs_under_python_optimized_mode(self):
        env = dict(os.environ)
        proc = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "test_muse_provider_receipt_ledger_v1_linear_budget.LinearProviderBudgetTests.test_provider_reads_are_linear_in_generation_count",
            ],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"optimized child failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
