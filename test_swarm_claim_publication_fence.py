import copy
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

from tools.swarm_claim_publication_fence.core import (
    ValidationError,
    VerificationError,
    canonical_json,
    compile_snapshot,
    loads_strict_json,
    verify_compilation,
)

DIGEST = "1" * 64
CHANNEL = "C0BTRNE6Y58"


def claim(ts, seat="Z-Sol", author="U0BR9670G2H", *, work="OP-CUSTODY", role="SOURCE", digest=DIGEST):
    return {
        "work_key": work,
        "role": role,
        "scope_digest_sha256": digest,
        "channel_id": CHANNEL,
        "message_ts": ts,
        "author_id": author,
        "seat_id": seat,
    }


def snapshot(*, candidate_ts="1789674638.801299", history_claims=None, search_matches=None, complete=True):
    candidate = claim(candidate_ts)
    if history_claims is None:
        history_claims = [candidate]
    if search_matches is None:
        search_matches = [candidate]
    return {
        "schema_version": 1,
        "issued_at": "2026-09-17T19:51:00Z",
        "max_observation_age_seconds": 300,
        "identity": {"work_key": "OP-CUSTODY", "role": "SOURCE", "scope_digest_sha256": DIGEST},
        "candidate": {k: candidate[k] for k in ("channel_id", "message_ts", "author_id", "seat_id")},
        "history": {
            "channel_id": CHANNEL,
            "observed_at": "2026-09-17T19:50:50Z",
            "window_start_ts": "1789674500.000000",
            "window_end_ts": "1789674700.000000",
            "complete": complete,
            "claims": history_claims,
        },
        "search": {"observed_at": "2026-09-17T19:50:52Z", "matches": search_matches},
    }


class ClassificationTests(unittest.TestCase):
    def status(self, snap):
        return compile_snapshot(snap)[0]["classification"]

    def test_visible_earliest(self):
        c = self.status(snapshot())
        self.assertEqual(c["status"], "CANDIDATE_VISIBLE_EARLIEST")
        self.assertTrue(c["candidate_visible_in_history"])
        self.assertTrue(c["candidate_is_earliest"])
        self.assertFalse(c["index_divergence"])

    def test_incomplete_history_holds(self):
        self.assertEqual(self.status(snapshot(complete=False))["status"], "HOLD_NO_HISTORY_CENSUS")

    def test_candidate_not_visible_holds(self):
        other = claim("1789674639.000000", seat="Z-Other", author="UOTHER123")
        c = self.status(snapshot(history_claims=[other], search_matches=[other]))
        self.assertEqual(c["status"], "HOLD_CANDIDATE_NOT_VISIBLE")

    def test_earlier_claim_wins_even_when_search_misses_it(self):
        earlier = claim("1789674600.000001", seat="Z-Earlier", author="UEARLIER1")
        candidate = claim("1789674638.801299")
        c = self.status(snapshot(history_claims=[earlier, candidate], search_matches=[candidate]))
        self.assertEqual(c["status"], "HOLD_EARLIER_CLAIM")
        self.assertTrue(c["index_divergence"])
        self.assertEqual(c["earliest_claim"]["seat_id"], "Z-Earlier")

    def test_search_zero_while_candidate_visible_is_index_divergence(self):
        c = self.status(snapshot(search_matches=[]))
        self.assertEqual(c["status"], "HOLD_INDEX_DIVERGENCE")
        self.assertEqual(c["search_missing_message_ts"], ["1789674638.801299"])

    def test_search_message_absent_history_holds(self):
        candidate = claim("1789674638.801299")
        extra = claim("1789674640.000001", seat="Z-Ghost", author="UGHOST123")
        c = self.status(snapshot(history_claims=[candidate], search_matches=[candidate, extra]))
        self.assertEqual(c["status"], "HOLD_HISTORY_MISMATCH")
        self.assertEqual(c["search_extra_message_ts"], ["1789674640.000001"])

    def test_later_duplicate_does_not_displace_candidate(self):
        candidate = claim("1789674638.801299")
        later = claim("1789674640.000001", seat="Z-Later", author="ULATER123")
        c = self.status(snapshot(history_claims=[later, candidate], search_matches=[candidate, later]))
        self.assertEqual(c["status"], "CANDIDATE_VISIBLE_EARLIEST")
        self.assertEqual(c["material_history_claim_count"], 2)

    def test_unrelated_scope_does_not_collide(self):
        candidate = claim("1789674638.801299")
        unrelated = claim("1789674600.000001", seat="Z-Other", author="UOTHER123", digest="2" * 64)
        c = self.status(snapshot(history_claims=[unrelated, candidate], search_matches=[candidate]))
        self.assertEqual(c["status"], "CANDIDATE_VISIBLE_EARLIEST")

    def test_unrelated_role_does_not_collide(self):
        candidate = claim("1789674638.801299")
        unrelated = claim("1789674600.000001", seat="Z-Other", author="UOTHER123", role="REVIEW")
        c = self.status(snapshot(history_claims=[unrelated, candidate], search_matches=[candidate]))
        self.assertEqual(c["status"], "CANDIDATE_VISIBLE_EARLIEST")


