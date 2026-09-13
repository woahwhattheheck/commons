import copy
import unittest
from datetime import datetime, timezone

from gate import GateInputError, evaluate, sha256_json

NOW = datetime(2026, 9, 13, 8, 45, 0, tzinfo=timezone.utc)


def manifest(effect="external"):
    request = {
        "tool": "github",
        "operation": "merge_pull_request",
        "effect": effect,
        "target": "woahwhattheheck/example#42",
        "payload": {"expected_head": "abc123", "strategy": "squash"},
        "payload_sha256": "",
    }
    request["payload_sha256"] = sha256_json(request["payload"])
    request_sha = sha256_json(request)
    result = {
        "version": 1,
        "run_id": "run-42",
        "agent_id": "worker-z",
        "snapshot_at": "2026-09-13T08:44:30Z",
        "request": request,
        "policy": {
            "capabilities": [{"tool": "github", "operation": "merge_pull_request", "effect": effect, "target_prefix": "woahwhattheheck/"}],
            "required_checks": ["unit", "graph"],
            "approval_required_effects": ["write", "external"],
            "approvers": ["owner"],
            "effect_budget": {"read": 100, "write": 10, "external": 2},
            "max_snapshot_age_seconds": 120,
            "max_future_skew_seconds": 5,
            "max_check_age_seconds": 180,
            "decision_ttl_seconds": 60,
        },
        "evidence": {
            "checks": {
                "unit": {"status": "pass", "subject_sha256": request_sha, "observed_at": "2026-09-13T08:44:40Z"},
                "graph": {"status": "pass", "subject_sha256": request_sha, "observed_at": "2026-09-13T08:44:50Z"},
            },
            "completed_effects": [],
        },
    }
    if effect in {"write", "external"}:
        result["approval"] = {
            "approval_id": "approval-42",
            "actor": "owner",
            "request_sha256": request_sha,
            "issued_at": "2026-09-13T08:44:20Z",
            "expires_at": "2026-09-13T08:46:00Z",
        }
    return result


def refresh_subjects(value):
    request_sha = sha256_json(value["request"])
    for check in value["evidence"]["checks"].values():
        check["subject_sha256"] = request_sha
    if "approval" in value:
        value["approval"]["request_sha256"] = request_sha
    return request_sha


