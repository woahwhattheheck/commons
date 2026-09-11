import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from deliverable_manifest import ManifestError, build_manifest, main


def acceptance(*criteria):
    return json.dumps({"criteria": list(criteria)}, separators=(",", ":")).encode()


def criterion(cid, description, *paths):
    return {"id": cid, "description": description, "paths": list(paths)}


class DeliverableManifestTests(unittest.TestCase):
    def make_bundle(self, root: Path, reverse=False):
        pairs = [
            ("README.txt", b"deliverable\n"),
            ("dist/app.js", b"export const answer = 42;\n"),
            ("types/app.d.ts", b"export declare const answer: number;\n"),
        ]
        if reverse:
            pairs.reverse()
        for rel, data in pairs:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def mapping(self):
        return acceptance(
            criterion("A1", "Runtime artifact is present", "dist/app.js"),
            criterion("A2", "Consumer type surface is present", "types/app.d.ts"),
            criterion("A3", "Delivery notes are present", "README.txt"),
        )

    def test_manifest_is_deterministic_across_creation_order_and_mtime(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra, rb = Path(a), Path(b)
            self.make_bundle(ra, reverse=False)
            self.make_bundle(rb, reverse=True)
            future = time.time() + 500
            os.utime(rb / "README.txt", (future, future))
            ma = build_manifest(ra, self.mapping())
            mb = build_manifest(rb, self.mapping())
            self.assertEqual(ma, mb)
            self.assertEqual(["README.txt", "dist/app.js", "types/app.d.ts"], [x["path"] for x in ma["files"]])

    def test_file_mutation_changes_manifest_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            before = build_manifest(root, self.mapping())
            (root / "dist/app.js").write_bytes(b"export const answer = 43;\n")
            after = build_manifest(root, self.mapping())
            self.assertNotEqual(before["manifest_sha256"], after["manifest_sha256"])
            self.assertNotEqual(before["files"][1]["sha256"], after["files"][1]["sha256"])

    def test_acceptance_order_and_path_order_are_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            left = acceptance(
                criterion("B", "Second", "types/app.d.ts", "README.txt"),
                criterion("A", "First", "dist/app.js"),
            )
            right = acceptance(
                criterion("A", "First", "dist/app.js"),
                criterion("B", "Second", "README.txt", "types/app.d.ts"),
            )
            self.assertEqual(build_manifest(root, left), build_manifest(root, right))

    def test_rejects_missing_mapped_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            with self.assertRaisesRegex(ManifestError, "absent file"):
                build_manifest(root, acceptance(criterion("A", "Missing", "dist/nope.js")))

    def test_rejects_duplicate_criterion_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            raw = acceptance(
                criterion("A", "One", "README.txt"),
                criterion("A", "Two", "dist/app.js"),
            )
            with self.assertRaisesRegex(ManifestError, "duplicate criterion id"):
                build_manifest(root, raw)

    def test_rejects_duplicate_path_within_criterion(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            raw = acceptance(criterion("A", "One", "README.txt", "README.txt"))
            with self.assertRaisesRegex(ManifestError, "repeats path"):
                build_manifest(root, raw)

    def test_same_file_may_support_distinct_criteria(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            raw = acceptance(
                criterion("A", "Runtime", "dist/app.js"),
                criterion("B", "Export", "dist/app.js"),
            )
            manifest = build_manifest(root, raw)
            self.assertEqual(2, len(manifest["acceptance"]))

    def test_rejects_noncanonical_acceptance_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            for bad in ("../README.txt", "/README.txt", "dist\\app.js", "dist//app.js", "dist/./app.js"):
                with self.subTest(path=bad):
                    with self.assertRaises(ManifestError):
                        build_manifest(root, acceptance(criterion("A", "Bad", bad)))

    def test_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            raw = b'{"criteria":[],"criteria":[]}'
            with self.assertRaisesRegex(ManifestError, "duplicate JSON key"):
                build_manifest(root, raw)


    def test_rejects_symlink_root(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as parent:
            real = Path(td)
            self.make_bundle(real)
            link = Path(parent) / "bundle-link"
            os.symlink(real, link)
            with self.assertRaisesRegex(ManifestError, "root must not be a symlink"):
                build_manifest(link, self.mapping())

    def test_rejects_symlink_file(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            os.symlink(root / "README.txt", root / "alias.txt")
            with self.assertRaisesRegex(ManifestError, "symlink file"):
                build_manifest(root, self.mapping())

    def test_rejects_symlink_directory(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as other:
            root = Path(td)
            self.make_bundle(root)
            os.symlink(other, root / "linked-dir")
            with self.assertRaisesRegex(ManifestError, "symlink directory"):
                build_manifest(root, self.mapping())

    def test_rejects_empty_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ManifestError, "no regular files"):
                build_manifest(Path(td), acceptance(criterion("A", "Nothing", "none")))

    def test_cli_writes_sidecar_outside_root(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "bundle"
            root.mkdir()
            self.make_bundle(root)
            amap = base / "acceptance.json"
            out = base / "receipt.json"
            amap.write_bytes(self.mapping())
            self.assertEqual(0, main([str(root), "--acceptance", str(amap), "--output", str(out)]))
            receipt = json.loads(out.read_text())
            self.assertEqual("commons-deliverable-manifest/v1", receipt["schema"])
            self.assertEqual(64, len(receipt["manifest_sha256"]))

    def test_cli_refuses_self_referential_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_bundle(root)
            amap = root.parent / "acceptance-sidecar.json"
            amap.write_bytes(self.mapping())
            with self.assertRaisesRegex(ManifestError, "outside the deliverable root"):
                main([
                    str(root),
                    "--acceptance", str(amap),
                    "--output", str(root / "manifest.json"),
                ])


if __name__ == "__main__":
    unittest.main()
