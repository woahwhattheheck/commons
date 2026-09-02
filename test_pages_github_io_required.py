#!/usr/bin/env python3
"""github.io copy filters must keep live board chunks and the free-sample SEED0."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from host import pages_github_io_required as required


ROOT = Path(__file__).resolve().parent


class PagesGithubIoRequiredTests(unittest.TestCase):
    def test_board_js_still_fetches_chunks_at_three_sites(self) -> None:
        text = (ROOT / "board.js").read_text(encoding="utf-8")
        for marker in required.BOARD_CHUNK_MARKERS:
            self.assertIn(marker, text)
        self.assertEqual(len(required.BOARD_CHUNK_MARKERS), 3)

    def test_required_files_exist_and_include_seed0_chunks_and_docs(self) -> None:
        files = required.required_files(ROOT)
        self.assertIn(required.CHUNKS_INDEX, files)
        self.assertIn(required.SEED0, files)
        self.assertIn(required.EXPANDING_SEED, files)
        self.assertIn(required.PAY, files)
        self.assertIn(required.ACTION_PAD, files)
        self.assertIn(required.COMMERCE, files)
        self.assertEqual(required.missing_on_disk(ROOT), ())
        self.assertTrue((ROOT / required.SEED0).is_file())
        self.assertEqual((ROOT / required.SEED0).stat().st_size, 8192)

    def test_free_sample_page_and_sales_pack_name_the_same_seed(self) -> None:
        page = (ROOT / "muhlnickel-free-sample.html").read_text(encoding="utf-8")
        pack = json.loads(
            (ROOT / "revenue" / "muhlnickel_free_sample" / "sales_pack.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn(required.SEED0, page)
        self.assertIn(required.EXPANDING_SEED, page)
        self.assertEqual(pack["proof"]["path"], required.SEED0)
        self.assertEqual(pack["proof"]["existing_doc"], required.EXPANDING_SEED)
        self.assertIn("github.io/commons/muhlnickel-free-sample.html", pack["canonical_page"])

    def test_stated_except_list_would_drop_chunks_and_seed0_not_docs(self) -> None:
        omitted = required.stated_except_omits(ROOT)
        self.assertIn(required.CHUNKS_INDEX, omitted)
        self.assertIn(required.SEED0, omitted)
        self.assertNotIn(required.EXPANDING_SEED, omitted)
        self.assertTrue(
            required.omitted_by_except_keep(
                required.SEED0,
                required.STATED_EXCEPT_DIRS,
                required.STATED_KEEP_PREFIXES,
            )
        )
        self.assertFalse(
            required.omitted_by_except_keep(
                required.EXPANDING_SEED,
                required.STATED_EXCEPT_DIRS,
                required.STATED_KEEP_PREFIXES,
            )
        )
        self.assertFalse(
            required.omitted_by_except_keep(
                "board.js",
                required.STATED_EXCEPT_DIRS,
                required.STATED_KEEP_PREFIXES,
            )
        )

    def test_rsync_exclude_muhl_with_docs_keep_still_drops_seed0(self) -> None:
        yml = """
        rsync -a --exclude muhl --exclude chunks --exclude excerpts --exclude conflicts --exclude .github \\
              --include muhl/docs --include muhl/docs/** ./ _site/
        """
        self.assertTrue(required.workflow_omits(yml, required.CHUNKS_INDEX))
        self.assertTrue(required.workflow_omits(yml, required.SEED0))
        self.assertFalse(required.workflow_omits(yml, required.EXPANDING_SEED))

    def test_rsync_that_keeps_seed0_and_chunks_is_clean(self) -> None:
        yml = """
        rsync -a --exclude muhl --exclude excerpts --exclude conflicts --exclude .github \\
              --include muhl/docs --include muhl/docs/** \\
              --include muhl/containers --include muhl/containers/MUHLNICKEL_DISTRO \\
              --include muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno ./ _site/
        """
        self.assertFalse(required.workflow_omits(yml, required.CHUNKS_INDEX))
        self.assertFalse(required.workflow_omits(yml, required.SEED0))
        self.assertFalse(required.workflow_omits(yml, required.EXPANDING_SEED))

    def test_copyback_rsync_and_cp_count_as_keep_prefixes(self) -> None:
        yml = """
        rsync -a --exclude muhl --exclude excerpts --exclude conflicts --exclude .github ./ _site/
        rsync -a muhl/docs/ _site/muhl/docs/
        cp -a muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno \\
          _site/muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno
        'keeps': ['chunks/', 'muhl/docs/', 'muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno']
        """
        self.assertFalse(required.workflow_omits(yml, required.CHUNKS_INDEX))
        self.assertFalse(required.workflow_omits(yml, required.SEED0))
        self.assertFalse(required.workflow_omits(yml, required.EXPANDING_SEED))

    def test_publish_all_workflow_omits_nothing(self) -> None:
        self.assertFalse(required.workflow_omits("echo publish whole tree", required.SEED0))
        self.assertFalse(required.workflow_omits("echo publish whole tree", required.CHUNKS_INDEX))

    def test_live_workflow_absent_or_keeps_required_paths(self) -> None:
        omitted = required.live_workflow_omits(ROOT)
        self.assertEqual(omitted, ())

    def test_workflow_republishes_after_successful_github_jekyll_clobber(self) -> None:
        """Actions still writes _site/; workflow_run recovers after Jekyll success.

        GitHub-managed pages-build-deployment still Jekyll-publishes main and
        overwrites the Actions artifact. Recover only on Jekyll *success*.
        In-tree pages-deploy.json is a complementary survive path.
        """
        text = (ROOT / ".github" / "workflows" / "pages-deploy.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("workflow_run:", text)
        self.assertIn("pages-build-deployment", text)
        self.assertIn("pages build and deployment", text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertNotRegex(
            text,
            r"(?m)^on:\n(?:  .*\n)*  push:",
            "push trigger must stay dropped; ingest storms cancelled deploys",
        )
        self.assertIn("_site/pages-deploy.json", text)
        self.assertIn("--exclude '_site/'", text)
        self.assertIn("[ ! -f _site/pages-deploy.json ]", text)
        self.assertIn("missing _site/pages-deploy.json after write", text)

    def test_generated_pages_deploy_receipt_is_in_git(self) -> None:
        """Actions still writes _site/; in-tree canary survives github-pages[bot] overwrite."""
        self.assertTrue((ROOT / required.PAGES_DEPLOY_RECEIPT).is_file())
        self.assertNotIn(required.PAGES_DEPLOY_RECEIPT, required.required_files(ROOT))
        self.assertTrue(required.live_workflow_writes_pages_deploy_receipt(ROOT))
        self.assertFalse(
            required.workflow_writes_pages_deploy_receipt("rsync -a ./ _site/")
        )
        payload = required.report(ROOT)
        self.assertTrue(payload["open_door"])
        self.assertTrue(payload["copy_filter_is_not_admission"])
        self.assertEqual(payload["missing_on_disk"], [])
        self.assertEqual(payload["uncovered_by_keep_map"], [])
        self.assertIn(required.SEED0, payload["stated_except_would_omit"])
        self.assertIn(required.CHUNKS_INDEX, payload["stated_except_would_omit"])
        self.assertNotIn(required.EXPANDING_SEED, payload["stated_except_would_omit"])
        self.assertEqual(payload["generated_live_receipt"], required.PAGES_DEPLOY_RECEIPT)
        self.assertIs(payload["generated_live_receipt_in_git"], True)
        self.assertIs(payload["workflow_writes_generated_live_receipt"], True)
        self.assertNotIn(required.PAGES_DEPLOY_RECEIPT, payload["required"])

    def test_peer_keep_map_covers_derived_required_files(self) -> None:
        keep_map = required.load_keep_map(ROOT)
        self.assertEqual(keep_map["id"], "cursor-pages-keep-paths-20260902-01")
        self.assertIs(keep_map["owns_deploy_workflow"], False)
        self.assertEqual(required.uncovered_by_keep_map(ROOT), ())
        self.assertTrue(required.covered_by_keep(required.CHUNKS_INDEX, keep_map["required_keep_paths"]))
        self.assertTrue(required.covered_by_keep(required.SEED0, keep_map["required_keep_paths"]))
        self.assertTrue(required.covered_by_keep(required.EXPANDING_SEED, keep_map["required_keep_paths"]))
        self.assertTrue(required.covered_by_keep(required.PAY, keep_map["required_keep_paths"]))
        self.assertTrue(required.covered_by_keep(required.ACTION_PAD, keep_map["required_keep_paths"]))
        self.assertTrue(required.covered_by_keep(required.COMMERCE, keep_map["required_keep_paths"]))
        self.assertIn(required.ACTION_PAD, keep_map["evidence"]["open_door"])
        evidence = keep_map["evidence"]["board_js_chunk_fetches"]
        self.assertEqual(len(evidence), 3)
        self.assertIn("chunks/{day}/{pid}.json", evidence)

    def test_covered_by_keep_is_prefix_or_exact(self) -> None:
        self.assertTrue(required.covered_by_keep("chunks/index.json", ("chunks/",)))
        self.assertTrue(required.covered_by_keep(required.SEED0, (required.SEED0,)))
        self.assertFalse(required.covered_by_keep(required.SEED0, ("muhl/docs/",)))
        self.assertFalse(required.covered_by_keep("excerpts/x.json", ("chunks/", "muhl/docs/")))

    def test_deploy_doc_absent_or_folded_keep_is_clean(self) -> None:
        self.assertFalse(required.live_deploy_doc_excludes_chunks(ROOT))
        payload = required.report(ROOT)
        self.assertFalse(payload["deploy_doc_excludes_chunks"])
        if payload["deploy_doc_present"]:
            text = (ROOT / "ground" / "PAGES_DEPLOY.md").read_text(encoding="utf-8")
            self.assertFalse(required.deploy_doc_excludes_chunks(text))
            self.assertRegex(text, r"`chunks/` MUST stay|chunks/ MUST stay")

    def test_deploy_doc_except_list_with_chunks_is_flagged(self) -> None:
        bad = (
            "Allowlist: the whole tree **except** `muhl/` (only `muhl/docs/` stays),\n"
            "`chunks/`, `excerpts/`, `conflicts/`, `.github/`. Roughly 235 MB.\n"
        )
        good = (
            "Allowlist: the whole tree **except** bulk `muhl/` outside keep rows.\n"
            "`chunks/` MUST stay (board.js). Also exclude `excerpts/`, `conflicts/`.\n"
        )
        self.assertTrue(required.deploy_doc_excludes_chunks(bad))
        self.assertFalse(required.deploy_doc_excludes_chunks(good))

    def test_fable_pages_deploy_pr_doc_keeps_chunks(self) -> None:
        """PR tip may move; after digit keep-align assist the card must keep chunks/."""
        import subprocess

        tip = "origin/claude/pages-workflow-deploy-20260902:ground/PAGES_DEPLOY.md"
        try:
            text = subprocess.check_output(["git", "show", tip], text=True)
        except subprocess.CalledProcessError:
            self.skipTest("Fable/GOAT Pages deploy branch tip not fetched")
        self.assertFalse(
            required.deploy_doc_excludes_chunks(text),
            "PAGES_DEPLOY.md on Pages PR must not list chunks/ under except (keep-paths)",
        )
        self.assertIn("chunks/", text)
        self.assertIn("MUST stay", text)

    def test_helper_source_does_not_add_admission_locks(self) -> None:

        text = (ROOT / "host" / "pages_github_io_required.py").read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("possessing the link stays authorization", lowered)
        self.assertNotIn("authentication required", lowered)
        self.assertNotIn("permission denied", lowered)
        self.assertNotIn("allowed_verbs", lowered)
        self.assertNotIn("path_allowed", lowered)


if __name__ == "__main__":
    unittest.main()
