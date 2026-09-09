from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
WORKFLOW = ROOT / ".github" / "workflows" / "titan-w10-exact-head-gate.yml"
VALID_SHA = "c179ca54ef38534ea801698aa15d5fbc3f59250f"
VALID_HEAD = "sol/verdant-w10-realized-fertilizer-certificate-20260909-03"
VALID_REPO = "woahwhattheheck/commons"
VALID_ITEM = {
    "number": 11699,
    "url": "https://github.com/woahwhattheheck/commons/pull/11699",
    "headRefName": VALID_HEAD,
    "headRefOid": VALID_SHA,
}


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _verifier_source() -> str:
    text = _workflow_text()
    marker = "pushed_sha, expected_head, expected_repo, output_path, prs_path = sys.argv[1:]"
    start = text.rfind("<<'PY'\n", 0, text.find(marker))
    if start < 0:
        raise AssertionError("exact-head verifier heredoc is missing")
    start = text.find("\n", start) + 1
    end = text.find("\n          PY\n", start)
    if end < 0:
        raise AssertionError("exact-head verifier heredoc terminator is missing")
    return textwrap.dedent(text[start:end] + "\n")


def _run_verifier(snapshot: bytes, *argv: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        snap_path = Path(tmp) / "w10-open-prs.json"
        out_path = Path(tmp) / "github-output.txt"
        snap_path.write_bytes(snapshot)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                "-",
                *argv,
                str(out_path),
                str(snap_path),
            ],
            input=_verifier_source(),
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        output = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        completed.output_file = output  # type: ignore[attr-defined]
        return completed


class ExactHeadPrVerifierTests(unittest.TestCase):
    def test_workflow_snapshots_inventory_and_does_not_share_stdin(self) -> None:
        text = _workflow_text()
        self.assertIn('printf \'%s\\n\' "$prs" > /tmp/w10-open-prs.json', text)
        self.assertIn("/tmp/w10-open-prs.json <<'PY'", text)
        self.assertNotIn("<<'PY' <<<", text)
        self.assertIn('"$GITHUB_SHA"', text)
        self.assertIn('"$head"', text)
        self.assertIn('"$repo"', text)
        self.assertIn('"$GITHUB_OUTPUT"', text)

    def test_valid_tuple_writes_github_output(self) -> None:
        completed = _run_verifier(
            json.dumps([VALID_ITEM]).encode("utf-8"),
            VALID_SHA,
            VALID_HEAD,
            VALID_REPO,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.output_file,  # type: ignore[attr-defined]
            "\n".join(
                [
                    "number=11699",
                    "url=https://github.com/woahwhattheheck/commons/pull/11699",
                    f"head_sha={VALID_SHA}",
                    "",
                ]
            ),
        )

    def test_empty_inventory_fails_closed(self) -> None:
        completed = _run_verifier(b"[]", VALID_SHA, VALID_HEAD, VALID_REPO)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("expected exactly one open PR inventory item, found 0", completed.stderr)
        self.assertEqual(completed.output_file, "")  # type: ignore[attr-defined]

    def test_duplicate_json_key_fails_closed(self) -> None:
        raw = (
            b'[{"number":11699,"number":1,"url":"https://github.com/woahwhattheheck/commons/pull/11699",'
            b'"headRefName":"sol/verdant-w10-realized-fertilizer-certificate-20260909-03",'
            b'"headRefOid":"c179ca54ef38534ea801698aa15d5fbc3f59250f"}]'
        )
        completed = _run_verifier(raw, VALID_SHA, VALID_HEAD, VALID_REPO)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("duplicate JSON key: number", completed.stderr)
        self.assertEqual(completed.output_file, "")  # type: ignore[attr-defined]

    def test_malformed_json_fails_closed(self) -> None:
        completed = _run_verifier(b"{", VALID_SHA, VALID_HEAD, VALID_REPO)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unable to parse open PR inventory", completed.stderr)
        self.assertEqual(completed.output_file, "")  # type: ignore[attr-defined]

    def test_wrong_head_ref_fails_closed(self) -> None:
        item = dict(VALID_ITEM)
        item["headRefName"] = "other-branch"
        completed = _run_verifier(json.dumps([item]).encode("utf-8"), VALID_SHA, VALID_HEAD, VALID_REPO)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not equal expected ref", completed.stderr)
        self.assertEqual(completed.output_file, "")  # type: ignore[attr-defined]

    def test_wrong_head_sha_fails_closed(self) -> None:
        item = dict(VALID_ITEM)
        item["headRefOid"] = "a" * 40
        completed = _run_verifier(json.dumps([item]).encode("utf-8"), VALID_SHA, VALID_HEAD, VALID_REPO)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not equal pushed SHA", completed.stderr)
        self.assertEqual(completed.output_file, "")  # type: ignore[attr-defined]

    def test_invalid_utf8_fails_closed(self) -> None:
        completed = _run_verifier(b"\xff\xfe", VALID_SHA, VALID_HEAD, VALID_REPO)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unable to parse open PR inventory", completed.stderr)
        self.assertEqual(completed.output_file, "")  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
