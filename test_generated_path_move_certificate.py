import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SCRIPT = HERE / "host" / "generated_path_move_certificate.py"

from host.generated_path_move_certificate import (
    SCHEMA,
    CertificateError,
    build_certificate,
)
from host.generated_path_moves import SCHEMA as PATH_MOVES_SCHEMA


class GeneratedPathMoveCertificateTests(unittest.TestCase):
    def test_generated_only_is_safe(self):
        cert = build_certificate(
            ["feed/github.json", "projection/pending/a.json", "ground/MANUAL.md"]
        )
        self.assertEqual(cert["schema"], SCHEMA)
        self.assertEqual(cert["verdict"], "GENERATED_ONLY_SAFE")
        self.assertEqual(cert["path_moves"]["disposition"], "generated_only")
        self.assertEqual(cert["path_moves_schema"], PATH_MOVES_SCHEMA)

    def test_mixed_is_review(self):
        cert = build_certificate(["feed/github.json", "host/x.py"])
        self.assertEqual(cert["verdict"], "MIXED_REVIEW")
        self.assertEqual(cert["path_moves"]["disposition"], "mixed")

    def test_feature_is_feature(self):
        cert = build_certificate(["host/x.py", "test_x.py"])
        self.assertEqual(cert["verdict"], "FEATURE")

    def test_optional_context_attaches_without_overriding(self):
        cert = build_certificate(
            ["feed/head.json"],
            custody={"lane": "visibility-b6", "request_id": "req-1"},
            drift_status="disjoint",
            base_ref="main",
            head="a" * 40,
        )
        self.assertEqual(cert["verdict"], "GENERATED_ONLY_SAFE")
        self.assertEqual(cert["drift_status"], "disjoint")
        self.assertEqual(cert["base_ref"], "main")
        self.assertEqual(cert["head"], "a" * 40)
        self.assertEqual(cert["custody"]["lane"], "visibility-b6")

    def test_bad_custody_refuses(self):
        with self.assertRaises(CertificateError):
            build_certificate(["feed/head.json"], custody="not-a-map")  # type: ignore[arg-type]

    def test_whitespace_optional_str_refuses(self):
        with self.assertRaises(CertificateError):
            build_certificate(["feed/head.json"], drift_status=" disjoint")

    def test_path_validation_propagates(self):
        with self.assertRaises(ValueError):
            build_certificate([])

    def test_cli_emits_machine_stable_json(self):
        self.assertTrue(SCRIPT.is_file())
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "feed/github.json",
                "--drift-status",
                "current",
                "--custody-json",
                '{"k":"v"}',
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(HERE),
            env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(HERE)},
        )
        got = json.loads(proc.stdout)
        self.assertEqual(got["schema"], SCHEMA)
        self.assertEqual(got["verdict"], "GENERATED_ONLY_SAFE")
        self.assertEqual(got["drift_status"], "current")
        self.assertEqual(got["custody"], {"k": "v"})


if __name__ == "__main__":
    unittest.main()
