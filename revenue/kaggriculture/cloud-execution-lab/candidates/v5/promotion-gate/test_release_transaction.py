#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "_release_transaction_under_test", HERE / "release_transaction.py"
)
assert SPEC is not None and SPEC.loader is not None
rt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rt)
ECON_SPEC = importlib.util.spec_from_file_location(
    "_economics_gate_for_release_test", HERE / "economics_gate.py"
)
assert ECON_SPEC is not None and ECON_SPEC.loader is not None
econ = importlib.util.module_from_spec(ECON_SPEC)
ECON_SPEC.loader.exec_module(econ)


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def make_archive(members):
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            for name, raw in sorted(members.items()):
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(raw))
    return output.getvalue()


class ReleaseTransactionTests(unittest.TestCase):
    def setUp(self):
        self.component = b"print('candidate')\n"
        self.component_sha = sha(self.component)
        self.source = {
            "runtime": {
                "feature.py": {
                    "source_path": "feature.py",
                    "sha256": self.component_sha,
                    "bytes": len(self.component),
                }
            }
        }
        self.source_raw = canon(self.source)
        self.archive = make_archive(
            {"SOURCE.json": self.source_raw, "feature.py": self.component}
        )
        self.old_source_raw = canon(
            {"runtime": {"old.py": {
                "source_path": "old.py",
                "sha256": "1" * 64,
                "bytes": 1,
            }}}
        )
        self.old = {
            "path": "exports/titan-current.tar.gz",
            "entrypoint": "main.py::agent",
            "config": "TITAN-CONFIG.json",
            "sha256": "2" * 64,
            "bytes": 123,
            "runtime_files": 1,
            "source_manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
            "source_manifest_sha256": sha(self.old_source_raw),
        }
        self.new = {
            "path": "exports/titan-current.tar.gz",
            "entrypoint": "main.py::agent",
            "config": "TITAN-CONFIG.json",
            "sha256": sha(self.archive),
            "bytes": len(self.archive),
            "runtime_files": 1,
            "source_manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
            "source_manifest_sha256": sha(self.source_raw),
        }
        self.old_raw = canon(self.old)
        self.new_raw = canon(self.new)
        self.manifest = {
            "candidate_id": "v5c:" + "a" * 64,
            "engine_id": "engine:test-pinned",
            "opponent_pack_id": "opponent:test-pack",
            "components": [
                {
                    "name": "feature",
                    "source": "feature.py",
                    "source_sha256": self.component_sha,
                    "activation": {"mode": "unconditional"},
                }
            ],
        }
        self.engagement = {"x": 1}
        self.runtime = {"x": 2}
        self.manifest_raw = canon(self.manifest)
        self.engagement_raw = canon(self.engagement)
        self.runtime_raw = canon(self.runtime)
        self.evidence_hashes = {
            "candidate_manifest": sha(self.manifest_raw),
            "engagement_report": sha(self.engagement_raw),
            "runtime_report": sha(self.runtime_raw),
        }
        self.promotion = {
            "schema": "titan-v5-promotion-gate/v1",
            "classification": "PASS",
            "promotion_ready": True,
            "candidate_id": self.manifest["candidate_id"],
            "control_id": "v5c:" + "b" * 64,
            "evidence_sha256": dict(self.evidence_hashes),
            "engagement": {"observations": 2, "divergence_count": 1},
            "runtime": {
                "receipt_count": 2,
                "deadline_fallback_count": 0,
                "deadline_fallback_rate": 0.0,
                "p99_headroom_seconds": 0.1,
            },
        }
        self.promotion_raw = canon(self.promotion)
        cells = []
        for seed in range(10, 14):
            for seat in (0, 1):
                cells.append(
                    {
                        "seed": seed,
                        "seat": seat,
                        "control_own": 1000 + seed,
                        "control_rival": 900 + seed,
                        "candidate_own": 1010 + seed,
                        "candidate_rival": 900 + seed,
                    }
                )
        self.economics = {
            "schema": econ.SCHEMA,
            "control_id": self.promotion["control_id"],
            "candidate_id": self.promotion["candidate_id"],
            "engine_id": self.manifest["engine_id"],
            "opponent_pack_id": self.manifest["opponent_pack_id"],
            "control_archive_sha256": self.old["sha256"],
            "candidate_archive_sha256": self.new["sha256"],
            "cells": cells,
        }
        self.economics_raw = canon(self.economics)
        self.trust_result = {
            "ok": True,
            "delegate": True,
            "checked_files": ["CANONICAL.json", "INTEGRATION.json", "COMPOSITION.json"],
            "errors": [],
        }
        self.trust_files = {
            "CANONICAL.json": b'{"a":1}\n',
            "INTEGRATION.json": b'{"b":2}\n',
            "COMPOSITION.json": b'{"c":3}\n',
            "check_control_plane.py": b"def validate_control_plane(root): return {'ok': True}\n",
        }

    def builder(self, manifest, engagement, runtime, *, evidence_sha256=None):
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(engagement, self.engagement)
        self.assertEqual(runtime, self.runtime)
        self.assertEqual(evidence_sha256, self.evidence_hashes)
        return dict(self.promotion)

    def build(self, **overrides):
        kwargs = dict(
            live_pointer_raw=self.old_raw,
            expected_old_pointer_raw=self.old_raw,
            approved_new_pointer_raw=self.new_raw,
            approved_archive_raw=self.archive,
            approved_source_manifest_raw=self.source_raw,
            candidate_manifest_raw=self.manifest_raw,
            engagement_raw=self.engagement_raw,
            runtime_raw=self.runtime_raw,
            promotion_receipt_raw=self.promotion_raw,
            economics_raw=self.economics_raw,
            promotion_builder=self.builder,
            economics_builder=econ.validate_report,
            trust_result=self.trust_result,
            trust_files=self.trust_files,
        )
        kwargs.update(overrides)
        return rt.build_transaction(**kwargs)

    def test_pass_is_deterministic_and_binds_all_authorities(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(first["classification"], "PASS")
        self.assertEqual("titan-v5-release-transaction/v2", first["schema"])
        self.assertRegex(first["transition_id"], r"^v5tx:[0-9a-f]{64}$")
        self.assertEqual(first["expected_old"]["archive_sha256"], self.old["sha256"])
        self.assertEqual(first["approved_new"]["archive_sha256"], self.new["sha256"])
        self.assertEqual(
            first["promotion"]["candidate_id"], self.manifest["candidate_id"]
        )
        self.assertEqual(first["promotion"]["control_id"], self.promotion["control_id"])
        self.assertEqual(first["economics"]["report_sha256"], sha(self.economics_raw))
        self.assertEqual(first["economics"]["engine_id"], self.manifest["engine_id"])
        self.assertEqual(first["economics"]["opponent_pack_id"], self.manifest["opponent_pack_id"])
        self.assertEqual(first["economics"]["control_archive_sha256"], self.old["sha256"])
        self.assertEqual(first["economics"]["candidate_archive_sha256"], self.new["sha256"])
        self.assertEqual(first["economics"]["cell_count"], 8)
        self.assertEqual(first["economics"]["sum_margin_delta"], 80)

    def test_stale_live_pointer_fails_closed(self):
        with self.assertRaisesRegex(rt.TransactionError, "stale"):
            self.build(live_pointer_raw=b"{}\n")

    def test_noop_pointer_is_not_a_transition(self):
        with self.assertRaisesRegex(rt.TransactionError, "must differ"):
            self.build(
                approved_new_pointer_raw=self.old_raw,
                approved_archive_raw=self.archive,
            )

    def test_archive_byte_tamper_fails(self):
        with self.assertRaisesRegex(rt.TransactionError, "archive (byte count|hash)"):
            self.build(approved_archive_raw=self.archive + b"x")

    def test_detached_source_manifest_fails_even_if_pointer_hash_is_updated(self):
        changed_source = canon({"runtime": {"feature.py": {
            "source_path": "feature.py",
            "sha256": "9" * 64,
            "bytes": len(self.component),
        }}})
        changed_new = dict(self.new)
        changed_new["source_manifest_sha256"] = sha(changed_source)
        with self.assertRaisesRegex(rt.TransactionError, "SOURCE.json differs"):
            self.build(
                approved_new_pointer_raw=canon(changed_new),
                approved_source_manifest_raw=changed_source,
            )

    def test_promoted_component_must_match_packaged_member_bytes(self):
        bad_component = b"print('wrong')\n"
        bad_archive = make_archive(
            {"SOURCE.json": self.source_raw, "feature.py": bad_component}
        )
        bad_new = dict(self.new)
        bad_new["sha256"] = sha(bad_archive)
        bad_new["bytes"] = len(bad_archive)
        with self.assertRaisesRegex(rt.TransactionError, "archive member disagrees"):
            self.build(
                approved_new_pointer_raw=canon(bad_new),
                approved_archive_raw=bad_archive,
            )

    def test_promotion_receipt_must_be_exact_replay(self):
        bad = dict(self.promotion)
        bad["runtime"] = dict(bad["runtime"])
        bad["runtime"]["receipt_count"] = 999
        with self.assertRaisesRegex(rt.TransactionError, "disagrees with gate replay"):
            self.build(promotion_receipt_raw=canon(bad))

    def test_negative_economics_cannot_release(self):
        bad = json.loads(json.dumps(self.economics))
        for cell in bad["cells"]:
            cell["candidate_own"] = cell["control_own"] - 1
            cell["candidate_rival"] = cell["control_rival"]
        with self.assertRaisesRegex(rt.TransactionError, "economics gate replay failed"):
            self.build(economics_raw=canon(bad))

    def test_cross_build_economics_cannot_release(self):
        bad = json.loads(json.dumps(self.economics))
        bad["candidate_id"] = "v5c:" + "c" * 64
        with self.assertRaisesRegex(rt.TransactionError, "economics gate replay failed"):
            self.build(economics_raw=canon(bad))

    def test_stale_execution_closure_cannot_release(self):
        mutations = [
            ("engine_id", "engine:stale"),
            ("opponent_pack_id", "opponent:stale"),
            ("control_archive_sha256", "c" * 64),
            ("candidate_archive_sha256", "d" * 64),
        ]
        for key, value in mutations:
            with self.subTest(key=key):
                bad = json.loads(json.dumps(self.economics))
                bad[key] = value
                with self.assertRaisesRegex(rt.TransactionError, "economics gate replay failed"):
                    self.build(economics_raw=canon(bad))

    def test_economics_bytes_change_transition_identity(self):
        first = self.build()
        better = json.loads(json.dumps(self.economics))
        better["cells"][0]["candidate_own"] += 1
        second = self.build(economics_raw=canon(better))
        self.assertNotEqual(first["economics"]["report_sha256"], second["economics"]["report_sha256"])
        self.assertNotEqual(first["transition_id"], second["transition_id"])

    def test_trusted_base_gate_must_pass(self):
        with self.assertRaisesRegex(rt.TransactionError, "trusted-base gate"):
            self.build(trust_result={"ok": False, "errors": ["bad"]})

    def test_duplicate_json_key_is_rejected(self):
        duplicate = b'{"path":"exports/titan-current.tar.gz","path":"x"}'
        with self.assertRaisesRegex(rt.TransactionError, "duplicate JSON key"):
            self.build(approved_new_pointer_raw=duplicate)

    def test_commit_rechecks_expected_old_and_publishes_receipt_after_pointer(self):
        receipt = self.build()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pointer = root / "CURRENT-ARCHIVE.json"
            output = root / "TRANSACTION.json"
            pointer.write_bytes(self.old_raw)
            rt.commit_pointer(
                current_pointer=pointer,
                expected_old_pointer_raw=self.old_raw,
                approved_new_pointer_raw=self.new_raw,
                receipt_path=output,
                receipt=receipt,
            )
            self.assertEqual(pointer.read_bytes(), self.new_raw)
            self.assertEqual(json.loads(output.read_text()), receipt)

    def test_commit_rejects_stale_pointer_without_receipt(self):
        receipt = self.build()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pointer = root / "CURRENT-ARCHIVE.json"
            output = root / "TRANSACTION.json"
            pointer.write_bytes(b"stale")
            with self.assertRaisesRegex(rt.TransactionError, "changed before commit"):
                rt.commit_pointer(
                    current_pointer=pointer,
                    expected_old_pointer_raw=self.old_raw,
                    approved_new_pointer_raw=self.new_raw,
                    receipt_path=output,
                    receipt=receipt,
                )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
