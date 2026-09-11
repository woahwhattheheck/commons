import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from host.build_receipt import ReceiptError, canonical_json, normalize_receipt


BASE = "a" * 40
HEAD = "b" * 40


def sample():
    return {
        "marker": "EXAMPLE-20260910-01",
        "base": BASE,
        "head": HEAD,
        "paths": ["z.txt", ".github/workflows/test.yml"],
        "tests": [
            {"name": "unit", "status": "pass", "command": "python -m unittest"},
            {"name": "lint", "status": "not_run"},
        ],
        "hosted": {"state": "queued", "run_ids": [42, 7]},
        "provider_nonclaims": [
            "no provider mutation",
            "no customer/payment mutation",
        ],
        "release_state": "released",
    }


class BuildReceiptTests(unittest.TestCase):
    def test_normalizes_and_sorts_without_inventing_truth(self):
        got = normalize_receipt(sample())
        self.assertEqual(got["schema_version"], "commons-build-receipt/v1")
        self.assertEqual(
            got["paths"], [".github/workflows/test.yml", "z.txt"]
        )
        self.assertEqual(
            [row["name"] for row in got["tests"]], ["lint", "unit"]
        )
        self.assertEqual(got["tests"][1]["status"], "PASS")
        self.assertEqual(got["hosted"], {"state": "QUEUED", "run_ids": [7, 42]})
        self.assertEqual(got["release_state"], "RELEASED")

    def test_canonical_json_is_stable(self):
        first = canonical_json(sample())
        payload = sample()
        payload["paths"].reverse()
        payload["tests"].reverse()
        payload["hosted"]["run_ids"].reverse()
        payload["provider_nonclaims"].reverse()
        self.assertEqual(first, canonical_json(payload))
        self.assertEqual(
            first,
            json.dumps(json.loads(first), sort_keys=True, separators=(",", ":")),
        )

    def test_rejects_missing_or_unknown_top_level_keys(self):
        payload = sample()
        payload.pop("head")
        with self.assertRaisesRegex(ReceiptError, "missing keys"):
            normalize_receipt(payload)
        payload = sample()
        payload["surprise"] = True
        with self.assertRaisesRegex(ReceiptError, "unknown keys"):
            normalize_receipt(payload)

    def test_rejects_ambiguous_git_identity_and_paths(self):
        payload = sample()
        payload["base"] = "abc123"
        with self.assertRaisesRegex(ReceiptError, "40-hex"):
            normalize_receipt(payload)
        for bad in ("../secret", "/tmp/x", r"a\b", "dir/../x", "dir/"):
            payload = sample()
            payload["paths"] = [bad]
            with self.subTest(path=bad), self.assertRaises(ReceiptError):
                normalize_receipt(payload)

    def test_rejects_duplicate_paths_tests_nonclaims_and_run_ids(self):
        payload = sample()
        payload["paths"] = ["a", "a"]
        with self.assertRaisesRegex(ReceiptError, "paths contains duplicates"):
            normalize_receipt(payload)
        payload = sample()
        payload["tests"].append({"name": "unit", "status": "PASS"})
        with self.assertRaisesRegex(ReceiptError, "duplicate test name"):
            normalize_receipt(payload)
        payload = sample()
        payload["provider_nonclaims"] = ["x", "x"]
        with self.assertRaisesRegex(ReceiptError, "contains duplicates"):
            normalize_receipt(payload)
        payload = sample()
        payload["hosted"]["run_ids"] = [1, 1]
        with self.assertRaisesRegex(ReceiptError, "contains duplicates"):
            normalize_receipt(payload)

    def test_rejects_invalid_states_and_not_run_with_ids(self):
        payload = sample()
        payload["release_state"] = "green-ish"
        with self.assertRaisesRegex(ReceiptError, "release_state invalid"):
            normalize_receipt(payload)
        payload = sample()
        payload["tests"][0]["status"] = "maybe"
        with self.assertRaisesRegex(ReceiptError, "status invalid"):
            normalize_receipt(payload)
        payload = sample()
        payload["hosted"] = {"state": "not_run", "run_ids": [99]}
        with self.assertRaisesRegex(ReceiptError, "cannot carry"):
            normalize_receipt(payload)

    def test_cli_accepts_file_and_fails_closed(self):
        root = Path(__file__).resolve().parent
        script = root / "host" / "build_receipt.py"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(sample()), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(script), str(path)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["head"], HEAD)

            path.write_text('{"marker": "broken"}', encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(script), str(path)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("missing keys", proc.stderr)


if __name__ == "__main__":
    unittest.main()