class StrictnessTests(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ValidationError):
            loads_strict_json('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValidationError):
            loads_strict_json('{"a":NaN}')

    def test_unknown_root_field_rejected(self):
        snap = snapshot()
        snap["surprise"] = True
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_bool_as_int_rejected(self):
        snap = snapshot()
        snap["max_observation_age_seconds"] = True
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_malformed_slack_ts_rejected(self):
        snap = snapshot()
        snap["candidate"]["message_ts"] = "1789674638.1"
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_candidate_outside_window_rejected(self):
        snap = snapshot(candidate_ts="1789674800.000000", history_claims=[], search_matches=[])
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_future_observation_rejected(self):
        snap = snapshot()
        snap["history"]["observed_at"] = "2026-09-17T19:52:00Z"
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_stale_observation_rejected(self):
        snap = snapshot()
        snap["history"]["observed_at"] = "2026-09-17T19:40:00Z"
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_future_candidate_rejected(self):
        snap = snapshot(candidate_ts="1789674700.000000", history_claims=[], search_matches=[])
        snap["history"]["window_end_ts"] = "1789674800.000000"
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_stale_candidate_rejected(self):
        old = "1789674000.000000"
        row = claim(old)
        snap = snapshot(candidate_ts=old, history_claims=[row], search_matches=[row])
        snap["history"]["window_start_ts"] = "1789673900.000000"
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_history_claim_after_history_observation_rejected(self):
        row = claim("1789674655.000000")
        snap = snapshot(candidate_ts="1789674638.801299", history_claims=[claim("1789674638.801299"), row], search_matches=[claim("1789674638.801299")])
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_search_claim_after_search_observation_rejected(self):
        later = claim("1789674655.000000", seat="Z-Later", author="ULATER123")
        candidate = claim("1789674638.801299")
        snap = snapshot(history_claims=[candidate, later], search_matches=[candidate, later])
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_malformed_digest_rejected(self):
        snap = snapshot()
        snap["identity"]["scope_digest_sha256"] = "ABC"
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_earlier_claim_precedence_over_search_ghost(self):
        earlier = claim("1789674600.000001", seat="Z-Earlier", author="UEARLIER1")
        candidate = claim("1789674638.801299")
        ghost = claim("1789674640.000001", seat="Z-Ghost", author="UGHOST123")
        c = compile_snapshot(snapshot(history_claims=[earlier, candidate], search_matches=[candidate, ghost]))[0]["classification"]
        self.assertEqual(c["status"], "HOLD_EARLIER_CLAIM")

    def test_duplicate_history_message_identity_rejected(self):
        row = claim("1789674638.801299")
        snap = snapshot(history_claims=[row, copy.deepcopy(row)], search_matches=[row])
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_search_nonexact_identity_rejected(self):
        candidate = claim("1789674638.801299")
        wrong = claim("1789674638.801299", digest="2" * 64)
        snap = snapshot(history_claims=[candidate], search_matches=[wrong])
        with self.assertRaises(ValidationError):
            compile_snapshot(snap)

    def test_search_transplanted_same_message_detected_as_mismatch(self):
        candidate = claim("1789674638.801299")
        transplanted = claim("1789674638.801299", seat="Z-Forged", author="UFORGED12")
        c = compile_snapshot(snapshot(history_claims=[candidate], search_matches=[transplanted]))[0]["classification"]
        self.assertEqual(c["status"], "HOLD_HISTORY_MISMATCH")


class VerificationTests(unittest.TestCase):
    def test_exact_recompile_verifies(self):
        snap = snapshot()
        report, md, receipt = compile_snapshot(snap)
        verify_compilation(snap, report, md, receipt)

    def test_modified_report_rejected_even_if_receipt_rehashed(self):
        snap = snapshot()
        report, md, receipt = compile_snapshot(snap)
        forged = copy.deepcopy(report)
        forged["classification"]["status"] = "CANDIDATE_VISIBLE_EARLIEST" if report["classification"]["status"] != "CANDIDATE_VISIBLE_EARLIEST" else "HOLD_INDEX_DIVERGENCE"
        forged_receipt = copy.deepcopy(receipt)
        forged_receipt["report_json_sha256"] = hashlib.sha256(canonical_json(forged).encode()).hexdigest()
        with self.assertRaises(VerificationError):
            verify_compilation(snap, forged, md, forged_receipt)

    def test_modified_markdown_rejected(self):
        snap = snapshot()
        report, md, receipt = compile_snapshot(snap)
        with self.assertRaises(VerificationError):
            verify_compilation(snap, report, md + "forged\n", receipt)

    def test_cli_compile_verify_and_create_exclusive(self):
        snap = snapshot()
        with tempfile.TemporaryDirectory() as td:
            snapshot_path = os.path.join(td, "snapshot.json")
            prefix = os.path.join(td, "fence")
            with open(snapshot_path, "w", encoding="utf-8") as handle:
                handle.write(canonical_json(snap))
            env = dict(os.environ)
            env["PYTHONPATH"] = os.getcwd()
            command = [sys.executable, "-m", "tools.swarm_claim_publication_fence.cli", "compile", snapshot_path, prefix]
            first = subprocess.run(command, cwd=os.getcwd(), env=env, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            for suffix in (".report.json", ".report.md", ".receipt.json"):
                self.assertEqual(os.stat(prefix + suffix).st_mode & 0o777, 0o600)
            verify = subprocess.run(
                [sys.executable, "-m", "tools.swarm_claim_publication_fence.cli", "verify", snapshot_path, prefix + ".report.json", prefix + ".report.md", prefix + ".receipt.json"],
                cwd=os.getcwd(), env=env, text=True, capture_output=True,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertIn("VERIFIED", verify.stdout)
            second = subprocess.run(command, cwd=os.getcwd(), env=env, text=True, capture_output=True)
            self.assertEqual(second.returncode, 2)
            self.assertIn("File exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
