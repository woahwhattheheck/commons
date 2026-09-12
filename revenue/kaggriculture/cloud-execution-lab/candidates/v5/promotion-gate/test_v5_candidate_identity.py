# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import promotion_gate as gate
import v5_candidate_identity as identity


def _spec(*, activation=None):
    return {
        "schema": identity.SPEC_SCHEMA,
        "base_id": "titan-v5-main",
        "engine_id": "engine:official:3c202c7e",
        "opponent_pack_id": "release:apex_v7+arlene_v14",
        "components": [
            {
                "name": "candidate",
                "source": "candidate.py",
                "activation": activation
                or {
                    "mode": "config",
                    "equals": {"enabled": True, "count": 1, "threshold": 1.0},
                },
            }
        ],
    }


class CandidateIdentityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.source = self.repo / "candidate.py"
        self.source.write_bytes(b"VALUE = 1\n")
        self.config = b'{"enabled":true,"count":1}\n'

    def tearDown(self):
        self.temp.cleanup()

    def build(self, spec=None):
        return identity.build_manifest(
            _spec() if spec is None else spec,
            repo_root=self.repo,
            config_raw=self.config,
        )

    def test_manifest_is_accepted_by_promotion_contract(self):
        manifest = self.build()
        self.assertEqual(manifest["candidate_id"], gate.validate_manifest(manifest))
        self.assertEqual(hashlib.sha256(self.config).hexdigest(), manifest["config_sha256"])
        component = manifest["components"][0]
        self.assertEqual(hashlib.sha256(b"VALUE = 1\n").hexdigest(), component["source_sha256"])
        pairs = dict(component["activation"]["equals"]["v"])
        self.assertEqual({"t": "bool", "v": True}, pairs["enabled"])
        self.assertEqual({"t": "int", "v": "1"}, pairs["count"])
        self.assertEqual({"t": "float", "v": "0x1.0000000000000p+0"}, pairs["threshold"])

    def test_same_bytes_and_spec_are_deterministic(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)

    def test_source_or_activation_change_changes_candidate_id(self):
        first = self.build()
        self.source.write_bytes(b"VALUE = 2\n")
        source_changed = self.build()
        self.assertNotEqual(first["candidate_id"], source_changed["candidate_id"])
        self.source.write_bytes(b"VALUE = 1\n")
        activation_changed = self.build(_spec(activation={"mode": "config", "equals": {"enabled": False}}))
        self.assertNotEqual(first["candidate_id"], activation_changed["candidate_id"])

    def test_component_order_is_canonical(self):
        (self.repo / "alpha.py").write_text("A = 1\n", encoding="utf-8")
        spec = _spec()
        spec["components"] = [
            {"name": "zeta", "source": "candidate.py", "activation": {"mode": "unconditional"}},
            {"name": "alpha", "source": "alpha.py", "activation": {"mode": "unconditional"}},
        ]
        manifest = self.build(spec)
        self.assertEqual(["alpha", "zeta"], [row["name"] for row in manifest["components"]])
        self.assertEqual(manifest["candidate_id"], gate.validate_manifest(manifest))

    def test_duplicate_source_is_rejected(self):
        spec = _spec()
        spec["components"] = [
            {"name": "one", "source": "candidate.py", "activation": {"mode": "unconditional"}},
            {"name": "two", "source": "candidate.py", "activation": {"mode": "unconditional"}},
        ]
        with self.assertRaisesRegex(identity.IdentityError, "duplicate candidate component source"):
            self.build(spec)

    def test_reserved_activation_metadata_is_rejected(self):
        spec = _spec(activation={"mode": "config", "equals": {"_candidate_id": "forged"}})
        with self.assertRaisesRegex(identity.IdentityError, "reserved metadata"):
            self.build(spec)

    def test_noncanonical_or_escaping_source_is_rejected(self):
        outside = self.root / "outside.py"
        outside.write_text("OUT = 1\n", encoding="utf-8")
        for source in ("../outside.py", "/tmp/candidate.py", "a/../candidate.py"):
            with self.subTest(source=source):
                spec = _spec()
                spec["components"][0]["source"] = source
                with self.assertRaisesRegex(identity.IdentityError, "canonical relative POSIX path"):
                    self.build(spec)
        link = self.repo / "escape.py"
        try:
            link.symlink_to(outside)
        except OSError:
            return
        spec = _spec()
        spec["components"][0]["source"] = "escape.py"
        with self.assertRaisesRegex(identity.IdentityError, "escapes repo root"):
            self.build(spec)

    def test_duplicate_json_keys_and_nonfinite_values_are_rejected(self):
        with self.assertRaisesRegex(identity.IdentityError, "duplicate JSON object key"):
            identity._loads_strict(b'{"a":1,"a":2}', source="spec")
        with self.assertRaisesRegex(identity.IdentityError, "non-finite JSON constant"):
            identity._loads_strict(b'{"a":NaN}', source="spec")

    def test_cli_failure_does_not_publish_output(self):
        spec_path = self.root / "spec.json"
        config_path = self.root / "config.json"
        output = self.root / "candidate-manifest.json"
        bad = _spec(activation={"mode": "config", "equals": {}})
        spec_path.write_text(json.dumps(bad), encoding="utf-8")
        config_path.write_bytes(self.config)
        rc = identity.main(
            [
                "candidate",
                str(spec_path),
                "--repo-root",
                str(self.repo),
                "--config",
                str(config_path),
                "--output",
                str(output),
            ]
        )
        self.assertEqual(2, rc)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
