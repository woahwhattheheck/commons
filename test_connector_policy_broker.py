import hashlib
import unittest

from host.connector_policy_broker import Policy, PolicyError, authorize, canary_policy, verify_decision


class PolicyBrokerTests(unittest.TestCase):
    def setUp(self):
        self.policy = Policy(
            policy_version="test/v1",
            github_repositories=frozenset({"acme/widgets"}),
            github_branch_prefixes=("agent/",),
            github_path_prefixes=("src/", ".github/workflows/"),
            slack_channel_ids=frozenset({"C0123456789"}),
        )

    def req(self, action, **kwargs):
        return {"action": action, "correlation_id": "run-123", **kwargs}

    def test_create_branch_requires_exact_base_sha_and_nondefault_prefix(self):
        good = self.req("github.create_branch", repository="acme/widgets", branch="agent/fix", base_sha="a" * 40)
        self.assertTrue(authorize(good, self.policy).allowed)
        self.assertEqual("BASE_SHA_REQUIRED", authorize({**good, "base_sha": "main"}, self.policy).code)
        self.assertEqual("DEFAULT_BRANCH_DIRECT_WRITE_DENIED", authorize({**good, "branch": "main"}, self.policy).code)
        self.assertEqual("BRANCH_PREFIX_NOT_ALLOWED", authorize({**good, "branch": "feature/fix"}, self.policy).code)

    def test_commit_is_expected_head_nonforce_and_path_bounded(self):
        good = self.req(
            "github.commit_files",
            repository="acme/widgets",
            branch="agent/fix",
            expected_head_sha="b" * 40,
            force=False,
            files=[{"path": "src/a.py", "content_utf8": "print('ok')\n"}],
            human_approval=False,
        )
        self.assertTrue(authorize(good, self.policy).allowed)
        self.assertEqual("FORCE_UPDATE_DENIED", authorize({**good, "force": True}, self.policy).code)
        self.assertEqual("EXPECTED_HEAD_SHA_REQUIRED", authorize({**good, "expected_head_sha": ""}, self.policy).code)
        bad = {**good, "files": [{"path": "docs/a.md", "content_utf8": "x"}]}
        self.assertEqual("PATH_PREFIX_NOT_ALLOWED", authorize(bad, self.policy).code)

    def test_path_traversal_and_duplicates_fail_closed(self):
        base = self.req(
            "github.commit_files",
            repository="acme/widgets",
            branch="agent/fix",
            expected_head_sha="b" * 40,
            force=False,
            human_approval=False,
        )
        traversal = {**base, "files": [{"path": "src/../secret", "content_utf8": "x"}]}
        self.assertEqual("INVALID_REQUEST", authorize(traversal, self.policy).code)
        dup = {**base, "files": [
            {"path": "src/a", "content_utf8": "x"},
            {"path": "src/a", "content_utf8": "y"},
        ]}
        self.assertEqual("DUPLICATE_PATH", authorize(dup, self.policy).code)

    def test_workflow_write_is_separate_authority(self):
        req = self.req(
            "github.commit_files",
            repository="acme/widgets",
            branch="agent/fix",
            expected_head_sha="b" * 40,
            force=False,
            files=[{"path": ".github/workflows/x.yml", "content_utf8": "name: x\n"}],
            human_approval=False,
        )
        self.assertEqual("WORKFLOW_WRITE_DENIED", authorize(req, self.policy).code)
        elevated = Policy(
            policy_version="elevated/v1",
            github_repositories=frozenset({"acme/widgets"}),
            github_branch_prefixes=("agent/",),
            github_path_prefixes=(".github/workflows/",),
            allow_workflow_writes=True,
        )
        self.assertEqual("WORKFLOW_HUMAN_APPROVAL_REQUIRED", authorize(req, elevated).code)
        self.assertTrue(authorize({**req, "human_approval": True}, elevated).allowed)

    def test_pull_request_can_be_forced_to_draft_default_base(self):
        req = self.req("github.create_pull_request", repository="acme/widgets", head="agent/fix", base="main", draft=True)
        self.assertTrue(authorize(req, self.policy).allowed)
        self.assertEqual("DRAFT_PR_REQUIRED", authorize({**req, "draft": False}, self.policy).code)
        self.assertEqual("BASE_BRANCH_NOT_ALLOWED", authorize({**req, "base": "release"}, self.policy).code)

    def test_slack_messages_require_allowed_channel_and_no_unfurl(self):
        req = self.req(
            "slack.post_message",
            channel_id="C0123456789",
            text="connector canary",
            unfurl_links=False,
            unfurl_media=False,
        )
        self.assertTrue(authorize(req, self.policy).allowed)
        self.assertEqual("CHANNEL_NOT_ALLOWED", authorize({**req, "channel_id": "C9999999999"}, self.policy).code)
        self.assertEqual("UNFURL_MUST_BE_DISABLED", authorize({**req, "unfurl_links": True}, self.policy).code)

    def test_slack_file_requires_length_and_digest(self):
        req = self.req(
            "slack.upload_file",
            channel_id="C0123456789",
            filename="canary.txt",
            size_bytes=3,
            sha256=hashlib.sha256(b"abc").hexdigest(),
        )
        self.assertTrue(authorize(req, self.policy).allowed)
        self.assertEqual("FILENAME_INVALID", authorize({**req, "filename": "../x"}, self.policy).code)
        self.assertEqual("FILE_SHA256_REQUIRED", authorize({**req, "sha256": "x"}, self.policy).code)

    def test_unknown_fields_are_rejected(self):
        req = self.req("github.create_branch", repository="acme/widgets", branch="agent/x", base_sha="a" * 40, token="secret")
        self.assertEqual("SCHEMA_MISMATCH", authorize(req, self.policy).code)

    def test_non_strict_json_is_rejected(self):
        req = self.req("slack.post_message", channel_id="C0123456789", text="x", unfurl_links=False, unfurl_media=False)
        req["extra"] = 1.5
        self.assertEqual("REQUEST_NOT_STRICT_JSON", authorize(req, self.policy).code)

    def test_receipt_is_deterministic_and_recomputable(self):
        req = self.req("github.create_branch", repository="acme/widgets", branch="agent/fix", base_sha="a" * 40)
        first = authorize(req, self.policy).as_dict()
        second = authorize(dict(reversed(list(req.items()))), self.policy).as_dict()
        self.assertEqual(first, second)
        self.assertTrue(verify_decision(req, self.policy, first))
        tampered = {**first, "allowed": False}
        self.assertFalse(verify_decision(req, self.policy, tampered))

    def test_canary_profile_is_narrow(self):
        policy = canary_policy(repository="acme/canary", slack_channel_id="C0123456789")
        good = {
            "action": "github.commit_files", "correlation_id": "canary-1",
            "repository": "acme/canary", "branch": "agent-canary/1", "expected_head_sha": "c" * 40,
            "force": False, "human_approval": False,
            "files": [{"path": ".connector-canary/1.txt", "content_utf8": "ok"}],
        }
        self.assertTrue(authorize(good, policy).allowed)
        self.assertEqual("PATH_PREFIX_NOT_ALLOWED", authorize({**good, "files": [{"path": "README.md", "content_utf8": "x"}]}, policy).code)

    def test_policy_rejects_malformed_configuration(self):
        with self.assertRaises(PolicyError):
            Policy(policy_version="x", github_repositories=frozenset({"not-a-repo"}))
        with self.assertRaises(PolicyError):
            Policy(policy_version="x", github_path_prefixes=("src",))
        with self.assertRaises(PolicyError):
            Policy(policy_version="x", max_file_bytes=True)


if __name__ == "__main__":
    unittest.main()
