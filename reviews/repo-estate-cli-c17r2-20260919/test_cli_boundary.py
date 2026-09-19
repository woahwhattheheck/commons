"""Independent offline acceptance for the existing repository-estate CLI.

All input records are fictional. Each test runs in a newly-created directory;
no repository, provider, workflow, or caller input is mutated. Source is copied
once into a fresh import tree, so this suite does not consume checkout pyc files.
Run from a repository root with unittest discovery, or set REPO_ESTATE_REVIEW_ROOT.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

SOURCE_PATHS = (
    "tools/__init__.py",
    "tools/repo_estate_rationalizer/__init__.py",
    "tools/repo_estate_rationalizer/schema.py",
    "tools/repo_estate_rationalizer/rationalizer.py",
)
SHA = "a" * 40
NOW = datetime(2026, 9, 19, 12, tzinfo=UTC)


def stamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def inputs(now: datetime):
    when = stamp(now - timedelta(minutes=1))
    snapshot = {
        "schema": "commons.repo-estate.snapshot/v1",
        "owner": "fictional-review",
        "captured_at": when,
        "repositories": [
            {"name": "fixture-public", "visibility": "public", "archived": False,
             "default_branch": "main", "default_branch_sha": None},
            {"name": "fixture-private", "visibility": "private", "archived": False,
             "default_branch": "main", "default_branch_sha": SHA},
        ],
    }
    evidence = {"schema": "commons.repo-estate.evidence/v1", "repositories": []}
    return snapshot, evidence


def evidence_row(now: datetime, **changes):
    when = stamp(now - timedelta(minutes=1))
    row = {
        "repository": "fixture-private", "default_branch_sha": SHA,
        "intent": "review_public", "owner_authorized": True,
        "owner_authority_ref": "fixture:owner", "archive_authorized": True,
        "archive_authority_ref": "fixture:archive",
        "secret_scan": {"result": "CLEAR", "commit_sha": SHA,
                        "observed_at": when, "ref": "fixture:scan"},
        "content_classification": "PUBLIC_RELEASE_OK",
        "content_classification_ref": "fixture:content",
        "legal_ip_review": "CLEAR_FOR_PUBLIC_RELEASE", "legal_ip_ref": "fixture:legal",
        "open_work": {"open_prs": 0, "open_issues": 0, "active_claims": 0,
                      "observed_at": when, "ref": "fixture:work"},
        "dependencies": {"consumer_count": 0, "replacement_repository": None,
                         "replacement_verified": False, "observed_at": when,
                         "ref": "fixture:dependencies"},
    }
    row.update(changes)
    return row


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class PublicBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ.get("REPO_ESTATE_REVIEW_ROOT", Path(__file__).resolve().parents[2]))
        cls.captured = {name: (source / name).read_bytes() for name in SOURCE_PATHS}
        cls.source_blobs = {name: git_blob(data) for name, data in cls.captured.items()}
        cls.source_temp = tempfile.TemporaryDirectory(prefix="estate-source-")
        cls.addClassCleanup(cls.source_temp.cleanup)
        cls.root = Path(cls.source_temp.name)
        for name, data in cls.captured.items():
            dest = cls.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        # These exact copied source files have no retained import cache.
        cls.previous_modules = {k: v for k, v in sys.modules.items()
                                if k == "tools" or k.startswith("tools.repo_estate_rationalizer")}
        for key in cls.previous_modules:
            sys.modules.pop(key)
        sys.path.insert(0, str(cls.root))
        cls.rr = importlib.import_module("tools.repo_estate_rationalizer.rationalizer")
        cls.addClassCleanup(cls.restore_modules)

    @classmethod
    def restore_modules(cls):
        for key in list(sys.modules):
            if key == "tools" or key.startswith("tools.repo_estate_rationalizer"):
                sys.modules.pop(key)
        sys.modules.update(cls.previous_modules)
        if str(cls.root) in sys.path:
            sys.path.remove(str(cls.root))

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="estate-case-")
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.snapshot, self.evidence = inputs(datetime.now(UTC).replace(microsecond=0))
        self.s = self.directory / "snapshot.json"
        self.e = self.directory / "evidence.json"
        self.out = self.directory / "packet.json"
        self.md = self.directory / "packet.md"
        self.save_inputs()

    def save_inputs(self):
        self.s.write_text(json.dumps(self.snapshot), encoding="utf-8")
        self.e.write_text(json.dumps(self.evidence), encoding="utf-8")

    def arguments(self, command="compile", *, out=None, md=None):
        args = [command, "--snapshot", str(self.s), "--evidence", str(self.e)]
        if command == "compile":
            return args + ["--out", str(out or self.out), "--markdown", str(md or self.md)]
        return args + ["--packet", str(self.out), "--markdown", str(self.md)]

    def child(self, args, *, module=True):
        target = ["-m", "tools.repo_estate_rationalizer.rationalizer"] if module else [str(self.root / SOURCE_PATHS[-1])]
        cmd = [sys.executable, *("-O" for _ in range(sys.flags.optimize)), "-B", *target, *args]
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONOPTIMIZE"}}
        env["PYTHONPATH"] = str(self.root)
        return subprocess.run(cmd, cwd=self.root, env=env, capture_output=True,
                              text=True, timeout=15)

    def in_process(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = self.rr.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def refused(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("REFUSED:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("VERIFIED", result.stdout)

    def test_real_cli_compile_verify_and_source_preservation(self):
        before = (self.s.read_bytes(), self.e.read_bytes())
        done = self.child(self.arguments())
        self.assertEqual(done.returncode, 0, done.stderr)
        packet = json.loads(self.out.read_bytes())
        self.assertEqual(packet["estate"]["state_counts"], {"HOLD": 1, "PUBLIC_ALREADY": 1})
        for key, value in packet["authority"].items():
            self.assertIs(value, key == "advisory_only")
        checked = self.child(self.arguments("verify"))
        self.assertEqual((checked.returncode, checked.stdout), (0, "VERIFIED\n"), checked.stderr)
        self.assertEqual(before, (self.s.read_bytes(), self.e.read_bytes()))

    def test_script_and_module_public_interfaces_agree_semantically(self):
        self.assertEqual(self.child(self.arguments()).returncode, 0)
        other, other_md = self.directory / "other.json", self.directory / "other.md"
        run = self.child(self.arguments(out=other, md=other_md), module=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        a, b = json.loads(self.out.read_bytes()), json.loads(other.read_bytes())
        for value in (a, b):
            value.pop("evaluated_at"); value.pop("packet_sha256")
        self.assertEqual(a, b)

    def test_invalid_visibility_json_shapes_refuse_without_traceback(self):
        for value in ([], {}, ["private"], {"private": True}, None, True, 1):
            with self.subTest(value=value):
                self.snapshot["repositories"][1]["visibility"] = value
                self.save_inputs()
                self.refused(self.child(self.arguments()))
                self.assertFalse(self.out.exists())

    def test_invalid_intent_json_shapes_refuse_without_traceback(self):
        for value in ([], {}, ["review_public"], {"review_public": True}, None, True, 1):
            with self.subTest(value=value):
                self.evidence["repositories"] = [evidence_row(datetime.now(UTC), intent=value)]
                self.save_inputs()
                self.refused(self.child(self.arguments()))
                self.assertFalse(self.out.exists())

    def test_duplicate_json_key_refuses_before_output(self):
        self.s.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
        self.refused(self.child(self.arguments()))
        self.assertFalse(self.out.exists())

    def test_bad_input_utf8_refuses_before_output(self):
        self.s.write_bytes(b"\xff\xfe")
        self.refused(self.child(self.arguments()))
        self.assertEqual(self.s.read_bytes(), b"\xff\xfe")
        self.assertFalse(self.out.exists())

    def test_bad_markdown_utf8_is_a_typed_verification_refusal(self):
        self.assertEqual(self.child(self.arguments()).returncode, 0)
        before = self.out.read_bytes()
        self.md.write_bytes(b"\xff\xfe")
        self.refused(self.child(self.arguments("verify")))
        self.assertEqual(self.out.read_bytes(), before)
        self.assertEqual(self.md.read_bytes(), b"\xff\xfe")

    def test_unencodable_evidence_text_is_a_typed_refusal(self):
        self.evidence["repositories"] = [evidence_row(datetime.now(UTC), content_classification="\ud800")]
        self.save_inputs()
        self.refused(self.child(self.arguments()))
        self.assertFalse(self.out.exists())

    def test_existing_packet_output_is_preserved(self):
        self.out.write_bytes(b"prior-reviewed-packet")
        self.refused(self.child(self.arguments()))
        self.assertEqual(self.out.read_bytes(), b"prior-reviewed-packet")
        self.assertFalse(self.md.exists())

    def test_existing_markdown_retains_first_new_output_without_overwrite(self):
        self.md.write_bytes(b"prior-reviewed-markdown")
        self.refused(self.child(self.arguments()))
        self.assertEqual(self.md.read_bytes(), b"prior-reviewed-markdown")
        packet = json.loads(self.out.read_bytes())
        self.assertTrue(self.rr.verify_packet(packet, self.snapshot, self.evidence))

    def test_shared_output_path_refuses_and_retains_first_json(self):
        self.refused(self.child(self.arguments(md=self.out)))
        self.assertEqual(json.loads(self.out.read_bytes())["schema"], "commons.repo-estate.rationalizer/v1")

    def test_output_parent_file_gives_typed_refusal(self):
        parent = self.directory / "not-a-directory"
        parent.write_bytes(b"existing-parent")
        self.refused(self.child(self.arguments(out=parent / "packet.json")))
        self.assertEqual(parent.read_bytes(), b"existing-parent")
        self.assertFalse(self.md.exists())

    def test_input_path_as_output_never_changes_inputs(self):
        before = (self.s.read_bytes(), self.e.read_bytes())
        for target in (self.s, self.e):
            with self.subTest(target=target.name):
                self.refused(self.child(self.arguments(out=target)))
                self.assertEqual(before, (self.s.read_bytes(), self.e.read_bytes()))
        self.assertFalse(self.md.exists())

    def test_hardlink_output_alias_never_changes_source(self):
        before = self.s.read_bytes()
        alias = self.directory / "alias.json"
        os.link(self.s, alias)
        self.refused(self.child(self.arguments(out=alias)))
        self.assertEqual(alias.read_bytes(), before)
        self.assertEqual(self.s.read_bytes(), before)

    def test_symlink_input_is_refused(self):
        original = self.directory / "original.json"
        self.s.rename(original)
        self.s.symlink_to(original)
        self.refused(self.child(self.arguments()))
        self.assertFalse(self.out.exists())

    def test_fifo_input_is_refused_without_blocking(self):
        self.s.unlink()
        os.mkfifo(self.s)
        self.refused(self.child(self.arguments()))
        self.assertFalse(self.out.exists())

    def test_read_error_becomes_refusal_and_preserves_input(self):
        before = self.s.read_bytes()
        with patch.object(self.rr.os, "read", side_effect=OSError("fixture read failure")):
            code, output, error = self.in_process(self.arguments())
        self.assertEqual(code, 2)
        self.assertIn("REFUSED:", error)
        self.assertFalse(output)
        self.assertEqual(self.s.read_bytes(), before)
        self.assertFalse(self.out.exists())

    def test_output_open_error_becomes_refusal(self):
        original = self.rr.os.open
        def refuse_output(name, flags, *args, **kwargs):
            if flags & os.O_CREAT:
                raise PermissionError("fixture output permission failure")
            return original(name, flags, *args, **kwargs)
        with patch.object(self.rr.os, "open", side_effect=refuse_output):
            code, output, error = self.in_process(self.arguments())
        self.assertEqual(code, 2)
        self.assertIn("REFUSED:", error)
        self.assertFalse(output)
        self.assertFalse(self.out.exists())

    def test_write_error_retains_partial_file_for_inspection(self):
        original = self.rr.os.write
        calls = 0
        def limited_write(fd, data):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original(fd, data[:12])
            raise OSError("fixture write failure")
        with patch.object(self.rr.os, "write", side_effect=limited_write):
            code, output, error = self.in_process(self.arguments())
        self.assertEqual(code, 2)
        self.assertIn("REFUSED:", error)
        self.assertFalse(output)
        self.assertEqual(self.out.stat().st_size, 12)
        self.assertFalse(self.md.exists())

    def test_fsync_error_retains_file_but_does_not_print_success(self):
        with patch.object(self.rr.os, "fsync", side_effect=OSError("fixture fsync failure")):
            code, output, error = self.in_process(self.arguments())
        self.assertEqual(code, 2)
        self.assertIn("REFUSED:", error)
        self.assertFalse(output)
        self.assertTrue(self.out.exists())
        self.assertFalse(self.md.exists())

    def test_receipt_and_exact_json_types_are_verified(self):
        rr = self.rr
        snap, evid = inputs(NOW)
        generation = rr._make_test_generation(clock_now=lambda tz: NOW)
        packet = generation.compile_packet(snap, evid)
        bad = copy.deepcopy(packet)
        bad["packet_sha256"] = "0" * 64
        self.assertFalse(generation.verify_packet(bad, snap, evid))
        for key in packet["authority"]:
            with self.subTest(authority=key):
                bad = copy.deepcopy(packet)
                bad["authority"][key] = int(bad["authority"][key])
                bad.pop("packet_sha256")
                bad["packet_sha256"] = rr.sha256_json(bad)
                self.assertFalse(generation.verify_packet(bad, snap, evid))
        for key, value in (("repository_count", 2.0), ("private_repository_count", True),
                           ("public_repository_count", 1.0)):
            with self.subTest(count=key):
                bad = copy.deepcopy(packet)
                bad["estate"][key] = value
                bad.pop("packet_sha256")
                bad["packet_sha256"] = rr.sha256_json(bad)
                self.assertFalse(generation.verify_packet(bad, snap, evid))

    def test_snapshot_time_admission_boundaries(self):
        rr = self.rr
        generation = rr._make_test_generation(clock_now=lambda tz: NOW)
        for age in (-1, 0, 1, 604799, 604800, 604801):
            with self.subTest(age_seconds=age):
                snap, evid = inputs(NOW)
                snap["captured_at"] = stamp(NOW - timedelta(seconds=age))
                if 0 <= age <= 604800:
                    self.assertEqual(generation.compile_packet(snap, evid)["estate"]["repository_count"], 2)
                else:
                    with self.assertRaises(rr.EstateError):
                        generation.compile_packet(snap, evid)

    def test_each_evidence_time_boundary_retains_all_missing_currentness_reasons(self):
        rr = self.rr
        generation = rr._make_test_generation(
            clock_now=lambda tz: NOW, trusted_owner_refs=frozenset({"fixture:owner"}))
        expected = {"secret_scan": "SECRET_SCAN_NOT_CURRENT_CLEAR",
                    "open_work": "OPEN_WORK_SNAPSHOT_STALE",
                    "dependencies": "DEPENDENCY_SNAPSHOT_STALE"}
        for field, reason in expected.items():
            for age in (-1, 0, 1, 604799, 604800, 604801):
                with self.subTest(field=field, age_seconds=age):
                    snap, evid = inputs(NOW)
                    row = evidence_row(NOW)
                    row[field]["observed_at"] = stamp(NOW - timedelta(seconds=age))
                    evid["repositories"] = [row]
                    decision = generation.compile_packet(snap, evid)["decisions"][0]
                    if 0 <= age <= 604800:
                        self.assertEqual(decision["state"], "PUBLICATION_REVIEW")
                    else:
                        self.assertEqual(decision["state"], "HOLD")
                        self.assertIn(reason, decision["reasons"])

    def test_archive_work_and_consumer_matrix(self):
        rr = self.rr
        generation = rr._make_test_generation(
            clock_now=lambda tz: NOW, trusted_owner_refs=frozenset({"fixture:owner"}),
            trusted_archive_refs=frozenset({"fixture:archive"}))
        import itertools
        for counts in itertools.product((0, 1, 2), repeat=4):
            with self.subTest(counts=counts):
                snap, evid = inputs(NOW)
                row = evidence_row(NOW, intent="review_archive")
                for key, count in zip(("open_prs", "open_issues", "active_claims"), counts):
                    row["open_work"][key] = count
                row["dependencies"]["consumer_count"] = counts[3]
                evid["repositories"] = [row]
                packet = generation.compile_packet(snap, evid)
                decision = packet["decisions"][0]
                self.assertEqual(decision["state"], "HOLD" if any(counts) else "ARCHIVE_REVIEW")
                self.assertEqual("OPEN_WORK_BLOCKS_ARCHIVE" in decision["reasons"], any(counts[:3]))
                self.assertEqual("ACTIVE_CONSUMERS_BLOCK_ARCHIVE" in decision["reasons"], bool(counts[3]))
                for key, value in packet["authority"].items():
                    self.assertIs(value, key == "advisory_only")

    def test_source_bytes_are_unchanged_after_execution(self):
        for name, data in self.captured.items():
            self.assertEqual((self.root / name).read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
