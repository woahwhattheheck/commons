#!/usr/bin/env python3
"""Current-work identifiers and main SHAs must match the complete token."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "host"))
import current_work as cw


def work(job_id="exact-token-20260907-01", kind="BUILDABLE"):
    return {
        "id": job_id,
        "title": "Exact token current work",
        "kind": kind,
        "claimed_paths": ["evidence.md"],
    }


class ExactTokenTests(unittest.TestCase):
    def test_valid_id_lengths_and_characters(self):
        for job_id in ("a" * 8, "z" * 80, "Ab09._-x"):
            with self.subTest(job_id=job_id):
                self.assertEqual(cw.validate_item(work(job_id)), [])

    def test_other_invalid_ids_still_report_problems(self):
        for job_id in ("a" * 7, "z" * 81, "has space", "has/slash", "caf\u00e9-word"):
            with self.subTest(job_id=job_id):
                self.assertTrue(cw.validate_item(work(job_id)))

    def test_trailing_newline_is_not_part_of_a_valid_id(self):
        for job_id in ("a" * 8, "z" * 80, "Ab09._-x"):
            for suffix in ("\n", "\r\n"):
                with self.subTest(job_id=job_id, suffix=suffix):
                    self.assertTrue(cw.validate_item(work(job_id + suffix)))

    def test_append_does_not_store_a_newline_suffixed_id(self):
        catalog = {"items": [work()]}
        incoming = work("another-item-20260907-01\n")
        updated, problems = cw.add_item(catalog, incoming)
        self.assertIs(updated, catalog)
        self.assertTrue(problems)
        self.assertEqual(catalog["items"], [work()])

    def test_exact_sha_closes_with_or_without_unrelated_pr(self):
        sha = "a" * 40
        for prs in ([], [123]):
            with self.subTest(prs=prs):
                result = cw.reconcile_item(work(), {
                    "main_sha": sha, "main_paths": {"evidence.md": True},
                    "open_prs": prs,
                })
                self.assertEqual(result["status"], "CLOSED")
                self.assertEqual(result["main_sha"], sha)

    def test_trailing_newline_sha_does_not_close(self):
        for prs in ([], [123]):
            with self.subTest(prs=prs):
                result = cw.reconcile_item(work(), {
                    "main_sha": "a" * 40 + "\n",
                    "main_paths": {"evidence.md": True}, "open_prs": prs,
                })
                self.assertEqual(result["status"], "OPEN")
                self.assertEqual(result["main_sha"], "")

    def test_other_invalid_shas_still_do_not_close(self):
        for sha in ("", "a" * 39, "a" * 41, "A" * 40, "a" * 40 + "\r\n", " " + "a" * 40):
            with self.subTest(sha=sha):
                result = cw.reconcile_item(work(), {
                    "main_sha": sha, "main_paths": {"evidence.md": True},
                })
                self.assertEqual(result["status"], "OPEN")

    def test_device_pin_is_unchanged(self):
        for sha in ("a" * 40, "a" * 40 + "\n"):
            with self.subTest(sha=sha):
                result = cw.reconcile_item(work(kind="DEVICE_PINNED"), {
                    "main_sha": sha, "main_paths": {"evidence.md": True},
                })
                self.assertEqual(result["status"], "PINNED")
                self.assertFalse(result["executable"])


if __name__ == "__main__":
    unittest.main()
