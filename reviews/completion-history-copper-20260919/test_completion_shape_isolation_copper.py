"""Malformed marker isolation; synthetic records, no provider I/O.

Uses only the previously published review fixture setup. Production completion
code is imported unchanged; no renderer or validator replacement is installed.
"""
import copy
import json
import unittest

import completion_projection as cp
import test_completion_provenance_review_copper as fixtures


class CompletionShapeIsolationTests(unittest.TestCase):
    setUp = fixtures.CompletionProvenanceReviewTests.setUp
    ancestor = staticmethod(fixtures.CompletionProvenanceReviewTests.ancestor)

    @staticmethod
    def invalid_urls():
        for section in ("issue", "merge"):
            for value in ([], {}, ["not-a-url"], {"value": "not-a-url"}):
                yield section, value

    def build(self, operation=fixtures.OP):
        issue = dict(self.issue, title=operation, body=f"Operation: {operation}")
        return cp.build_marker(self.root, operation, issue, self.pr)

    def test_reader_rejects_url_containers_without_raising(self):
        for section, value in self.invalid_urls():
            with self.subTest(section=section, value=value):
                row = self.build()
                row[section]["url"] = copy.deepcopy(value)
                self.assertFalse(cp.marker_is_valid(self.root, row, self.ancestor))

    def test_bad_marker_does_not_abort_healthy_completion(self):
        cp.write_marker(self.root, self.build(), self.ancestor)
        invalid_path = self.root / cp.marker_rel(fixtures.OTHER)
        original_source = (self.root / cp.source_rel(fixtures.OP)).read_bytes()
        for section, value in self.invalid_urls():
            with self.subTest(section=section, value=value):
                row = self.build(fixtures.OTHER)
                row[section]["url"] = copy.deepcopy(value)
                encoded = json.dumps(row).encode("utf-8")
                invalid_path.write_bytes(encoded)
                self.assertEqual(
                    frozenset({fixtures.OP}),
                    cp.completed_operation_ids(self.root, self.ancestor),
                )
                self.assertEqual(encoded, invalid_path.read_bytes())
                self.assertEqual(
                    original_source,
                    (self.root / cp.source_rel(fixtures.OP)).read_bytes(),
                )

    def test_control_unrelated_document_shapes_remain_ignored(self):
        cp.write_marker(self.root, self.build(), self.ancestor)
        invalid_path = self.root / cp.marker_rel(fixtures.OTHER)
        for row in (None, False, 5, "invalid", [], {}, {"issue": []}):
            with self.subTest(row=row):
                invalid_path.write_text(json.dumps(row), encoding="utf-8")
                self.assertEqual(
                    frozenset({fixtures.OP}),
                    cp.completed_operation_ids(self.root, self.ancestor),
                )


if __name__ == "__main__":
    unittest.main()
