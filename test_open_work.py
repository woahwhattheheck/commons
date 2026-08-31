#!/usr/bin/env python3
"""Open-work projector: LANDED is p/{id}.md on current main. Slack CLAIMED is not."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
import current_work as cw  # noqa: E402
import open_work as ow  # noqa: E402


LANDED_IDS = (
    "kimi-pages-speed-20260829-01",
    "kimi-subzero-walker-20260829-01",
    "kimi-distro-listing-20260829-01",
)
SHA = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=ROOT,
    text=True,
).strip().lower()


def _commit_tree(root):
    subprocess.check_call(["git", "init", "-q"], cwd=root)
    subprocess.check_call(["git", "add", "."], cwd=root)
    subprocess.check_call(
        [
            "git",
            "-c",
            "user.name=Commons Test",
            "-c",
            "user.email=commons-test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=root,
    )
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
    ).strip().lower()


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class OpenWorkContract(unittest.TestCase):
    def test_self_test(self):
        self.assertEqual(ow.self_test(), 0)

    def test_known_landed_ids_on_this_tree(self):
        snapshot = ow.project(ROOT, SHA)
        by_id = {item["id"]: item for item in snapshot["items"]}
        for ident in LANDED_IDS:
            self.assertTrue(
                os.path.isfile(os.path.join(ROOT, "p", "%s.md" % ident)),
                ident,
            )
            row = by_id.get(ident)
            self.assertIsNotNone(row, ident)
            self.assertEqual(row["class"], "LANDED", ident)
            self.assertEqual(row["receipt"], "p/%s.md" % ident)
            self.assertEqual(row["last_sha"], SHA)

    def test_fixture_classes(self):
        tmp = tempfile.mkdtemp(prefix="open-work-")
        try:
            _write(
                os.path.join(tmp, "p", "kimi-pages-speed-20260829-01.md"),
                "from: KIMI\nid: kimi-pages-speed-20260829-01\n\n---\n\nWORK ORDER kimi-pages-speed-20260829-01 landed.\n",
            )
            _write(
                os.path.join(tmp, "p", "kimi-subzero-walker-20260829-01.md"),
                "from: KIMI\nid: kimi-subzero-walker-20260829-01\n\n---\n\nWORK ORDER kimi-subzero-walker-20260829-01 landed.\n",
            )
            _write(
                os.path.join(tmp, "p", "kimi-distro-listing-20260829-01.md"),
                "from: KIMI\nid: kimi-distro-listing-20260829-01\n\n---\n\nWORK ORDER kimi-distro-listing-20260829-01 landed.\n",
            )
            _write(
                os.path.join(tmp, "p", "owner-open-404-20260829-01.md"),
                "from: BRYCE\nis_language_model: NO\nid: owner-open-404-20260829-01\nkind: ACTION\n\n---\n\nWORK ORDER missing-work-404-20260829-01\nOWNER LAND ORDER missing-work-404-20260829-01\n",
            )
            _write(
                os.path.join(tmp, "p", "salon-hello-fixture-20260829-01.md"),
                "from: PEER\nid: salon-hello-fixture-20260829-01\n\n---\n\nhello table\n\n*Sent using* Cursor\n",
            )
            _write(
                os.path.join(tmp, "wake_jobs", "example.json"),
                json.dumps(
                    {
                        "job_id": "grkrev-not-a-work-order",
                        "status": "LEASED",
                        "task": "WORK ORDER kimi-pages-speed-20260829-01",
                    }
                ),
            )
            fixture_sha = _commit_tree(tmp)
            snapshot = ow.project(
                tmp,
                fixture_sha,
                extra={"slack_claimed": ["slack-claimed-no-file-20260829-01"]},
                include_salon=True,
            )
            by_id = {item["id"]: item for item in snapshot["items"]}
            for ident in LANDED_IDS:
                self.assertEqual(by_id[ident]["class"], "LANDED")
                self.assertEqual(by_id[ident]["receipt"], "p/%s.md" % ident)
            missing = by_id["missing-work-404-20260829-01"]
            self.assertEqual(missing["class"], "OPEN")
            self.assertEqual(missing["receipt"], "404")
            salon = by_id["salon-hello-fixture-20260829-01"]
            self.assertEqual(salon["class"], "SALON")
            dead = by_id["slack-claimed-no-file-20260829-01"]
            self.assertEqual(dead["class"], "DEAD_CLAIM")
            self.assertEqual(dead["receipt"], "404")
            self.assertNotEqual(dead["class"], "LANDED")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_slack_claimed_is_not_landed_without_p(self):
        row = ow.classify_id(
            "slack-claimed-no-file-20260829-01",
            ROOT,
            extra={"slack_claimed": ["slack-claimed-no-file-20260829-01"]},
            record={"work": True},
            main_sha=SHA,
        )
        self.assertEqual(row["class"], "DEAD_CLAIM")
        self.assertEqual(row["receipt"], "404")

    def test_work_order_after_structural_window_is_not_omitted(self):
        body = "\n".join(["context line %s" % index for index in range(20)])
        parsed = ow.parse_structured_record(
            "from: PEER\nid: delayed-marker-record-20260831-01\n\n---\n\n"
            + body
            + "\nWORK ORDER delayed-work-order-20260831-01\n"
        )
        self.assertIn("delayed-work-order-20260831-01", parsed["work_ids"])

    def test_main_sha_pins_receipt_existence_to_git_tree(self):
        tmp = tempfile.mkdtemp(prefix="open-work-sha-")
        ident = "sha-pinned-receipt-20260831-01"
        try:
            subprocess.check_call(["git", "init", "-q"], cwd=tmp)
            _write(os.path.join(tmp, "seed.txt"), "seed\n")
            subprocess.check_call(["git", "add", "seed.txt"], cwd=tmp)
            subprocess.check_call(
                [
                    "git",
                    "-c",
                    "user.name=Open Work Test",
                    "-c",
                    "user.email=open-work@example.invalid",
                    "commit",
                    "-q",
                    "-m",
                    "seed",
                ],
                cwd=tmp,
            )
            before = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=tmp, text=True
            ).strip()
            _write(
                os.path.join(tmp, "p", "%s.md" % ident),
                "id: %s\n\n---\n\nWORK ORDER %s\n" % (ident, ident),
            )
            subprocess.check_call(["git", "add", "p/%s.md" % ident], cwd=tmp)
            subprocess.check_call(
                [
                    "git",
                    "-c",
                    "user.name=Open Work Test",
                    "-c",
                    "user.email=open-work@example.invalid",
                    "commit",
                    "-q",
                    "-m",
                    "receipt",
                ],
                cwd=tmp,
            )
            after = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=tmp, text=True
            ).strip()

            old_snapshot = ow.project(
                tmp, before, extra={"work_ids": [ident]}
            )
            new_snapshot = ow.project(
                tmp, after, extra={"work_ids": [ident]}
            )
            old_row = {item["id"]: item for item in old_snapshot["items"]}[ident]
            new_row = {item["id"]: item for item in new_snapshot["items"]}[ident]
            self.assertEqual(old_row["class"], "OPEN")
            self.assertEqual(old_row["receipt"], "404")
            self.assertEqual(new_row["class"], "LANDED")
            self.assertEqual(new_row["receipt"], "p/%s.md" % ident)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_current_work_points_at_sibling_projector(self):
        live = cw.project(
            {
                "schema": cw.SCHEMA,
                "add_work": {"preferred": cw.SHIP_LOOP, "skill": cw.SHIP_SKILL},
                "items": [],
                "historical_directives": [],
            },
            {},
        )
        pointer = live.get("open_work") or {}
        self.assertEqual(pointer.get("instrument"), "host/open_work.py")
        self.assertEqual(pointer.get("human"), "ground/open-work-structured-ids-on-current-main.md")
        self.assertEqual(pointer.get("machine"), "ground/open-work-structured-ids-on-current-main.json")
        self.assertEqual(pointer.get("listing"), "ground/open-work-listing")
        self.assertIn("not a second queue", str(pointer.get("note") or "").lower())

    def test_written_outputs_name_classes_and_sha(self):
        tmp = tempfile.mkdtemp(prefix="open-work-write-")
        try:
            _write(
                os.path.join(tmp, "p", "kimi-pages-speed-20260829-01.md"),
                "id: kimi-pages-speed-20260829-01\n\n---\n\nWORK ORDER kimi-pages-speed-20260829-01\n",
            )
            fixture_sha = _commit_tree(tmp)
            snapshot = ow.project(tmp, fixture_sha)
            ow.write_snapshot(tmp, snapshot)
            with open(os.path.join(tmp, ow.HUMAN_REL), encoding="utf-8") as handle:
                human = handle.read()
            with open(os.path.join(tmp, ow.MACHINE_REL), encoding="utf-8") as handle:
                machine = json.loads(handle.read())
            self.assertIn("LANDED", human)
            self.assertIn(SHA, human)
            self.assertEqual(machine["schema"], ow.SCHEMA)
            self.assertEqual(machine["main_sha"], SHA)
            self.assertEqual(machine["items"][0]["class"], "LANDED")
            self.assertTrue(os.path.isfile(os.path.join(tmp, ow.HUMAN_REL)))
            self.assertTrue(os.path.isfile(os.path.join(tmp, ow.POINTER_HUMAN_REL)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_title_filenames_are_ls_legible_and_do_not_remint(self):
        self.assertTrue(ow.is_title_filename("kimi-pages-speed-20260829-01"))
        self.assertTrue(ow.is_title_filename("kimi-subzero-walker-20260829-01"))
        self.assertTrue(ow.is_title_filename("kimi-distro-listing-20260829-01"))
        self.assertTrue(ow.is_title_filename("commons-peers-telegram-20260829-01"))
        self.assertFalse(ow.is_title_filename("action-20260828163033-89fe29a5e062"))
        tmp = tempfile.mkdtemp(prefix="open-work-ls-")
        try:
            _write(
                os.path.join(tmp, "p", "kimi-pages-speed-20260829-01.md"),
                "id: kimi-pages-speed-20260829-01\n\n---\n\nWORK ORDER kimi-pages-speed-20260829-01\n",
            )
            _write(
                os.path.join(tmp, "p", "owner-open-404-20260829-01.md"),
                "from: BRYCE\nis_language_model: NO\nid: owner-open-404-20260829-01\nkind: ACTION\n\n---\n\nWORK ORDER missing-work-404-20260829-01\n",
            )
            _write(
                os.path.join(tmp, "p", "action-20260828163033-89fe29a5e062.md"),
                "from: SOL\nid: action-20260828163033-89fe29a5e062\nkind: ACTION\n\n---\n\nkind: ACTION\n",
            )
            fixture_sha = _commit_tree(tmp)
            snapshot = ow.project(tmp, fixture_sha)
            ow.write_snapshot(tmp, snapshot)
            listing = os.path.join(tmp, ow.LISTING_REL)
            names = sorted(os.listdir(listing))
            self.assertIn("missing-work-404-20260829-01-open.md", names)
            self.assertTrue(names[0].startswith("missing-work"))
            self.assertFalse(any(name.startswith("open-") for name in names))
            self.assertNotIn("action-20260828163033-89fe29a5e062-landed.md", names)
            self.assertNotIn("landed-action-20260828163033-89fe29a5e062.md", names)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "p", "kimi-pages-speed-20260829-01.md")))
            self.assertTrue(
                os.path.isfile(os.path.join(ROOT, "p", "commons-peers-telegram-20260829-01.md"))
            )
            self.assertTrue(
                os.path.isfile(os.path.join(ROOT, "p", "kimi-subzero-walker-20260829-01.md"))
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


    def test_unavailable_main_sha_never_falls_back_to_worktree(self):
        tmp = tempfile.mkdtemp(prefix="open-work-unmeasured-sha-")
        ident = "unmeasured-main-receipt-20260831-01"
        try:
            _write(
                os.path.join(tmp, "p", "%s.md" % ident),
                "id: %s\n\n---\n\nWORK ORDER %s\n" % (ident, ident),
            )
            snapshot = ow.project(
                tmp,
                "f" * 40,
                extra={"work_ids": [ident]},
            )
            by_id = {item["id"]: item for item in snapshot["items"]}
            self.assertEqual(by_id[ident]["class"], "OPEN")
            self.assertEqual(by_id[ident]["receipt"], "404")
            self.assertEqual(
                snapshot["errors"],
                [{"code": "MAIN_SHA_UNMEASURED", "main_sha": "f" * 40}],
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