class GateTests(unittest.TestCase):
    def test_valid_external_release(self):
        receipt = evaluate(manifest(), NOW)
        self.assertEqual(receipt["decision"], "RELEASE")
        self.assertEqual(receipt["reasons"], [])
        self.assertEqual(receipt["release_expires_at"], "2026-09-13T08:46:00Z")

    def test_read_can_release_without_approval(self):
        m = manifest("read")
        self.assertEqual(evaluate(m, NOW)["decision"], "RELEASE")
        self.assertNotIn("approval", m)

    def test_stale_snapshot_holds(self):
        m = manifest(); m["snapshot_at"] = "2026-09-13T08:42:59Z"
        self.assertIn("STALE_SNAPSHOT", evaluate(m, NOW)["reasons"])

    def test_future_snapshot_holds(self):
        m = manifest(); m["snapshot_at"] = "2026-09-13T08:45:06Z"
        self.assertIn("SNAPSHOT_FROM_FUTURE", evaluate(m, NOW)["reasons"])

    def test_payload_hash_mismatch_holds(self):
        m = manifest(); m["request"]["payload"]["strategy"] = "merge"; refresh_subjects(m)
        self.assertIn("PAYLOAD_HASH_MISMATCH", evaluate(m, NOW)["reasons"])

    def test_disallowed_capability_dimensions_hold(self):
        for field, value in [("tool", "slack"), ("operation", "delete_repo"), ("effect", "write"), ("target", "other/example#42")]:
            with self.subTest(field=field):
                m = manifest(); m["request"][field] = value; refresh_subjects(m)
                self.assertIn("CAPABILITY_NOT_ALLOWED", evaluate(m, NOW)["reasons"])

    def test_missing_required_check_holds(self):
        m = manifest(); del m["evidence"]["checks"]["graph"]
        self.assertIn("CHECK_MISSING:graph", evaluate(m, NOW)["reasons"])

    def test_failed_check_holds(self):
        m = manifest(); m["evidence"]["checks"]["unit"]["status"] = "fail"
        self.assertIn("CHECK_NOT_PASS:unit", evaluate(m, NOW)["reasons"])

    def test_check_subject_mismatch_holds(self):
        m = manifest(); m["evidence"]["checks"]["unit"]["subject_sha256"] = "0" * 64
        self.assertIn("CHECK_SUBJECT_MISMATCH:unit", evaluate(m, NOW)["reasons"])

    def test_stale_and_future_checks_hold(self):
        m = manifest(); m["evidence"]["checks"]["unit"]["observed_at"] = "2026-09-13T08:41:59Z"
        self.assertIn("CHECK_STALE:unit", evaluate(m, NOW)["reasons"])
        m = manifest(); m["evidence"]["checks"]["unit"]["observed_at"] = "2026-09-13T08:45:06Z"
        self.assertIn("CHECK_FROM_FUTURE:unit", evaluate(m, NOW)["reasons"])

    def test_missing_approval_holds(self):
        m = manifest(); del m["approval"]
        self.assertIn("APPROVAL_MISSING", evaluate(m, NOW)["reasons"])

    def test_unapproved_actor_holds(self):
        m = manifest(); m["approval"]["actor"] = "stranger"
        self.assertIn("APPROVER_NOT_ALLOWED", evaluate(m, NOW)["reasons"])

    def test_approval_scope_mismatch_holds(self):
        m = manifest(); m["approval"]["request_sha256"] = "f" * 64
        self.assertIn("APPROVAL_SCOPE_MISMATCH", evaluate(m, NOW)["reasons"])

    def test_expired_approval_holds(self):
        m = manifest(); m["approval"]["expires_at"] = "2026-09-13T08:45:00Z"
        self.assertIn("APPROVAL_EXPIRED", evaluate(m, NOW)["reasons"])

    def test_future_approval_holds(self):
        m = manifest(); m["approval"]["issued_at"] = "2026-09-13T08:45:06Z"
        self.assertIn("APPROVAL_FROM_FUTURE", evaluate(m, NOW)["reasons"])

    def test_invalid_approval_interval_holds(self):
        m = manifest(); m["approval"]["issued_at"] = "2026-09-13T08:44:50Z"; m["approval"]["expires_at"] = "2026-09-13T08:44:50Z"
        self.assertIn("APPROVAL_INVALID_INTERVAL", evaluate(m, NOW)["reasons"])

    def test_duplicate_effect_holds(self):
        m = manifest(); request_sha = sha256_json(m["request"])
        m["evidence"]["completed_effects"].append({"effect_id": "effect-1", "effect": "external", "request_sha256": request_sha, "status": "committed"})
        self.assertIn("ALREADY_EFFECTED", evaluate(m, NOW)["reasons"])

    def test_effect_budget_holds(self):
        m = manifest(); m["policy"]["effect_budget"]["external"] = 1
        m["evidence"]["completed_effects"].append({"effect_id": "effect-1", "effect": "external", "request_sha256": "0" * 64, "status": "committed"})
        self.assertIn("EFFECT_BUDGET_EXHAUSTED", evaluate(m, NOW)["reasons"])

    def test_zero_budget_holds_even_with_no_prior_effects(self):
        m = manifest(); m["policy"]["effect_budget"]["external"] = 0
        self.assertIn("EFFECT_BUDGET_EXHAUSTED", evaluate(m, NOW)["reasons"])

    def test_receipt_is_deterministic_for_same_trusted_time(self):
        self.assertEqual(evaluate(manifest(), NOW), evaluate(manifest(), NOW))

    def test_receipt_is_bound_to_request(self):
        a = manifest(); b = copy.deepcopy(a); b["request"]["target"] = "woahwhattheheck/example#43"; refresh_subjects(b)
        self.assertNotEqual(evaluate(a, NOW)["request_sha256"], evaluate(b, NOW)["request_sha256"])

    def test_release_expiry_clamps_to_freshness_boundary(self):
        m = manifest(); m["policy"]["decision_ttl_seconds"] = 600; m["approval"]["expires_at"] = "2026-09-13T09:00:00Z"
        self.assertEqual(evaluate(m, NOW)["release_expires_at"], "2026-09-13T08:46:30Z")

    def test_naive_evaluation_clock_rejected(self):
        with self.assertRaises(GateInputError): evaluate(manifest(), datetime(2026, 9, 13, 8, 45, 0))

    def test_duplicate_effect_ids_rejected(self):
        m = manifest(); item = {"effect_id": "same", "effect": "read", "request_sha256": "0" * 64, "status": "committed"}; m["evidence"]["completed_effects"] = [item, copy.deepcopy(item)]
        with self.assertRaises(GateInputError): evaluate(m, NOW)

    def test_unknown_completed_effect_status_rejected(self):
        m = manifest(); m["evidence"]["completed_effects"] = [{"effect_id": "e", "effect": "read", "request_sha256": "0" * 64, "status": "pending"}]
        with self.assertRaises(GateInputError): evaluate(m, NOW)

    def test_malformed_timestamp_rejected(self):
        m = manifest(); m["snapshot_at"] = "yesterday"
        with self.assertRaises(GateInputError): evaluate(m, NOW)


if __name__ == "__main__":
    unittest.main()
