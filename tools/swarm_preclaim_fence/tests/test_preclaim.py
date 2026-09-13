# SPDX-License-Identifier: MIT
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.swarm_preclaim_fence.preclaim import PreclaimInputError, evaluate_preclaim

A = "a" * 40
B = "b" * 40
C = "c" * 40


def request(**overrides):
    value = {
        "owner_fork": "woahwhattheheck/tarsnap",
        "upstream_pr_or_issue": "Tarsnap/tarsnap#836",
        "stable_id": "TARSNAP-836-FOO",
        "candidate_paths": ["lib/foo.c", "tests/foo_test.sh"],
        "semantic_phrases": ["foo resync"],
    }
    value.update(overrides)
    return value


def slice_(hits=None, complete=True):
    return {"complete": complete, "hits": list(hits or [])}


def evidence():
    return {
        "slack": {
            "stable_id": slice_(),
            "upstream_ref": slice_(),
            "candidate_paths": {
                "lib/foo.c": slice_(),
                "tests/foo_test.sh": slice_(),
            },
            "semantic_phrases": {"foo resync": slice_()},
        },
        "github": {
            "owner_open_prs": slice_(),
            "paths": {
                "lib/foo.c": {
                    "complete": True,
                    "owner_default_sha": A,
                    "upstream_base_sha": A,
                    "upstream_head_sha": B,
                },
                "tests/foo_test.sh": {
                    "complete": True,
                    "owner_default_sha": None,
                    "upstream_base_sha": None,
                    "upstream_head_sha": C,
                },
            },
        },
    }


