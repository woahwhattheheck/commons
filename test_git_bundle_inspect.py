"""Real Git interoperability plus bounded malformed-input coverage."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import random
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from host.git_bundle_inspect import (
    BundleError, Limits, export_objects, inspect_bundle, inspect_file,
)


def object_id(kind, data, algorithm="sha1"):
    return hashlib.new(algorithm, f"{kind} {len(data)}\0".encode() + data).hexdigest()


def size_header(kind, size):
    output = bytearray([(kind << 4) | (size & 15)])
    size >>= 4
    while size:
        output[-1] |= 128
        output.append(size & 127)
        size >>= 7
    return bytes(output)


def varint(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def entry(kind, data, base=b""):
    return size_header(kind, len(data)) + base + zlib.compress(data)


def bundle(entries, refs=None, prerequisites=(), capabilities=(), version=2, algorithm="sha1", pack_version=2):
    refs = refs if refs is not None else [("0" * (hashlib.new(algorithm).digest_size * 2), "refs/heads/test")]
    header = f"# v{version} git bundle\n".encode()
    header += b"".join(b"@" + cap + b"\n" for cap in capabilities)
    header += b"".join(b"-" + oid.encode() + b" baseline\n" for oid in prerequisites)
    header += b"".join(oid.encode() + b" " + name.encode() + b"\n" for oid, name in refs) + b"\n"
    pack = b"PACK" + struct.pack(">II", pack_version, len(entries)) + b"".join(entries)
    return header + pack + hashlib.new(algorithm, pack).digest()


def git(directory, *arguments, input=None):
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
           "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
           "GIT_AUTHOR_DATE": "2020-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2020-01-01T00:00:00Z",
           "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(["git", "-c", f"core.hooksPath={os.devnull}", *arguments], cwd=directory,
                          input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=env, check=True, timeout=20).stdout


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.content = b"hello\n"
        self.oid = object_id("blob", self.content)
        self.sample = bundle([entry(3, self.content)], refs=[(self.oid, "refs/heads/test")])

    def tearDown(self):
        self.tmp.cleanup()

    def test_blob_and_metadata(self):
        result = inspect_bundle(self.sample)
        self.assertEqual(result.objects[self.oid].data, self.content)
        self.assertEqual(result.report["recovery_status"], "self_contained_objects")
        self.assertFalse(result.report["restore_verified"])
        self.assertEqual(result.report["bundle_sha256"], hashlib.sha256(self.sample).hexdigest())

    def test_sha256_v3(self):
        oid = object_id("blob", self.content, "sha256")
        result = inspect_bundle(bundle([entry(3, self.content)], refs=[(oid, "HEAD")], version=3,
                                       capabilities=(b"object-format=sha256",), algorithm="sha256"))
        self.assertIn(oid, result.objects)
        self.assertEqual(result.report["object_format"], "sha256")

    def test_forward_reference_delta(self):
        delta = varint(6) + varint(8) + b"\x90\x06\x02ok"
        result = inspect_bundle(bundle([entry(7, delta, bytes.fromhex(self.oid)), entry(3, self.content)]))
        self.assertIn(object_id("blob", b"hello\nok"), result.objects)
        self.assertEqual(result.report["resolved_entries"], 2)

    def test_offset_delta(self):
        first = entry(3, self.content)
        delta = b"\x06\x08\x90\x06\x02ok"
        result = inspect_bundle(bundle([first, entry(6, delta, bytes([len(first)]))]))
        self.assertIn(object_id("blob", b"hello\nok"), result.objects)

    def test_missing_base_remains_partial(self):
        delta = b"\x06\x08\x90\x06\x02ok"
        result = inspect_bundle(bundle([entry(7, delta, bytes.fromhex(self.oid))]))
        self.assertEqual(len(result.report["unresolved_deltas"]), 1)
        self.assertEqual(result.report["recovery_status"], "partial")
        self.assertEqual(result.objects, {})

    def test_prerequisites_remain_explicit(self):
        data = bundle([entry(3, self.content)], refs=[(self.oid, "HEAD")], prerequisites=("a" * 40,))
        result = inspect_bundle(data)
        self.assertEqual(result.report["recovery_status"], "partial")
        self.assertEqual(result.report["prerequisites"][0]["oid"], "a" * 40)

    def test_filter_never_claims_self_contained(self):
        result = inspect_bundle(bundle([entry(3, self.content)], refs=[(self.oid, "HEAD")],
                                       version=3, capabilities=(b"filter=blob:none",)))
        self.assertEqual(result.report["recovery_status"], "partial")

    def test_checksum_and_truncation(self):
        bad = bytearray(self.sample)
        bad[-1] ^= 1
        for data in (bytes(bad), self.sample[:-1], self.sample[:30], b"not a bundle"):
            with self.subTest(data=data[:20]), self.assertRaises(BundleError):
                inspect_bundle(data)

    def test_compressed_size_bounds(self):
        for packed in (size_header(3, 2) + zlib.compress(b"toolong"),
                       size_header(3, 10) + zlib.compress(b"short"),
                       size_header(3, 10) + b"not zlib"):
            with self.subTest(packed=packed), self.assertRaises(BundleError):
                inspect_bundle(bundle([packed]))

    def test_invalid_delta_controls(self):
        deltas = [b"\x06", b"\x06\x01\x00", b"\x06\x01\x02x", b"\x06\x01\x90\x07",
                  b"\x06\x01\x91", b"\x06\x02\x01x", b"\x80" * 11]
        for delta in deltas:
            with self.subTest(delta=delta), self.assertRaises(BundleError):
                inspect_bundle(bundle([entry(7, delta, bytes.fromhex(self.oid))]))

    def test_offset_must_name_entry(self):
        for distance in (0, 1, 127):
            with self.subTest(distance=distance), self.assertRaises(BundleError):
                inspect_bundle(bundle([entry(6, b"\x06\x01\x01x", bytes([distance]))]))

    def test_unsupported_capability_and_header_order(self):
        for data in (bundle([], version=3, capabilities=(b"unknown=yes",)),
                     bundle([], version=2, capabilities=(b"object-format=sha1",)),
                     bundle([], version=3, capabilities=(b"object-format=sha512",)),
                     bundle([], version=3, capabilities=(b"filter=x", b"filter=y")),
                     bundle([], refs=[("0" * 40, "HEAD"), ("0" * 40, "HEAD")])):
            with self.subTest(data=data[:100]), self.assertRaises(BundleError):
                inspect_bundle(data)

    def test_limits(self):
        for limits in (Limits(input_bytes=10), Limits(header_bytes=10), Limits(object_bytes=1),
                       Limits(decoded_bytes=1)):
            with self.subTest(limits=limits), self.assertRaises(BundleError):
                inspect_bundle(self.sample, limits)
        with self.assertRaises(BundleError):
            Limits(objects=0)
        with self.assertRaises(BundleError):
            inspect_bundle(bundle([entry(3, b"a"), entry(3, b"b")]), Limits(objects=1))

    def test_delta_depth_and_total_budget(self):
        base = b"a"
        rows = [entry(3, base)]
        for _ in range(3):
            delta = varint(len(base)) + varint(len(base) + 1) + bytes([0x90, len(base), 1]) + b"b"
            rows.append(entry(7, delta, bytes.fromhex(object_id("blob", base))))
            base += b"b"
        data = bundle(rows)
        self.assertIn(object_id("blob", base), inspect_bundle(data).objects)
        with self.assertRaises(BundleError):
            inspect_bundle(data, Limits(delta_depth=2))
        with self.assertRaises(BundleError):
            inspect_bundle(data, Limits(decoded_bytes=25))

    def test_tree_missing_links_and_gitlinks(self):
        tree = b"100644 file\0" + bytes.fromhex(self.oid) + b"160000 submodule\0" + b"x" * 20
        tid = object_id("tree", tree)
        result = inspect_bundle(bundle([entry(2, tree)], refs=[(tid, "HEAD")]))
        self.assertEqual(result.report["missing_object_links"], [self.oid])
        result = inspect_bundle(bundle([entry(2, tree), entry(3, self.content)], refs=[(tid, "HEAD")]))
        self.assertEqual(result.report["recovery_status"], "self_contained_objects")

    def test_malformed_object_links(self):
        for kind, data in ((2, b"100644 file"), (1, b"no header"), (4, b"tag t\n\nmsg")):
            with self.subTest(kind=kind), self.assertRaises(BundleError):
                inspect_bundle(bundle([entry(kind, data)]))

    def test_export_never_uses_ref_paths_or_overwrites(self):
        result = inspect_bundle(bundle([entry(3, self.content)], refs=[(self.oid, "../../escape")]))
        target = self.root / "output"
        export_objects(result, target)
        self.assertEqual((target / f"{self.oid}.blob").read_bytes(), self.content)
        self.assertEqual(set(p.name for p in target.iterdir()), {f"{self.oid}.blob", "manifest.json"})
        self.assertEqual(stat.S_IMODE((target / f"{self.oid}.blob").stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            export_objects(result, target)

    def test_file_and_cli(self):
        path = self.root / "input.bundle"
        path.write_bytes(self.sample)
        self.assertEqual(inspect_file(path).report["pack_checksum_valid"], True)
        command = [sys.executable, "-m", "host.git_bundle_inspect", str(path)]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["unique_recovered_objects"], 1)
        proc = subprocess.run(command + ["--max-input-bytes", "1"], capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stderr)["recovery_status"], "failed")

    def test_multichunk_zlib_stream(self):
        content = random.Random(24).randbytes(180000)
        oid = object_id("blob", content)
        result = inspect_bundle(bundle([entry(3, content)], refs=[(oid, "HEAD")]))
        self.assertEqual(result.objects[oid].data, content)

    def test_default_65536_delta_copy_size(self):
        base = b"x" * 65536
        oid = object_id("blob", base)
        delta = varint(len(base)) + varint(len(base)) + b"\x80"
        result = inspect_bundle(bundle([entry(3, base), entry(7, delta, bytes.fromhex(oid))]))
        self.assertEqual(result.report["resolved_entries"], 2)
        self.assertEqual(result.objects[oid].data, base)

    def test_delta_base_length_mismatch(self):
        bad = b"\x07\x01\x01x"
        with self.assertRaisesRegex(BundleError, "base size mismatch"):
            inspect_bundle(bundle([entry(3, self.content), entry(7, bad, bytes.fromhex(self.oid))]))

    def test_empty_blob(self):
        oid = object_id("blob", b"")
        result = inspect_bundle(bundle([entry(3, b"")], refs=[(oid, "HEAD")]))
        self.assertEqual(result.objects[oid].data, b"")

    def test_pack_versions_and_invalid_types(self):
        self.assertEqual(inspect_bundle(bundle([entry(3, b"a")], pack_version=3)).report["pack_version"], 3)
        for data in (bundle([], pack_version=1), bundle([entry(0, b"")]), bundle([entry(5, b"")])):
            with self.subTest(data=data), self.assertRaises(BundleError):
                inspect_bundle(data)

    def test_declared_count_mismatch(self):
        original = bundle([entry(3, b"a")])
        start = original.index(b"PACK")
        for count in (0, 2):
            pack = bytearray(original[start:-20])
            struct.pack_into(">I", pack, 8, count)
            data = original[:start] + pack + hashlib.sha1(pack).digest()
            with self.subTest(count=count), self.assertRaises(BundleError):
                inspect_bundle(data)

    def test_object_link_budget(self):
        tree = b"100644 a\0" + bytes.fromhex(self.oid) + b"100644 b\0" + bytes.fromhex(self.oid)
        data = bundle([entry(2, tree), entry(3, self.content)])
        with self.assertRaisesRegex(BundleError, "link count"):
            inspect_bundle(data, dataclasses.replace(Limits(), object_links=1))

    def test_wrong_dependency_type(self):
        commit = b"tree " + self.oid.encode() + b"\n\nmessage"
        with self.assertRaisesRegex(BundleError, "wrong type"):
            inspect_bundle(bundle([entry(1, commit), entry(3, self.content)]))


@unittest.skipUnless(shutil.which("git"), "Git required for independent interoperability fixtures")
class RealGitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "first.txt").write_text("first\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "first")
        self.base = git(self.repo, "rev-parse", "HEAD").strip().decode()
        (self.repo / "second.txt").write_text("second\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "second")
        git(self.repo, "tag", "-a", "-m", "fixture", "v1")

    def tearDown(self):
        self.tmp.cleanup()

    def compare_objects(self, result):
        for oid, obj in result.objects.items():
            self.assertEqual(git(self.repo, "cat-file", "-t", oid).strip().decode(), obj.kind)
            self.assertEqual(git(self.repo, "cat-file", obj.kind, oid), obj.data)

    def test_full_bundle_and_native_restore(self):
        path = self.root / "full.bundle"
        git(self.repo, "bundle", "create", str(path), "--all")
        result = inspect_file(path)
        self.assertEqual(result.report["recovery_status"], "self_contained_objects")
        self.compare_objects(result)
        git(self.repo, "bundle", "verify", str(path))
        git(self.root, "clone", "-q", str(path), "restored")
        git(self.root / "restored", "fsck", "--full")
        self.assertEqual((self.root / "restored/second.txt").read_bytes(), b"second\n")

    def test_thin_bundle_recovers_new_blob_without_base(self):
        path = self.root / "thin.bundle"
        git(self.repo, "bundle", "create", str(path), "HEAD", "^" + self.base)
        result = inspect_file(path)
        self.assertEqual(result.report["recovery_status"], "partial")
        self.assertEqual(result.report["prerequisites"][0]["oid"], self.base)
        self.assertIn(object_id("blob", b"second\n"), result.objects)
        self.compare_objects(result)
        empty = self.root / "empty"
        empty.mkdir()
        git(empty, "init", "-q")
        with self.assertRaises(subprocess.CalledProcessError):
            git(empty, "bundle", "verify", str(path))

    def test_real_delta_pack(self):
        # Real git pack-objects delta output, not a Python replacement for Git.
        for index in range(8):
            (self.repo / "similar.txt").write_text("line\n" * 2000 + str(index), encoding="utf-8")
            git(self.repo, "add", ".")
            git(self.repo, "commit", "-qm", f"revision {index}")
        ids = git(self.repo, "rev-list", "--objects", "--all")
        pack = git(self.repo, "pack-objects", "--stdout", "--delta-base-offset", input=ids)
        head = git(self.repo, "rev-parse", "HEAD").strip()
        data = b"# v2 git bundle\n" + head + b" refs/heads/main\n\n" + pack
        result = inspect_bundle(data)
        self.assertGreater(result.report["decoded_bytes"], sum(len(obj.data) for obj in result.objects.values()))
        self.assertEqual(result.report["recovery_status"], "self_contained_objects")
        self.compare_objects(result)

    def test_real_sha256_bundle(self):
        repo = self.root / "sha256"
        repo.mkdir()
        git(repo, "init", "-q", "--object-format=sha256")
        (repo / "f").write_bytes(b"sha256 fixture")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "sha256")
        path = self.root / "sha256.bundle"
        git(repo, "bundle", "create", str(path), "--all")
        result = inspect_file(path)
        self.assertEqual(result.report["object_format"], "sha256")
        self.assertEqual(result.report["recovery_status"], "self_contained_objects")
        for oid, obj in result.objects.items():
            self.assertEqual(git(repo, "cat-file", obj.kind, oid), obj.data)


if __name__ == "__main__":
    unittest.main()
