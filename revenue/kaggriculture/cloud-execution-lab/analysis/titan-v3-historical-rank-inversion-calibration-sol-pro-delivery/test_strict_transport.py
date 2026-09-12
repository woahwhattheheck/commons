from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import strict_transport as st


PATCH = b"""From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001
From: Test <test@example.com>
Date: Thu, 10 Sep 2026 00:00:00 +0000
Subject: [PATCH] add fixture

---
 x.txt | 1 +
 1 file changed, 1 insertion(+)
 create mode 100644 x.txt

diff --git a/x.txt b/x.txt
new file mode 100644
index 0000000..ce01362
--- /dev/null
+++ b/x.txt
@@ -0,0 +1 @@
+hello
-- 
2.43.0
"""


def patch_id(payload: bytes) -> str:
    proc = subprocess.run(
        ["git", "patch-id", "--stable"],
        input=payload,
        stdout=subprocess.PIPE,
        check=True,
    )
    return proc.stdout.decode("ascii").split()[0]


def build_delivery(root: Path) -> dict:
    compressed = gzip.compress(PATCH, mtime=0)
    encoded = base64.b64encode(compressed)
    width = (len(encoded) + st.EXPECTED_PART_COUNT - 1) // st.EXPECTED_PART_COUNT
    chunks = [
        encoded[index * width : (index + 1) * width]
        for index in range(st.EXPECTED_PART_COUNT)
    ]
    assert all(chunks)
    parts = []
    for index, chunk in enumerate(chunks):
        name = f"packet.b64.part-{index:02d}"
        raw = chunk + b"\n"
        (root / name).write_bytes(raw)
        parts.append(
            {
                "path": name,
                "payload_bytes": len(chunk),
                "repository_blob_bytes": len(raw),
                "repository_blob_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    manifest = {
        "schema": st.SCHEMA,
        "operation": st.OPERATION,
        "base_commit": "a" * 40,
        "transport": {
            "encoding": "base64",
            "parts_are_newline_terminated": True,
            "parts": parts,
            "decoded_gzip_bytes": len(compressed),
            "decoded_gzip_sha256": hashlib.sha256(compressed).hexdigest(),
            "decoded_patch_bytes": len(PATCH),
            "stable_patch_id": patch_id(PATCH),
            "full_tar_sha256": "b" * 64,
        },
        "change": {
            "files_added": 14,
            "lines_added": 2027,
            "runtime_policy_changed": False,
            "canonical_archive_changed": False,
            "provider_or_kaggle_changed": False,
        },
        "validation": {"tests_passed": 42, "tests_failed": 0},
    }
    (root / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def rewrite_manifest(root: Path, manifest: dict) -> None:
    (root / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_keys_rejected(self):
        with self.assertRaises(st.TransportError):
            st.strict_loads('{"x":1,"x":2}')

    def test_nan_and_overflow_rejected(self):
        for payload in ('{"x":NaN}', '{"x":Infinity}', '{"x":1e9999}'):
            with self.subTest(payload=payload):
                with self.assertRaises(st.TransportError):
                    st.strict_loads(payload)


class DeliveryVerificationTests(unittest.TestCase):
    def test_valid_delivery_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_delivery(root)
            patch, receipt = st.verify_delivery(root)
            self.assertEqual(patch, PATCH)
            self.assertEqual(receipt["stable_patch_id"], patch_id(PATCH))
            self.assertEqual(receipt["files_added_declared"], 14)

    def test_tampered_part_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_delivery(root)
            path = root / "packet.b64.part-02"
            raw = bytearray(path.read_bytes())
            raw[0] = ord("A") if raw[0] != ord("A") else ord("B")
            path.write_bytes(raw)
            with self.assertRaisesRegex(st.TransportError, "SHA-256 mismatch"):
                st.verify_delivery(root)

    def test_noncanonical_part_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            manifest["transport"]["parts"][0]["path"] = "../packet.b64.part-00"
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "non-canonical"):
                st.verify_delivery(root)

    def test_wrong_part_order_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            manifest["transport"]["parts"][0], manifest["transport"]["parts"][1] = (
                manifest["transport"]["parts"][1],
                manifest["transport"]["parts"][0],
            )
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "non-canonical"):
                st.verify_delivery(root)

    def test_missing_terminal_lf_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            path = root / "packet.b64.part-00"
            raw = path.read_bytes()[:-1]
            path.write_bytes(raw)
            item = manifest["transport"]["parts"][0]
            item["repository_blob_bytes"] = len(raw)
            item["repository_blob_sha256"] = hashlib.sha256(raw).hexdigest()
            item["payload_bytes"] = len(raw)
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "terminal LF"):
                st.verify_delivery(root)

    def test_internal_lf_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            path = root / "packet.b64.part-00"
            raw = path.read_bytes()
            raw = raw[:3] + b"\n" + raw[3:]
            path.write_bytes(raw)
            item = manifest["transport"]["parts"][0]
            item["repository_blob_bytes"] = len(raw)
            item["repository_blob_sha256"] = hashlib.sha256(raw).hexdigest()
            item["payload_bytes"] = len(raw) - 1
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "terminal LF"):
                st.verify_delivery(root)

    def test_payload_length_lie_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            manifest["transport"]["parts"][0]["payload_bytes"] += 1
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "payload byte count"):
                st.verify_delivery(root)

    def test_gzip_hash_lie_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            manifest["transport"]["decoded_gzip_sha256"] = "0" * 64
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "gzip SHA-256"):
                st.verify_delivery(root)

    def test_patch_byte_count_lie_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            manifest["transport"]["decoded_patch_bytes"] += 1
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "patch byte count"):
                st.verify_delivery(root)

    def test_patch_id_lie_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            manifest["transport"]["stable_patch_id"] = "0" * 40
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "patch-id mismatch"):
                st.verify_delivery(root)

    def test_bool_is_not_accepted_as_integer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            manifest["transport"]["parts"][0]["payload_bytes"] = True
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "expected integer"):
                st.verify_delivery(root)

    def test_files_added_contract_is_not_input_weakable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = build_delivery(root)
            manifest["change"]["files_added"] = 13
            rewrite_manifest(root, manifest)
            with self.assertRaisesRegex(st.TransportError, "must remain 14"):
                st.verify_delivery(root)

    def test_delivery_symlink_is_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            real = base / "real"
            real.mkdir()
            build_delivery(real)
            link = base / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(st.TransportError, "symlinked"):
                st.verify_delivery(link)

    def test_part_symlink_is_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_delivery(root)
            part = root / "packet.b64.part-01"
            saved = root / "saved"
            part.rename(saved)
            part.symlink_to(saved)
            with self.assertRaisesRegex(st.TransportError, "symlinked"):
                st.verify_delivery(root)


