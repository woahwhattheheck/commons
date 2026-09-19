"""Recovery regressions for #15801: reference, time and damaged-record behavior.

Only disposable local fixture repositories are used. No provider or network calls.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import completion_projection as cp

OP = "COMPLETION-RECOVERY-FIXTURE-0001"
OTHER = "COMPLETION-RECOVERY-FIXTURE-0002"


class CompletionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "p").mkdir()
        self.source = self.root / cp.source_rel(OP)
        self.source.write_text("---\nfrom: UNSEATED\nto: TABLE\nid: " + OP + "\n---\nfixture\n")
        self.source_digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.issue = {
            "number": 15130, "state": "closed", "state_reason": "completed",
            "closed_at": "2026-09-17T00:41:27Z",
            "html_url": "https://github.com/woahwhattheheck/commons/issues/15130",
        }
        self.pr = {
            "number": 15138, "merged": True, "merged_at": "2026-09-17T00:41:26Z",
            "merge_commit_sha": "c" * 40, "base": {"ref": "main"},
            "body": "Closes #15130.",
            "html_url": "https://github.com/woahwhattheheck/commons/pull/15138",
        }
        self.path = self.root / cp.marker_rel(OP)
        self.path.parent.mkdir(parents=True)

    def tearDown(self):
        self.assertEqual(self.source_digest, hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.temp.cleanup()

    @staticmethod
    def ancestor(sha):
        return sha == "c" * 40

    def marker(self):
        return cp.build_marker(self.root, OP, self.issue, self.pr)

    def store(self, row):
        self.path.write_text(json.dumps(row), encoding="utf-8")

    def test_documented_keyword_reference_matrix(self):
        keywords = ("close", "closes", "closed", "fix", "fixes", "fixed", "resolve", "resolves", "resolved")
        references = ("#15130", "woahwhattheheck/commons#15130", "https://github.com/woahwhattheheck/commons/issues/15130")
        for keyword in keywords:
            for reference in references:
                for separator in (" ", ": ", " : ", "\n"):
                    body = keyword.upper() + separator + reference + "."
                    with self.subTest(body=body):
                        self.assertTrue(cp.closing_keyword_mentions_issue(body, 15130))

    def test_bare_numbers_and_missing_hashes_do_not_close(self):
        for body in ("Closes 15130", "Fixes woahwhattheheck/commons15130", "Resolves: 15130", "Closes: woahwhattheheck/commons15130"):
            with self.subTest(body=body):
                self.assertFalse(cp.closing_keyword_mentions_issue(body, 15130))
                with self.assertRaises(cp.CompletionEvidenceError):
                    cp.build_marker(self.root, OP, self.issue, dict(self.pr, body=body))

    def test_other_repository_or_issue_does_not_close(self):
        for body in ("Closes other/repo#15130", "Closes https://github.com/other/repo/issues/15130", "Closes #151300", "Closes #15130a", "Discusses #15130", "Disclosure #15130"):
            with self.subTest(body=body):
                self.assertFalse(cp.closing_keyword_mentions_issue(body, 15130))

    def test_colon_reference_builds_a_usable_marker(self):
        marker = cp.build_marker(self.root, OP, self.issue, dict(self.pr, body="CLOSES: #15130"))
        cp.write_marker(self.root, marker, self.ancestor)
        self.assertEqual(frozenset({OP}), cp.completed_operation_ids(self.root, self.ancestor))

    def test_invalid_issue_number_types_do_not_match(self):
        for value in (None, True, False, 0, -1, 15130.0, "15130", [], {}):
            with self.subTest(value=value):
                self.assertFalse(cp.closing_keyword_mentions_issue("Closes #15130", value))

    def test_malformed_timestamp_matrix_cannot_build(self):
        values = (None, False, [], {}, "", "aaa", "2026-09-17", "2026-09-17T00:41:26", "2026-02-30T00:00:00Z", "2026-09-17T25:00:00Z", "2026-09-17T00:41:26+99:00")
        for value in values:
            with self.subTest(value=value, field="closed_at"):
                with self.assertRaises(cp.CompletionEvidenceError):
                    cp.build_marker(self.root, OP, dict(self.issue, closed_at=value), self.pr)
            with self.subTest(value=value, field="merged_at"):
                with self.assertRaises(cp.CompletionEvidenceError):
                    cp.build_marker(self.root, OP, self.issue, dict(self.pr, merged_at=value))

    def test_malformed_persisted_times_do_not_hide_work(self):
        marker = self.marker()
        marker["issue"]["closed_at"] = "zzz"
        marker["merge"]["merged_at"] = "aaa"
        self.store(marker)
        self.assertFalse(cp.marker_is_valid(self.root, marker, self.ancestor))
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))

    def test_offset_order_uses_instants_not_lexicographic_order(self):
        # 02:00+02 is 00:00Z: it precedes 01:00Z despite its lexical ordering.
        issue = dict(self.issue, closed_at="2026-09-17T01:00:00Z")
        pr = dict(self.pr, merged_at="2026-09-17T02:00:00+02:00")
        marker = cp.build_marker(self.root, OP, issue, pr)
        self.assertTrue(cp.marker_is_valid(self.root, marker, self.ancestor))
        self.assertEqual(pr["merged_at"], marker["merge"]["merged_at"])

    def test_lexically_earlier_but_chronologically_later_merge_rejected(self):
        issue = dict(self.issue, closed_at="2026-09-17T01:00:00Z")
        pr = dict(self.pr, merged_at="2026-09-17T00:30:00-02:00")
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, issue, pr)
        marker = self.marker()
        marker["issue"]["closed_at"] = issue["closed_at"]
        marker["merge"]["merged_at"] = pr["merged_at"]
        self.assertFalse(cp.marker_is_valid(self.root, marker, self.ancestor))

    def test_equal_instants_and_fractional_seconds_retained(self):
        issue = dict(self.issue, closed_at="2026-09-17T01:00:00.123456Z")
        pr = dict(self.pr, merged_at="2026-09-17T03:00:00.123456+02:00")
        marker = cp.build_marker(self.root, OP, issue, pr)
        self.assertTrue(cp.marker_is_valid(self.root, marker, self.ancestor))

    def test_nonobject_provider_rows_raise_domain_error(self):
        for value in (None, [], 1, "row"):
            with self.subTest(value=value):
                with self.assertRaises(cp.CompletionEvidenceError):
                    cp.build_marker(self.root, OP, value, self.pr)
                with self.assertRaises(cp.CompletionEvidenceError):
                    cp.build_marker(self.root, OP, self.issue, value)
                with self.assertRaises(cp.CompletionEvidenceError):
                    cp.build_marker(self.root, OP, self.issue, dict(self.pr, base=value))

    def test_unhashable_urls_are_invalid_not_projection_exceptions(self):
        for section in ("issue", "merge"):
            for value in ([], {}, ["url"], {"url": "value"}):
                with self.subTest(section=section, value=value):
                    marker = self.marker()
                    marker[section]["url"] = value
                    self.store(marker)
                    self.assertFalse(cp.marker_is_valid(self.root, marker, self.ancestor))
                    self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))

    def test_malformed_row_shapes_do_not_interrupt_projection(self):
        for value in (None, [], True, 4, "row", {}):
            with self.subTest(value=value):
                self.store(value)
                self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))
        for field in ("source", "merge", "issue"):
            marker = self.marker()
            marker[field] = ["not an object"]
            self.store(marker)
            self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))

    def test_duplicate_keys_cannot_silently_replace_marker_fields(self):
        raw = json.dumps(self.marker()).replace('"schema":', '"schema":"wrong","schema":', 1)
        self.path.write_text(raw)
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))

    def test_nonfinite_json_is_not_completion_evidence(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                raw = json.dumps(self.marker())[:-1] + ', "extra": ' + constant + '}'
                self.path.write_text(raw)
                self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))

    def test_excessively_nested_json_stays_visible(self):
        self.path.write_text('[' * 2000 + '0' + ']' * 2000)
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))
        self.assertEqual((), cp.remove_markers_for_issue(self.root, 15130))

    def test_invalid_utf8_stays_visible_and_can_be_replaced_by_valid_evidence(self):
        self.path.write_bytes(b'\xff\xfe')
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))
        self.assertEqual("wrote", cp.write_marker(self.root, self.marker(), self.ancestor))
        self.assertEqual(frozenset({OP}), cp.completed_operation_ids(self.root, self.ancestor))

    def test_large_json_record_stays_visible(self):
        marker = self.marker()
        marker["padding"] = 'x' * 65537
        self.store(marker)
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))

    def test_oversized_integer_record_stays_visible(self):
        raw = json.dumps(self.marker())[:-1] + ', "extra": ' + '9' * 10000 + '}'
        self.path.write_text(raw)
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))

    def test_noncanonical_filename_cannot_substitute_for_missing_marker(self):
        other_path = self.path.parent / 'renamed-copy.json'
        other_path.write_text(json.dumps(self.marker()))
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))

    def test_one_bad_marker_does_not_discard_a_valid_sibling(self):
        cp.write_marker(self.root, self.marker(), self.ancestor)
        other_path = self.path.parent / (OTHER + '.json')
        other_path.write_text('[' * 2000 + '0' + ']' * 2000)
        self.assertEqual(frozenset({OP}), cp.completed_operation_ids(self.root, self.ancestor))
        self.assertEqual((OP,), cp.remove_markers_for_issue(self.root, 15130))
        self.assertTrue(other_path.is_file())

    def test_reopen_removes_all_retained_copies_for_only_that_issue(self):
        marker = self.marker()
        cp.write_marker(self.root, marker, self.ancestor)
        alias = self.path.parent / 'old-copy.json'
        alias.write_text(json.dumps(marker))
        unrelated = copy.deepcopy(marker)
        unrelated["issue"]["number"] = 999
        other_path = self.path.parent / 'unrelated.json'
        other_path.write_text(json.dumps(unrelated))
        self.assertEqual((OP, OP), cp.remove_markers_for_issue(self.root, 15130))
        self.assertFalse(self.path.exists())
        self.assertFalse(alias.exists())
        self.assertTrue(other_path.exists())

    def test_write_is_idempotent_and_read_is_not_resealing(self):
        marker = self.marker()
        self.assertEqual("wrote", cp.write_marker(self.root, marker, self.ancestor))
        before = self.path.read_bytes()
        self.assertEqual("unchanged", cp.write_marker(self.root, marker, self.ancestor))
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, lambda _: False))
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(frozenset({OP}), cp.completed_operation_ids(self.root, self.ancestor))

    def test_real_git_ancestry_changes_visibility_without_source_rewrite(self):
        def git(*args, check=True):
            return subprocess.run(
                ["git", "-c", "user.name=Completion fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=check, timeout=10,
            )
        git("init", "-q")
        git("add", "p")
        git("commit", "-q", "-m", "fixture source")
        before = git("rev-parse", "HEAD").stdout.strip()
        (self.root / "implemented.txt").write_text("synthetic implementation\n")
        git("add", "implemented.txt")
        git("commit", "-q", "-m", "fixture implementation")
        implemented = git("rev-parse", "HEAD").stdout.strip()
        def actual_ancestor(sha):
            return git("merge-base", "--is-ancestor", sha, "HEAD", check=False).returncode == 0
        marker = cp.build_marker(self.root, OP, self.issue, dict(self.pr, merge_commit_sha=implemented))
        cp.write_marker(self.root, marker, actual_ancestor)
        self.assertEqual(frozenset({OP}), cp.completed_operation_ids(self.root, actual_ancestor))
        git("checkout", "--detach", "-q", before)
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, actual_ancestor))
        git("checkout", "--detach", "-q", implemented)
        self.assertEqual(frozenset({OP}), cp.completed_operation_ids(self.root, actual_ancestor))
        self.assertEqual((OP,), cp.remove_markers_for_issue(self.root, 15130))
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, actual_ancestor))


if __name__ == "__main__":
    unittest.main()
