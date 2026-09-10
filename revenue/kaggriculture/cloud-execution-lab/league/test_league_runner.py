# SPDX-License-Identifier: Apache-2.0
"""Contracts for contestant staging and the league runner plan path.

The full evaluator path is exercised by the real league panel (see
README); these tests cover staging fingerprints and the dry-run plan
without playing games.
"""
import json
import os
import tempfile
import unittest

from run_league import load_config, shard_list, stage_contestant, main as run_main


CHALLENGER = {
    "name": "v3-final-crop-binding",
    "entry": "cloud-execution-lab/candidates/v3-final-crop-binding/candidate_main.py",
    "callable": "agent",
    "support_modules": [
        "cloud-runtime-pulse/observed_clone.py",
        "cloud-quickstep/seller_snapshot.py",
    ],
}


class StageContestantTest(unittest.TestCase):
    def test_staging_produces_bootstrap_and_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = stage_contestant(CHALLENGER["name"], CHALLENGER["entry"],
                                  CHALLENGER["callable"],
                                  CHALLENGER["support_modules"], tmp)
            self.assertEqual(len(fp["entry_sha256"]), 64)
            self.assertTrue(os.path.isfile(fp["bootstrap"]))
            bootstrap = open(fp["bootstrap"]).read()
            self.assertIn(CHALLENGER["entry"], bootstrap)
            self.assertIn("do not edit by hand", bootstrap)
            support_dir = os.path.join(tmp, CHALLENGER["name"], "support")
            for module in ("observed_clone.py", "seller_snapshot.py"):
                self.assertTrue(os.path.isfile(os.path.join(support_dir, module)))
            self.assertEqual(len(fp["support"]), 2)
            self.assertTrue(all(len(s["sha256"]) == 64 for s in fp["support"]))

    def test_missing_entry_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Exception):
                stage_contestant("nope", "cloud-execution-lab/nope.py",
                                 "agent", [], tmp)


class ShardListTest(unittest.TestCase):
    def test_even_split(self):
        self.assertEqual(shard_list([1, 2, 3, 4], 2), [[1, 3], [2, 4]])

    def test_more_workers_than_items(self):
        self.assertEqual(shard_list([1, 2], 8), [[1], [2]])


class DryRunTest(unittest.TestCase):
    def test_dry_run_writes_plan_and_stages(self):
        import run_league as rl
        here = os.path.dirname(os.path.abspath(rl.__file__))
        with tempfile.TemporaryDirectory() as tmp:
            rc = run_main(["--config", os.path.join(here, "config.json"),
                           "--outdir", os.path.join(tmp, "run"),
                           "--dry-run"])
            self.assertEqual(rc, 0)
            plan = json.loads(open(os.path.join(tmp, "run", "plan.json")).read())
            self.assertIn("v3-kestrel-capital-execution", plan["contestants"])
            self.assertIn("v3-final-crop-binding", plan["contestants"])
            self.assertEqual(plan["cells_per_contestant"],
                             len(plan["opponents"]) * len(plan["seeds"]) * 2)


class ResumeTest(unittest.TestCase):
    def test_resume_aggregates_saved_shards_without_playing(self):
        import run_league as rl
        here = os.path.dirname(os.path.abspath(rl.__file__))
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = os.path.join(tmp, "run")
            shards = os.path.join(run_dir, "shards")
            os.makedirs(shards)
            games = []
            for seat in (0, 1):
                games.append({"opponent": "official_pass", "seed": 1,
                              "candidate_seat": seat, "status": "complete",
                              "scores": [100.0, 10.0] if seat == 0 else [10.0, 100.0],
                              "failure": None})
            report = {"seeds": [1], "games": games}
            with open(os.path.join(shards, "shard_v3-kestrel-capital-execution_1.json"),
                      "w") as handle:
                json.dump(report, handle)
            rc = run_main(["--config", os.path.join(here, "config.json"),
                           "--outdir", run_dir,
                           "--opponents", "official_pass",
                           "--seeds", "1",
                           "--ledger", os.path.join(tmp, "ledger.json"),
                           "--resume"])
            self.assertEqual(rc, 0)
            summary = json.loads(open(os.path.join(run_dir, "report.json")).read())
            names = [row["name"] for row in summary["standings"]]
            self.assertIn("v3-kestrel-capital-execution", names)
            self.assertIn("official_pass", names)
            rows = {r["name"]: r for r in summary["standings"]}
            self.assertEqual(rows["v3-kestrel-capital-execution"]["wins"], 2)
            self.assertEqual(rows["official_pass"]["losses"], 2)


if __name__ == "__main__":
    unittest.main()