class OutputCustodyTests(unittest.TestCase):
    def test_materialize_creates_new_exact_patch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "delivery"
            root.mkdir()
            build_delivery(root)
            outdir = Path(td) / "out"
            outdir.mkdir()
            output = outdir / "packet.patch"
            receipt = st.materialize(root, output)
            self.assertEqual(output.read_bytes(), PATCH)
            self.assertEqual(receipt["output_sha256"], hashlib.sha256(PATCH).hexdigest())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "delivery"
            root.mkdir()
            build_delivery(root)
            output = Path(td) / "sentinel.patch"
            output.write_bytes(b"do-not-touch")
            with self.assertRaisesRegex(st.TransportError, "refusing to overwrite"):
                st.materialize(root, output)
            self.assertEqual(output.read_bytes(), b"do-not-touch")

    def test_output_symlink_target_is_never_overwritten(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "delivery"
            root.mkdir()
            build_delivery(root)
            target = Path(td) / "target"
            target.write_bytes(b"do-not-touch")
            output = Path(td) / "out.patch"
            output.symlink_to(target)
            with self.assertRaisesRegex(st.TransportError, "refusing to overwrite"):
                st.materialize(root, output)
            self.assertEqual(target.read_bytes(), b"do-not-touch")

    def test_symlinked_output_parent_is_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "delivery"
            root.mkdir()
            build_delivery(root)
            real = base / "real-out"
            real.mkdir()
            link = base / "out-link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(st.TransportError, "symlinked"):
                st.materialize(root, link / "packet.patch")
            self.assertEqual(list(real.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
