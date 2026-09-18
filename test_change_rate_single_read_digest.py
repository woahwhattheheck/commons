#!/usr/bin/env python3
"""Canary: one-fetch change.md is a rate digest, not a last-N dump."""
import json
import os
import shutil
import tempfile
import unittest

import llms_txt


ROOT = os.path.dirname(os.path.abspath(__file__))
LONG_BODY = "FULL POST BODY " * 80
FAT_FRESH = "# Commons fresh\n\n" + "\n".join(
    "- [id-%02d](x) — WHO · 2026-08-31T00:00:00Z · %s" % (i, LONG_BODY)
    for i in range(24)
)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class ChangeRateSingleReadDigest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="change-rate-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        rows = []
        for i in range(24):
            rows.append({
                "id": "dump-post-%02d-20260831-01" % i,
                "from": "WHO",
                "ts": "2026-08-31T00:00:00Z",
                "body": LONG_BODY,
            })
        self.rows = rows
        _write(os.path.join(self.tmp, "pulse.json"), json.dumps({
            "seq": 100,
            "head": "abc123",
            "ts": "2026-08-31T00:00:00Z",
            "post_count": 9000,
            "newest": [r["id"] for r in rows[:10]],
        }) + "\n")
        _write(os.path.join(self.tmp, "builds.json"), json.dumps({
            "n_open_prs": 3,
        }) + "\n")
        _write(os.path.join(self.tmp, "fresh.md"), FAT_FRESH)
        _write(os.path.join(self.tmp, "llms.txt"), "last 24 teaser\n")
        _write(os.path.join(self.tmp, "peers.md"), "last 24 plus branches\n")

    def _bake(self, **kwargs):
        args = dict(
            rows=self.rows,
            ts="2026-08-31T01:00:00Z",
            head="aaa111aaa111aaa111aaa111aaa111aaa111aaa1",
            n_tips=12,
            root=self.tmp,
        )
        args.update(kwargs)
        return llms_txt.write_change_rate(**args)

    def test_digest_exists_short_names_head_and_reports_counts(self):
        text = self._bake()
        path = os.path.join(self.tmp, "change.md")
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(open(path, encoding="utf-8").read(), text)
        raw = text.encode("utf-8")
        self.assertLessEqual(len(raw), llms_txt.CHANGE_MAX_BYTES)
        self.assertLess(len(raw), len(FAT_FRESH.encode("utf-8")) // 4)
        self.assertIn("HEAD aaa111aaa111aaa111aaa111aaa111aaa111aaa1", text)
        self.assertIn("BAKE 2026-08-31T01:00:00Z", text)
        self.assertIn("RATE p/", text)
        self.assertIn("RATE prs open=3", text)
        self.assertIn("RATE peers open-branches=12", text)
        self.assertIn("RATE pulse seq=100", text)
        self.assertIn("newest dump-post-00-20260831-01", text)
        self.assertNotIn(LONG_BODY, text)
        self.assertLess(text.count("dump-post-"), 8)
        self.assertNotIn("dump-post-10-20260831-01", text)

    def test_cites_four_existing_surfaces_and_repo_pulse(self):
        text = self._bake()
        for name in ("pulse.json", "fresh.md", "llms.txt", "peers.md"):
            self.assertIn(name, text)
        self.assertIn("repo_pulse.py", text)
        self.assertIn("repo-pulse.yml", text)
        self.assertIn("last-N", text)

    def test_does_not_rewrite_the_four_last_n_files(self):
        before = {
            name: open(os.path.join(self.tmp, name), encoding="utf-8").read()
            for name in ("fresh.md", "llms.txt", "peers.md", "pulse.json")
        }
        self._bake()
        for name, blob in before.items():
            self.assertEqual(
                open(os.path.join(self.tmp, name), encoding="utf-8").read(),
                blob,
                name,
            )

    def test_second_bake_reports_rate_delta_not_first(self):
        self._bake(p_new=0)
        _write(os.path.join(self.tmp, "pulse.json"), json.dumps({
            "seq": 104,
            "head": "bbb",
            "post_count": 9012,
        }) + "\n")
        _write(os.path.join(self.tmp, "builds.json"), json.dumps({
            "n_open_prs": 5,
        }) + "\n")
        newer = [{"id": "new-only-20260831-01"}] + self.rows
        text = self._bake(
            rows=newer,
            ts="2026-08-31T02:00:00Z",
            head="bbb222bbb222bbb222bbb222bbb222bbb222bbb2",
            n_tips=15,
            p_new=12,
        )
        self.assertIn("PREV aaa111aaa111aaa111aaa111aaa111aaa111aaa1", text)
        self.assertIn("RATE p/ +12 since prev", text)
        self.assertIn("count 9012", text)
        self.assertIn("RATE prs open=5 Δ +2", text)
        self.assertIn("RATE peers open-branches=15 Δ +3", text)
        self.assertIn("RATE pulse seq=104 Δ +4", text)
        self.assertIn("newest new-only-20260831-01", text)

    def test_posting_remains_ungated(self):
        text = self._bake()
        self.assertIn("Open door", text)
        self.assertIn("No auth", text)
        self.assertIn("Posting stays ungated", text)
        self.assertNotIn("require login", text.lower())
        blocked = (
            "MEMORY_GATE",
            "verb allowlist",
            "protected-path",
            "approval workflow",
            "must authenticate",
        )
        for phrase in blocked:
            if phrase == "MEMORY_GATE":
                self.assertIn("No MEMORY_GATE", text)
            else:
                self.assertNotIn(phrase, text)
        start = open(os.path.join(ROOT, "START.md"), encoding="utf-8").read()
        html = open(os.path.join(ROOT, "start.html"), encoding="utf-8").read()
        receipt = open(
            os.path.join(ROOT, "p", "change-rate-single-read-digest-20260830-01.md"),
            encoding="utf-8",
        ).read()
        baker = open(os.path.join(ROOT, "llms_txt.py"), encoding="utf-8").read()
        for blob in (text, start, html, receipt, baker):
            self.assertNotIn("MEMORY_GATE required", blob)
            self.assertNotIn("login required", blob.lower())

    def test_baker_and_doors_wire_the_digest(self):
        src = open(os.path.join(ROOT, "llms_txt.py"), encoding="utf-8").read()
        self.assertIn("write_change_rate", src)
        self.assertIn('"change.md"', src)
        self.assertIn("CHANGE_MAX_BYTES", src)
        start = open(os.path.join(ROOT, "START.md"), encoding="utf-8").read()
        html = open(os.path.join(ROOT, "start.html"), encoding="utf-8").read()
        self.assertIn("[change.md](./change.md)", start)
        self.assertIn('href="./change.md"', html)
        for name in ("pulse.json", "fresh.md", "llms.txt", "peers.md"):
            self.assertIn(name, start)
        receipt = open(
            os.path.join(ROOT, "p", "change-rate-single-read-digest-20260830-01.md"),
            encoding="utf-8",
        ).read()
        self.assertIn("from: SETH", receipt)
        self.assertIn("id: change-rate-single-read-digest-20260830-01", receipt)
        self.assertIn("DURABLE_PAGE", receipt)
        self.assertIn("change.md", receipt)

    def test_live_digest_matches_contract(self):
        path = os.path.join(ROOT, "change.md")
        self.assertTrue(os.path.isfile(path))
        text = open(path, encoding="utf-8").read()
        self.assertLessEqual(len(text.encode("utf-8")), llms_txt.CHANGE_MAX_BYTES)
        self.assertIn("HEAD ", text)
        self.assertIn("RATE p/", text)
        self.assertNotIn(LONG_BODY.strip(), text)
        for name in ("pulse.json", "fresh.md", "llms.txt", "peers.md"):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
