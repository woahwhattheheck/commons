from __future__ import annotations

import unittest
from unittest import mock

from tools.outbound_send_guard import muse_provider_receipt_ledger_v1 as ledger


class MergeGenesisTests(unittest.TestCase):
    def test_initialize_allows_main_merge_commit_but_ledger_commits_stay_single_parent(self):
        genesis = "a" * 40
        base_tree = "b" * 40
        created_tree = "c" * 40
        created_commit = "d" * 40
        final_state = {"provider_head_sha": created_commit, "manifest": {"generation": 0}}

        with mock.patch.object(ledger, "_get_default_head", return_value=genesis), \
             mock.patch.object(ledger, "_get_commit", return_value={"tree_sha": base_tree}) as get_commit, \
             mock.patch.object(ledger, "_post_tree", return_value=created_tree) as post_tree, \
             mock.patch.object(ledger, "_post_commit", return_value=created_commit) as post_commit, \
             mock.patch.object(ledger, "_api", return_value={"object": {"sha": created_commit}}), \
             mock.patch.object(ledger, "_get_ref", return_value=created_commit), \
             mock.patch.object(ledger, "verify_remote_complete_prefix", return_value=final_state):
            self.assertEqual(ledger.initialize_remote_ledger(token="test-token"), final_state)

        get_commit.assert_called_once_with(genesis, require_single_parent=False)
        post_tree.assert_called_once()
        post_commit.assert_called_once_with("test-token", created_tree, genesis, 0)


if __name__ == "__main__":
    unittest.main()
