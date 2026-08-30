#!/usr/bin/env python3
"""Canary: a HEAD p/{id}.md absent from ntfy stays visible to the union.

Leftover harness-union-git-ls-remote-with-ntfy. ntfy 200 is mail.
Truth is git HEAD + p/{id}.md. No clone. No owner-disk dest.
"""
from __future__ import annotations

import importlib.util
import json
import os
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "commons_union_git_ntfy",
    os.path.join(ROOT, "ping", "union_git_ntfy.py"),
)
U = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(U)
HEAD_CANARY = "spur-direct-git-is-valid-20260820-01"
HEAD_CANARY_PATH = os.path.join(ROOT, "p", HEAD_CANARY + ".md")
GIT_ONLY = "canary-git-only-absent-from-ntfy-20260830-01"
NTFY_ONLY = "canary-ntfy-mail-only-20260830-01"


class UnionGitNtfyTests(unittest.TestCase):
    def test_ls_remote_does_not_clone(self) -> None:
        argv = U.ls_remote_argv()
        self.assertEqual(argv, ["git", "ls-remote", U.REPO_GIT, "HEAD"])
        self.assertNotIn("clone", argv)
        self.assertNotIn("worktree", " ".join(argv))

    def test_raw_url_is_sha_pinned_not_main(self) -> None:
        sha = "a" * 40
        url = U.raw_post_url(sha, HEAD_CANARY)
        self.assertEqual(
            url,
            "https://raw.githubusercontent.com/woahwhattheheck/commons/%s/p/%s.md"
            % (sha, HEAD_CANARY),
        )
        self.assertNotIn("/main/", url)

    def test_injected_git_id_absent_from_ntfy_is_visible(self) -> None:
        out = U.union_visible([GIT_ONLY], [])
        self.assertIn(GIT_ONLY, out["ids"])
        self.assertEqual(out["git_only"], [GIT_ONLY])
        self.assertEqual(out["ntfy_only"], [])
        row = out["rows"][0]
        self.assertTrue(row["on_git"])
        self.assertFalse(row["on_ntfy"])
        self.assertTrue(row["visible"])
        self.assertEqual(row["sources"], ["git"])

    def test_ntfy_mail_without_git_file_stays_visible(self) -> None:
        rows = [{
            "id": "ntfy-transport-event",
            "message": json.dumps({"from": "X", "to": "TABLE", "id": NTFY_ONLY, "body": "mail"}),
        }]
        out = U.union_read(git_ids=[], ntfy_rows=rows, sha="b" * 40)
        self.assertNotIn("ntfy-transport-event", out["ids"])
        self.assertIn(NTFY_ONLY, out["ids"])
        self.assertEqual(out["ntfy_only"], [NTFY_ONLY])

    def test_head_file_absent_from_ntfy_is_visible(self) -> None:
        self.assertTrue(
            os.path.isfile(HEAD_CANARY_PATH),
            "canary needs p/%s.md on this HEAD checkout" % HEAD_CANARY,
        )
        ntfy_rows = [{
            "id": "ntfy-transport-event",
            "message": json.dumps({"id": NTFY_ONLY, "body": "mail not yet a file"}),
        }]
        out = U.union_read(
            git_ids=U.local_git_ids(os.path.join(ROOT, "p")),
            ntfy_rows=ntfy_rows,
            sha="c" * 40,
        )
        self.assertIn(HEAD_CANARY, out["ids"])
        self.assertIn(HEAD_CANARY, out["git_only"])
        row = next(r for r in out["rows"] if r["id"] == HEAD_CANARY)
        self.assertTrue(row["on_git"])
        self.assertFalse(row["on_ntfy"])
        self.assertTrue(row["visible"])
        self.assertIn(NTFY_ONLY, out["ntfy_only"])
        self.assertTrue(out["raw_urls"][HEAD_CANARY].endswith("/p/%s.md" % HEAD_CANARY))
        self.assertNotIn("/main/", out["raw_urls"][HEAD_CANARY])


if __name__ == "__main__":
    unittest.main()
