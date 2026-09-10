# SPDX-License-Identifier: Apache-2.0
from promotion_test_support import *

class SeedCustodyTests(unittest.TestCase):
    def test_current_bank_is_valid_and_spent(self) -> None:
        value = pc.validate_seed_ledger(spent_ledger())
        self.assertEqual(len(value["entries"]), 1)
        self.assertEqual(value["entries"][0]["status"], "spent")

    def test_seed_reuse_is_rejected(self) -> None:
        future = copy.deepcopy(panel()["run"])
        future["seeds"][0] = spent_ledger()["entries"][0]["seeds"][0]
        with self.assertRaisesRegex(pc.PromotionClosureError, "reuses prior seeds"):
            pc.assert_fresh_spend(spent_ledger(), future)

    def test_attempt_two_is_rejected(self) -> None:
        future = copy.deepcopy(panel()["run"])
        future["run_attempt"] = 2
        with self.assertRaisesRegex(pc.PromotionClosureError, "attempt 1"):
            pc.assert_fresh_spend(spent_ledger(), future)

    def test_manual_dispatch_is_rejected(self) -> None:
        future = copy.deepcopy(panel()["run"])
        future["event_name"] = "workflow_dispatch"
        with self.assertRaisesRegex(pc.PromotionClosureError, "pull_request"):
            pc.assert_fresh_spend(spent_ledger(), future)

    def test_append_only_rejects_prior_mutation(self) -> None:
        before = spent_ledger()
        after = copy.deepcopy(before)
        after["entries"][0]["status"] = "reserved"
        after["entries"].append(panel()["run"])
        with self.assertRaisesRegex(pc.PromotionClosureError, "changed prior"):
            pc.validate_append_only(before, after)

    def test_run_environment_is_hard_pinned(self) -> None:
        env = {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_RUN_ATTEMPT": "1",
            "CHECKED_OUT_HEAD": "a" * 40,
            "GITHUB_RUN_ID": "123",
        }
        receipt = pc.validate_run_environment(env, expected_head="a" * 40)
        self.assertEqual(receipt["run_id"], 123)
        env["GITHUB_RUN_ATTEMPT"] = "2"
        with self.assertRaisesRegex(pc.PromotionClosureError, "attempt 1"):
            pc.validate_run_environment(env, expected_head="a" * 40)


class ClosureManifestTests(unittest.TestCase):
    def test_identical_entry_wrapper_does_not_hide_scheduler_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            left = root / "v1"
            right = root / "v2"
            left.mkdir()
            right.mkdir()
            for lane, scheduler in ((left, "VALUE = 1\n"), (right, "VALUE = 2\n")):
                (lane / "candidate.py").write_text("from scheduler import agent\n", encoding="utf-8")
                (lane / "scheduler.py").write_text(scheduler, encoding="utf-8")
            one = pc.build_closure_manifest(
                left,
                entry="candidate.py",
                module_origins={"scheduler": "scheduler.py"},
            )
            two = pc.build_closure_manifest(
                right,
                entry="candidate.py",
                module_origins={"scheduler": "scheduler.py"},
            )
            self.assertEqual(one["members"][0]["sha256"], two["members"][0]["sha256"])
            self.assertNotEqual(one["closure_sha256"], two["closure_sha256"])

    def test_manifest_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("def agent(*args): return []\n", encoding="utf-8")
            manifest = pc.build_closure_manifest(root, entry="main.py")
            (root / "main.py").write_text("def agent(*args): return ['PASS']\n", encoding="utf-8")
            with self.assertRaisesRegex(pc.PromotionClosureError, "differs from live root"):
                pc.validate_closure_manifest(root, manifest)

    def test_symlink_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("x = 1\n", encoding="utf-8")
            try:
                (root / "alias.py").symlink_to(root / "main.py")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(pc.PromotionClosureError, "symlinked"):
                pc.build_closure_manifest(root, entry="main.py")



if __name__ == "__main__":
    unittest.main()
