#!/usr/bin/env python3
"""Focused tests for the fail-closed repository portfolio projection."""

from __future__ import annotations

import copy
import unittest

from host.repository_portfolio import PortfolioError, classify, validate


CANON = "a" * 40
OLD = "b" * 40


def fixture() -> dict[str, object]:
    return {
        "schema": "commons-repository-portfolio/v1",
        "source_main_sha": CANON,
        "public_repositories": [
            {
                "full_name": "owner/commons",
                "visibility": "public",
                "head_sha": CANON,
                "role": "CANONICAL",
                "condition": "CANONICAL",
            },
            {
                "full_name": "owner/commons-backup",
                "visibility": "public",
                "head_sha": "c" * 40,
                "role": "MIRROR",
                "condition": "STALE_MIRROR",
                "recorded_source_sha": OLD,
                "commits_behind": 45,
            },
            {
                "full_name": "owner/help",
                "visibility": "public",
                "head_sha": "d" * 40,
                "role": "HELP_REFERENCE",
                "condition": "REFERENCE",
            },
            {
                "full_name": "owner/sprint",
                "visibility": "public",
                "head_sha": "e" * 40,
                "role": "SPRINT_REFERENCE",
                "condition": "REFERENCE",
            },
        ],
        "private_aggregate": {
            "accessible_repository_count": 1,
            "details_persisted": False,
            "head_state": "VERIFIED_REDACTED",
        },
        "summary": {
            "accessible_repositories": 5,
            "public_repositories": 4,
            "private_repositories": 1,
            "canonical_repositories": 1,
            "current_mirrors": 0,
            "stale_mirrors": 1,
            "unverified_mirrors": 0,
            "reference_repositories": 2,
        },
    }


class RepositoryPortfolioTests(unittest.TestCase):
    def test_exact_valid_summary(self) -> None:
        self.assertEqual(validate(fixture()), fixture()["summary"])

    def test_duplicate_public_repo_fails_closed(self) -> None:
        row = copy.deepcopy(fixture()["public_repositories"][0])
        data = fixture()
        data["public_repositories"].append(row)
        with self.assertRaisesRegex(PortfolioError, "duplicate public repository"):
            validate(data)

    def test_private_name_is_rejected(self) -> None:
        data = fixture()
        data["private_aggregate"]["full_name"] = "owner/private-device"
        with self.assertRaisesRegex(PortfolioError, "leaks repository detail"):
            validate(data)

    def test_private_head_is_rejected(self) -> None:
        data = fixture()
        data["private_aggregate"]["head_sha"] = "f" * 40
        with self.assertRaisesRegex(PortfolioError, "leaks repository detail"):
            validate(data)

    def test_unknown_mirror_gap_is_not_current(self) -> None:
        row = fixture()["public_repositories"][1]
        row["commits_behind"] = None
        self.assertEqual(classify(row, CANON), "MIRROR_UNVERIFIED")

    def test_zero_gap_exact_head_is_current(self) -> None:
        row = fixture()["public_repositories"][1]
        row["recorded_source_sha"] = CANON
        row["commits_behind"] = 0
        self.assertEqual(classify(row, CANON), "CURRENT_MIRROR")

    def test_zero_gap_wrong_head_is_inconsistent(self) -> None:
        row = fixture()["public_repositories"][1]
        row["commits_behind"] = 0
        self.assertEqual(classify(row, CANON), "MIRROR_INCONSISTENT")

    def test_canonical_must_match_source_main(self) -> None:
        data = fixture()
        data["public_repositories"][0]["head_sha"] = "f" * 40
        with self.assertRaisesRegex(PortfolioError, "canonical repository head differs"):
            validate(data)


if __name__ == "__main__":
    unittest.main()
