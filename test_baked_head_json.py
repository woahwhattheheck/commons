import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import llms_txt


ROOT = Path(__file__).resolve().parent
SHA = "a" * 40
NOW = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


class BakedHeadJsonTests(unittest.TestCase):
    def test_scheduled_publisher_tracks_head_json(self):
        self.assertIn("head.json", llms_txt.PUBLISH_OUTPUTS)

    def test_writer_emits_schema_pinned_observation_deterministically(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "head.json"
            first = llms_txt.write_head_json(SHA, "2026-09-01T10:00:00Z", path)
            one = path.read_bytes()
            second = llms_txt.write_head_json(SHA, "2026-09-01T10:00:00Z", path)
            self.assertEqual(one, path.read_bytes())
            self.assertEqual(first, second)
            self.assertEqual(json.loads(one)["schema"], "commons-head-v1")
            self.assertEqual(json.loads(one)["status"], "BAKED_OBSERVATION")

    def test_fresh_bake_is_preferred_without_remote_read(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "head.json"
            llms_txt.write_head_json(SHA, "2026-09-01T09:55:00Z", path)
            calls = []
            result = llms_txt.resolve_head(
                path=path,
                now=NOW,
                remote_reader=lambda: calls.append(True),
            )
            self.assertEqual(result["sha"], SHA)
            self.assertEqual(result["status"], "BAKED_OBSERVED")
            self.assertFalse(result["is_current"])
            self.assertEqual(calls, [])

    def test_stale_bake_falls_back_to_git_remote_measurement(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "head.json"
            llms_txt.write_head_json(SHA, "2026-09-01T09:00:00Z", path)
            remote = "b" * 40
            result = llms_txt.resolve_head(
                path=path,
                now=NOW,
                remote_reader=lambda: remote,
            )
            self.assertEqual(result["sha"], remote)
            self.assertEqual(result["source"], "git-ls-remote")
            self.assertEqual(result["status"], "REMOTE_CURRENT")
            self.assertTrue(result["is_current"])

    def test_remote_reader_uses_ls_remote_main(self):
        with mock.patch.object(
            llms_txt.subprocess,
            "check_output",
            return_value=f"{SHA}\trefs/heads/main\n",
        ) as read:
            self.assertEqual(llms_txt.git_remote_head(), SHA)
        self.assertEqual(
            read.call_args.args[0],
            ["git", "ls-remote", "origin", "refs/heads/main"],
        )

    def test_remote_failure_returns_stale_only_with_explicit_mark(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "head.json"
            llms_txt.write_head_json(SHA, "2026-09-01T09:00:00Z", path)

            def fail():
                raise RuntimeError("measured remote failure")

            result = llms_txt.resolve_head(path=path, now=NOW, remote_reader=fail)
            self.assertEqual(result["sha"], SHA)
            self.assertEqual(result["status"], "BAKED_STALE")
            self.assertFalse(result["is_current"])

    def test_invalid_bake_uses_remote(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "head.json"
            path.write_text('{"schema":"wrong","sha":"not-a-sha"}\n', encoding="utf-8")
            result = llms_txt.resolve_head(
                path=path,
                now=NOW,
                remote_reader=lambda: "c" * 40,
            )
            self.assertEqual(result["status"], "REMOTE_CURRENT")

    def test_future_bake_and_invalid_remote_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "head.json"
            llms_txt.write_head_json(SHA, "2026-09-01T10:10:01Z", path)
            self.assertIsNone(llms_txt.read_baked_head(path=path, now=NOW))
            with self.assertRaises(RuntimeError):
                llms_txt.resolve_head(
                    path=path,
                    now=NOW,
                    remote_reader=lambda: "not-a-sha",
                )

    def test_browser_reader_prefers_bake_and_marks_it_observed(self):
        script = r'''
global.window = {};
global.sessionStorage = { getItem: () => null, setItem: () => {} };
global.fetch = async function (url) {
  if (String(url).indexOf("head.json") >= 0) {
    return { ok: true, json: async () => ({
      schema: "commons-head-v1",
      sha: "dddddddddddddddddddddddddddddddddddddddd",
      observed_at: new Date().toISOString(),
      source: "scheduled-pages-bake",
      status: "BAKED_OBSERVATION"
    }) };
  }
  throw new Error("GitHub API fallback must not run for a fresh bake: " + url);
};
require("./head.js");
window.COMMONS_HEAD.headState().then(function (state) {
  if (state.status !== "BAKED_OBSERVED" || state.is_current !== false) process.exit(2);
  process.stdout.write(JSON.stringify(state));
}).catch(function (err) { console.error(err); process.exit(3); });
'''
        result = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["source"], "scheduled-pages-bake")

    def test_existing_baked_file_is_valid_and_bounded(self):
        path = ROOT / "head.json"
        baked = json.loads(path.read_text(encoding="utf-8"))
        baked_at = datetime.fromisoformat(baked["observed_at"].replace("Z", "+00:00"))
        observed = llms_txt.read_baked_head(path, now=baked_at + timedelta(minutes=1))
        self.assertIsNotNone(observed)
        self.assertEqual(observed["schema"], "commons-head-v1")


if __name__ == "__main__":
    unittest.main()