class PreclaimFenceTests(unittest.TestCase):
    def test_stable_id_empty_but_exact_pr_number_hit_is_owned(self):
        ev = evidence()
        ev["slack"]["upstream_ref"] = slice_(
            [{"id": "1789.1", "channel_id": "C1", "ts": "1789.1"}]
        )
        got = evaluate_preclaim(request(), ev)
        self.assertEqual(got["decision"], "OWNED")
        self.assertIn("SLACK_UPSTREAM_REF_HIT", got["reasons"])

    def test_exact_head_on_owner_default_is_already_absorbed(self):
        ev = evidence()
        for row in ev["github"]["paths"].values():
            row["owner_default_sha"] = row["upstream_head_sha"]
        got = evaluate_preclaim(request(), ev)
        self.assertEqual(got["decision"], "ALREADY_ABSORBED")
        self.assertEqual(
            {row["status"] for row in got["path_status"].values()}, {"EXACT_HEAD"}
        )

    def test_absorbed_beats_stale_open_pr_hit(self):
        ev = evidence()
        for row in ev["github"]["paths"].values():
            row["owner_default_sha"] = row["upstream_head_sha"]
        ev["github"]["owner_open_prs"] = slice_(
            [{"id": "pr-15", "repo": "woahwhattheheck/tarsnap", "number": 15}]
        )
        got = evaluate_preclaim(request(), ev)
        self.assertEqual(got["decision"], "ALREADY_ABSORBED")

    def test_diverged_path_requires_manual_diff(self):
        ev = evidence()
        ev["github"]["paths"]["lib/foo.c"]["owner_default_sha"] = C
        got = evaluate_preclaim(request(), ev)
        self.assertEqual(got["decision"], "NEEDS_MANUAL_DIFF")
        self.assertIn("DIVERGED_CANDIDATE_PATH", got["reasons"])

    def test_partial_head_absorption_requires_manual_diff(self):
        ev = evidence()
        ev["github"]["paths"]["lib/foo.c"]["owner_default_sha"] = B
        got = evaluate_preclaim(request(), ev)
        self.assertEqual(got["decision"], "NEEDS_MANUAL_DIFF")
        self.assertIn("PARTIAL_HEAD_ABSORPTION", got["reasons"])

    def test_clean_base_and_missing_paths_are_safe(self):
        got = evaluate_preclaim(request(), evidence())
        self.assertEqual(got["decision"], "SAFE_TO_BIND_BRANCH")
        self.assertEqual(got["mutations_performed"], [])
        self.assertEqual(got["path_status"]["lib/foo.c"]["status"], "EXACT_BASE")
        self.assertEqual(got["path_status"]["tests/foo_test.sh"]["status"], "MISSING")

    def test_owner_open_pr_hit_is_owned(self):
        ev = evidence()
        ev["github"]["owner_open_prs"] = slice_(
            [{
                "id": "owner-pr-22",
                "url": "https://github.com/woahwhattheheck/tarsnap/pull/22",
                "repo": "woahwhattheheck/tarsnap",
                "number": 22,
                "overlap_paths": ["lib/foo.c"],
            }]
        )
        got = evaluate_preclaim(request(), ev)
        self.assertEqual(got["decision"], "OWNED")
        self.assertIn("OWNER_FORK_OPEN_PR_HIT", got["reasons"])

    def test_candidate_path_slack_hit_is_owned(self):
        ev = evidence()
        ev["slack"]["candidate_paths"]["lib/foo.c"] = slice_(
            [{"id": "m-1", "channel_id": "C0", "ts": "1.0"}]
        )
        got = evaluate_preclaim(request(), ev)
        self.assertEqual(got["decision"], "OWNED")
        self.assertIn("SLACK_CANDIDATE_PATH_HIT", got["reasons"])

    def test_semantic_phrase_slack_hit_is_owned(self):
        ev = evidence()
        ev["slack"]["semantic_phrases"]["foo resync"] = slice_(
            [{"id": "m-2", "channel_id": "C0", "ts": "2.0"}]
        )
        got = evaluate_preclaim(request(), ev)
        self.assertEqual(got["decision"], "OWNED")
        self.assertIn("SLACK_SEMANTIC_PHRASE_HIT", got["reasons"])

    def test_incomplete_evidence_fails_closed(self):
        ev = evidence()
        ev["slack"]["upstream_ref"]["complete"] = False
        got = evaluate_preclaim(request(), ev)
        self.assertEqual(got["decision"], "NEEDS_MANUAL_DIFF")
        self.assertIn("EVIDENCE_INCOMPLETE", got["reasons"])

    def test_raw_slack_text_is_rejected_from_receipt(self):
        ev = evidence()
        ev["slack"]["upstream_ref"] = slice_(
            [{"id": "m-3", "text": "workspace secret-ish body"}]
        )
        with self.assertRaises(PreclaimInputError):
            evaluate_preclaim(request(), ev)

    def test_path_traversal_is_rejected(self):
        req = request(candidate_paths=["../outside"])
        with self.assertRaises(PreclaimInputError):
            evaluate_preclaim(req, evidence())

    def test_duplicate_candidate_path_is_rejected(self):
        req = request(candidate_paths=["lib/foo.c", "lib/foo.c"])
        with self.assertRaises(PreclaimInputError):
            evaluate_preclaim(req, evidence())

    def test_missing_required_query_slice_is_rejected(self):
        ev = evidence()
        del ev["slack"]["upstream_ref"]
        with self.assertRaises(PreclaimInputError):
            evaluate_preclaim(request(), ev)

    def test_no_stable_id_requires_no_fake_stable_query(self):
        req = request(stable_id=None)
        ev = evidence()
        del ev["slack"]["stable_id"]
        got = evaluate_preclaim(req, ev)
        self.assertEqual(got["decision"], "SAFE_TO_BIND_BRANCH")
        self.assertEqual(got["slack_hits"]["stable_id"], [])

    def test_receipt_hash_is_deterministic(self):
        one = evaluate_preclaim(request(), evidence())
        two = evaluate_preclaim(copy.deepcopy(request()), copy.deepcopy(evidence()))
        self.assertEqual(one["receipt_sha256"], two["receipt_sha256"])

    def test_cli_returns_nonzero_for_non_safe_decision(self):
        req = request()
        ev = evidence()
        ev["slack"]["upstream_ref"] = slice_([{"id": "owned"}])
        with tempfile.TemporaryDirectory() as td:
            req_path = Path(td) / "request.json"
            ev_path = Path(td) / "evidence.json"
            req_path.write_text(json.dumps(req), encoding="utf-8")
            ev_path.write_text(json.dumps(ev), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.swarm_preclaim_fence.preclaim",
                    "--request",
                    str(req_path),
                    "--evidence",
                    str(ev_path),
                ],
                cwd=Path(__file__).resolve().parents[3],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(json.loads(proc.stdout)["decision"], "OWNED")


if __name__ == "__main__":
    unittest.main()
