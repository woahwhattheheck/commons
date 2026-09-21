"""Regression coverage for outward identity and typed publication boundaries."""
from __future__ import annotations

import json
import unittest

from commons_publication_policy import (
    OUTBOUND_IDENTITY_TERMS,
    PublicationPolicyViolation,
    check_outbound_identity,
    check_publication,
)
from integrations.commons_publication_hooks.hook import (
    handle,
    private_feedback,
    publication_verdict,
)


def _event(tool: str, tool_input: dict, *, server: str = "github") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "mcp_server_name": server,
        "tool_input": tool_input,
    }


class OutboundIdentityBoundaryTests(unittest.TestCase):
    def test_each_exact_identity_term_is_blocked_with_private_correction(self):
        for term in OUTBOUND_IDENTITY_TERMS:
            with self.subTest(term=term):
                decision = check_outbound_identity(
                    {"title": f"[{term}] ship the patch"}
                )
                self.assertFalse(decision["allowed"])
                self.assertEqual(
                    decision["code"], "outbound_identity_attribution"
                )
                self.assertFalse(decision["delivered"])
                self.assertFalse(decision["incident"])
                self.assertEqual(decision["matched_fields"], ["title"])
                self.assertEqual(decision["matched_terms"], [term])
                self.assertIn(term, decision["private_instruction"])

    def test_identity_boundaries_normalization_and_invisible_format_controls(self):
        safe = "codexical claudeish opuscular fablet astraea resolution grokking"
        self.assertTrue(check_outbound_identity({"body": safe})["allowed"])
        self.assertEqual(
            check_outbound_identity({"body": "release_Astra_notes"})[
                "matched_terms"
            ],
            ["Astra"],
        )
        self.assertEqual(
            check_outbound_identity({"body": "Ａｓｔｒａ"})["matched_terms"],
            ["Astra"],
        )
        self.assertEqual(
            check_outbound_identity({"body": "A\u200bstra"})["matched_terms"],
            ["Astra"],
        )

    def test_policy_exception_exposes_private_structured_details(self):
        decision = check_outbound_identity({"body": "Prepared by Astra."})
        with self.assertRaises(PublicationPolicyViolation) as raised:
            raise PublicationPolicyViolation(decision)
        error = raised.exception
        self.assertEqual(error.code, "outbound_identity_attribution")
        self.assertFalse(error.incident)
        self.assertFalse(error.delivered)
        self.assertEqual(error.matched_fields, ("body",))
        self.assertEqual(error.matched_terms, ("Astra",))
        self.assertIn("retry", error.private_instruction)

    def test_gateway_checks_only_nested_authored_fields_not_private_envelope(self):
        body = (
            "The Python SDK now raises BoTTubeError when an HTTP error contains a "
            "non-object JSON value. Recorded validation on base "
            "e4dcd51fa42c1ca34f7738bf94ceb1cc37b6c2dd: the complete SDK test "
            "subset passed all 42 tests twice; the new cases produced 16 failures "
            "and 14 passes before the change. Related multi-claim tracker: #520."
        )
        event = _event(
            "commons_github_gateway",
            {
                "schema": "commons-github-gateway/v1",
                "operation_id": "Codex-Astra-private-control-id",
                "source_agent": "Claude",
                "operation": "pull.update",
                "args": {
                    "owner": "Scottcjn",
                    "repo": "bottube",
                    "pull_number": 2207,
                    "title": "Preserve Python SDK HTTP errors for non-object JSON",
                    "body": body,
                },
            },
            server="commons",
        )
        decision = publication_verdict(event)
        self.assertIsNotNone(decision)
        self.assertTrue(decision["allowed"])
        self.assertTrue(
            check_publication(
                body, "Preserve Python SDK HTTP errors"
            )["allowed"]
        )

    def test_gateway_blocks_term_only_when_it_enters_an_outward_field(self):
        event = _event(
            "commons_github_gateway",
            {
                "operation_id": "private-id",
                "operation": "pull.update",
                "args": {
                    "title": "[Astra] Preserve transport errors",
                    "body": "Implementation details.",
                },
            },
            server="commons",
        )
        decision = publication_verdict(event)
        self.assertIsNotNone(decision)
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["matched_fields"], ["title"])
        self.assertEqual(decision["matched_terms"], ["Astra"])

    def test_source_content_paths_and_control_payload_are_not_scanned(self):
        event = _event(
            "mcp__codex_apps__github_create_file",
            {
                "repository_full_name": "owner/repo",
                "path": "fixtures/Astra-response.json",
                "content": "Codex Claude Opus Fable Astra Sol Grok",
                "payload": {"source_agent": "Astra"},
                "message": "Add transport regression coverage",
            },
        )
        decision = publication_verdict(event)
        self.assertIsNotNone(decision)
        self.assertTrue(decision["allowed"])

    def test_raw_gateway_envelope_cannot_be_published_as_fallback_notification(self):
        envelope = {
            "schema": "commons-github-gateway/v1",
            "operation_id": "private-id",
            "operation": "pull.update",
            "args": {"title": "Neutral title", "body": "Neutral body"},
        }
        decision = publication_verdict(
            _event(
                "mcp__codex_apps__github_create_issue",
                {
                    "repository_full_name": "owner/repo",
                    "title": "Publication hold",
                    "body": json.dumps(envelope),
                },
            )
        )
        self.assertIsNotNone(decision)
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["code"], "private_control_envelope")
        self.assertEqual(decision["matched_fields"], ["body"])
        self.assertIn(
            "Do not create an issue", decision["private_instruction"]
        )

    def test_blocked_agent_receives_fields_terms_and_remove_instruction_privately(self):
        event = _event(
            "mcp__codex_apps__github_create_issue",
            {
                "repository_full_name": "owner/repo",
                "title": "Astra release note",
                "body": "Neutral details.",
            },
        )
        response = handle(event)
        output = response["hookSpecificOutput"]
        self.assertNotIn("continue", response)
        self.assertNotIn("suppressOutput", response)
        self.assertEqual(output["permissionDecision"], "deny")

        feedback = json.loads(output["permissionDecisionReason"])
        self.assertEqual(feedback["state"], "OUTBOUND_IDENTITY_BLOCKED")
        self.assertFalse(feedback["delivered"])
        self.assertFalse(feedback["incident"])
        self.assertEqual(feedback["matched_fields"], ["title"])
        self.assertEqual(feedback["matched_terms"], ["Astra"])
        self.assertTrue(feedback["instruction"].startswith("Remove Astra"))
        self.assertNotIn("Neutral details", output["permissionDecisionReason"])


    def test_connector_comment_label_and_dismissal_fields_are_typed(self):
        cases = (
            ("mcp__codex_apps__github_add_issue_comment", {"body": "Astra note"}, "body"),
            ("mcp__codex_apps__github_label_pr", {"label": "Astra"}, "label"),
            (
                "mcp__codex_apps__github_dismiss_pull_request_review",
                {"message": "Astra dismissal"},
                "message",
            ),
        )
        for tool, args, field in cases:
            with self.subTest(tool=tool):
                decision = publication_verdict(_event(tool, args))
                self.assertFalse(decision["allowed"])
                self.assertEqual(decision["matched_fields"], [field])
                self.assertEqual(decision["matched_terms"], ["Astra"])

        removal = publication_verdict(
            _event("mcp__codex_apps__github_remove_issue_label", {"label": "Astra"})
        )
        self.assertTrue(removal["allowed"])

    def test_gateway_unknown_malformed_and_empty_mutations_fail_closed(self):
        cases = (
            {"schema": "commons-github-gateway/v1", "operation": "pull.archive", "args": {}},
            {"schema": "commons-github-gateway/v1", "operation": "pull.update", "args": "private"},
            {"schema": "commons-github-gateway/v1", "operation": "pull.update", "args": {}},
        )
        for payload in cases:
            with self.subTest(payload=payload):
                decision = publication_verdict(
                    _event("commons_github_gateway", payload, server="commons")
                )
                self.assertFalse(decision["allowed"])
                self.assertEqual(decision["code"], "outbound_field_mapping_missing")

    def test_gateway_labels_and_inline_review_bodies_are_checked(self):
        label = publication_verdict(
            _event(
                "commons_github_gateway",
                {
                    "schema": "commons-github-gateway/v1",
                    "operation": "issue.update",
                    "args": {"labels": ["Astra"]},
                },
                server="commons",
            )
        )
        self.assertEqual(label["matched_fields"], ["labels[0]"])

        review = publication_verdict(
            _event(
                "commons_github_gateway",
                {
                    "schema": "commons-github-gateway/v1",
                    "operation": "pull.review.create",
                    "args": {
                        "body": "Neutral review.",
                        "file_comments": [{"body": "Astra note"}],
                    },
                },
                server="commons",
            )
        )
        self.assertEqual(review["matched_fields"], ["file_comments[0].body"])

    def test_direct_merge_requires_explicit_checked_metadata(self):
        for args in (
            {"merge_method": "rebase"},
            {"merge_method": "squash"},
            {"merge_method": "merge", "commit_title": "Neutral"},
        ):
            with self.subTest(args=args):
                decision = publication_verdict(
                    _event("mcp__codex_apps__github_merge_pull_request", args)
                )
                self.assertFalse(decision["allowed"])
                self.assertEqual(decision["code"], "outbound_field_mapping_missing")

        allowed = publication_verdict(
            _event(
                "mcp__codex_apps__github_merge_pull_request",
                {
                    "merge_method": "squash",
                    "commit_title": "Integrate change",
                    "commit_message": "Integrate the reviewed change.",
                },
            )
        )
        self.assertTrue(allowed["allowed"])

    def test_wrapped_private_envelope_is_not_published(self):
        envelope = {
            "schema": "commons-github-gateway/v1",
            "operation_id": "private-id",
            "operation": "pull.update",
            "args": {"title": "Neutral", "body": "Neutral"},
        }
        decision = publication_verdict(
            _event(
                "mcp__codex_apps__github_create_issue",
                {
                    "title": "Neutral title",
                    "body": "Diagnostic follows: " + json.dumps(envelope),
                },
            )
        )
        self.assertEqual(decision["code"], "private_control_envelope")
        self.assertEqual(decision["matched_fields"], ["body"])

    def test_private_feedback_never_echoes_rejected_content(self):
        decision = check_outbound_identity({"body": "secret Astra material"})
        feedback = private_feedback(decision)
        self.assertNotIn("secret", feedback)
        self.assertIn('"delivered":false', feedback)
        self.assertIn('"incident":false', feedback)

    def test_chat_writes_are_read_only_until_sender_identity_is_verified(self):
        write = publication_verdict(
            _event(
                "mcp__codex_apps__slack_slack_send_message",
                {"channel_id": "C1", "message": "Neutral status."},
                server="slack",
            )
        )
        self.assertIsNotNone(write)
        self.assertFalse(write["allowed"])
        self.assertEqual(
            write["code"], "outbound_sender_identity_unverified"
        )

        read = publication_verdict(
            _event(
                "mcp__codex_apps__slack_slack_read_channel",
                {"channel_id": "C1"},
                server="slack",
            )
        )
        self.assertIsNone(read)

    def test_unknown_mutating_managed_route_fails_closed_without_notification(self):
        decision = publication_verdict(
            _event(
                "commons_future_publish",
                {
                    "payload": {"body": "Astra"},
                    "operation": "future.publish",
                },
                server="commons",
            )
        )
        self.assertIsNotNone(decision)
        self.assertFalse(decision["allowed"])
        self.assertEqual(
            decision["code"], "outbound_field_mapping_missing"
        )
        self.assertEqual(decision["matched_fields"], [])
        self.assertEqual(decision["matched_terms"], [])
        self.assertIn(
            "fallback notification", decision["private_instruction"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
