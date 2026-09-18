#!/usr/bin/env python3
"""Exercise landed-work history selection against real temporary Git histories."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("landed_work_feed_history_subject", ROOT / "host/landed_work_feed.py")
assert SPEC and SPEC.loader
feed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(feed)


class HistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sequence = 0
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Feed Test")
        self.git("config", "user.email", "feed-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", str(self.root / "no-hooks"))
        self.commit("llms.txt+fresh.md initial", {"llms.txt": "initial"})

    def git(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(self.root), *args], text=True, stderr=subprocess.PIPE,
        ).strip()

    def commit(self, title: str, files: dict[str, str] | None = None) -> str:
        self.sequence += 1
        for name, text in (files or {}).items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.git("add", "--all")
        self.git("commit", "-q", "--allow-empty", "-m", title)
        return self.git("rev-parse", "HEAD")

    def bakes(self, count: int, *, by_path: bool = False) -> None:
        for _ in range(count):
            self.commit(
                "Update generated files" if by_path else "llms.txt+fresh.md bake",
                {"llms.txt": str(self.sequence)} if by_path else None,
            )

    def selected(self, limit: int) -> list[str]:
        return [row["sha"] for row in feed.recent_merges(limit, self.root)]

    def test_long_title_bake_run_does_not_hide_deliveries(self) -> None:
        first = self.commit("Merge pull request #101", {"source.py": "first"})
        second = self.commit("Merge pull request #102", {"source.py": "second"})
        self.bakes(137)
        self.assertEqual(self.selected(2), [second, first])

    def test_long_path_only_bake_run_does_not_hide_deliveries(self) -> None:
        first = self.commit("Useful #103", {"source.py": "first"})
        self.bakes(70, by_path=True)
        self.assertEqual(self.selected(1), [first])

    def test_page_boundary_has_no_omissions_or_duplicates(self) -> None:
        wanted = []
        for count in (63, 64, 65):
            wanted.insert(0, self.commit(f"Useful #{count}", {"source.py": str(count)}))
            self.bakes(count)
        self.assertEqual(self.selected(3), wanted)
        self.assertEqual(self.selected(9), wanted)

    def test_exhaustion_returns_fewer_than_requested(self) -> None:
        first = self.commit("Useful #104", {"source.py": "first"})
        self.bakes(90)
        self.assertEqual(self.selected(8), [first])

    def test_all_bakes_exhaust_without_inventing_a_delivery(self) -> None:
        self.bakes(70, by_path=True)
        self.assertEqual(self.selected(3), [])

    def test_limit_stops_at_requested_qualifying_entry(self) -> None:
        self.commit("Older #105", {"source.py": "older"})
        latest = self.commit("Latest #106", {"source.py": "latest"})
        with patch.object(feed, "parse_commit", wraps=feed.parse_commit) as parser:
            self.assertEqual(self.selected(1), [latest])
            self.assertEqual(parser.call_count, 1)

    def test_first_parent_excludes_unmerged_branch_history(self) -> None:
        base = self.commit("Main #107", {"base.py": "base"})
        self.git("checkout", "-q", "-b", "feature")
        side = self.commit("Side #108", {"feature.py": "feature"})
        self.git("checkout", "-q", "main")
        self.git("merge", "--no-ff", "-qm", "Merge pull request #109", "feature")
        merge = self.git("rev-parse", "HEAD")
        self.bakes(68)
        rows = feed.recent_merges(10, self.root)
        self.assertEqual([row["sha"] for row in rows], [merge, base])
        self.assertNotIn(side, [row["sha"] for row in rows])
        self.assertEqual(rows[0]["paths"], ["feature.py"])

    def test_merge_at_page_boundary_follows_its_first_parent(self) -> None:
        base = self.commit("Main #201", {"base.py": "base"})
        self.git("checkout", "-q", "-b", "feature")
        side = self.commit("Side #202", {"feature.py": "feature"})
        self.git("checkout", "-q", "main")
        self.git("merge", "--no-ff", "-qm", "Merge pull request #203", "feature")
        merge = self.git("rev-parse", "HEAD")
        self.bakes(63)
        selected = self.selected(8)
        self.assertEqual(selected, [merge, base])
        self.assertNotIn(side, selected)

    def test_head_advancing_between_pages_does_not_change_snapshot(self) -> None:
        first = self.commit("Older #110", {"source.py": "older"})
        self.bakes(70)
        original_git = feed.git
        appended = []
        log_calls = []

        def advance(args: list[str], cwd: Path | None = None) -> str:
            output = original_git(args, cwd)
            if args[0] == "log":
                log_calls.append(args)
                if not appended:
                    appended.append(self.commit("New #111", {"new.py": "new"}))
            return output

        with patch.object(feed, "git", side_effect=advance):
            self.assertEqual(self.selected(2), [first])
        self.assertGreaterEqual(len(log_calls), 2)
        self.assertTrue(all("-64" in args for args in log_calls))
        self.assertEqual(self.selected(2), [appended[0], first])

    def test_mixed_source_and_generated_paths_remain_visible(self) -> None:
        sha = self.commit("Useful #112", {"source.py": "code", "llms.txt": "generated"})
        row = feed.recent_merges(1, self.root)[0]
        self.assertEqual(row["sha"], sha)
        self.assertEqual(row["pr"], 112)
        self.assertEqual(row["paths"], ["llms.txt", "source.py"])
        self.assertEqual(row["harness"], "feed-test")
        self.assertIn("harness=feed-test", feed.format_line(row))

    def test_subject_tabs_and_unicode_are_preserved(self) -> None:
        title = "Useful #113 café\tcomponent"
        sha = self.commit(title, {"source.py": "code"})
        self.bakes(2)
        row = feed.recent_merges(1, self.root)[0]
        self.assertEqual((row["sha"], row["title"]), (sha, title))

    def test_zero_limit_does_not_read_git(self) -> None:
        with patch.object(feed, "git", side_effect=AssertionError("unexpected git read")):
            self.assertEqual(self.selected(0), [])

    def test_negative_limit_is_rejected_before_reading_git(self) -> None:
        with patch.object(feed, "git", side_effect=AssertionError("unexpected git read")):
            with self.assertRaisesRegex(ValueError, "nonnegative"):
                feed.recent_merges(-1, self.root)

    def test_cli_negative_limit_is_a_usage_error_not_a_git_call(self) -> None:
        with patch.object(feed, "measure", side_effect=AssertionError("unexpected measure")):
            with contextlib.redirect_stderr(io.StringIO()) as captured:
                with self.assertRaises(SystemExit) as result:
                    feed.main(["--limit", "-1"])
        self.assertEqual(result.exception.code, 2)
        self.assertIn("--limit must be nonnegative", captured.getvalue())

    def test_later_page_failure_is_not_reported_as_partial_success(self) -> None:
        self.commit("Older #204", {"source.py": "older"})
        self.bakes(70)
        self.commit("Latest #205", {"source.py": "latest"})
        original_git = feed.git
        log_calls = 0

        def fail_later(args: list[str], cwd: Path | None = None) -> str:
            nonlocal log_calls
            if args[0] == "log":
                log_calls += 1
                if log_calls == 2:
                    raise subprocess.CalledProcessError(128, ["git", *args])
            return original_git(args, cwd)

        with patch.object(feed, "git", side_effect=fail_later):
            with self.assertRaises(subprocess.CalledProcessError):
                feed.recent_merges(3, self.root)

    def test_git_failure_is_not_reported_as_an_empty_feed(self) -> None:
        with patch.object(feed, "git", side_effect=subprocess.CalledProcessError(128, ["git"])):
            with self.assertRaises(subprocess.CalledProcessError):
                feed.recent_merges(2, self.root)


if __name__ == "__main__":
    unittest.main()
