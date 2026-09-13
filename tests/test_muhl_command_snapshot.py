import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

HOST = Path(__file__).resolve().parents[1] / "host"
if str(HOST) not in sys.path:
    sys.path.insert(0, str(HOST))

import muhl_command_snapshot as snap


SURFACE = b"""id=driveprobe1
kind=surface
approved=YES
claimed_from=GROK
authenticated_player=UNKNOWN
"""

SAY = b"""id=say12345
kind=say
approved=YES
from=GROK
to=KITE
claimed_from=GROK
authenticated_player=UNKNOWN
owner_ok=
---
hello there
"""

DUMP = b"""id=dump12345
kind=dump
approved=YES
claimed_from=GROK
authenticated_player=UNKNOWN
path=C:\\Users\\lucys\\Desktop\\MUHL_COMMONS\\commons.mno
"""


def gh_item(name: str, data: bytes) -> tuple[dict, dict]:
    sha = snap.git_blob_sha(data)
    item = {
        "name": name,
        "path": f"COMMANDS/{name}",
        "type": "file",
        "sha": sha,
        "size": len(data),
    }
    obj = {
        "name": name,
        "path": f"COMMANDS/{name}",
        "type": "file",
        "sha": sha,
        "size": len(data),
        "encoding": "base64",
        "content": base64.b64encode(data).decode("ascii"),
    }
    return item, obj


class SnapshotTests(unittest.TestCase):
    def test_surface_and_say_parse(self):
        surface = snap.parse_command_bytes(
            SURFACE, name="driveprobe1.txt", source="test:surface"
        )[0]
        self.assertEqual(surface["kind"], "surface")

        say = snap.parse_command_bytes(
            SAY, name="say12345.txt", source="test:say"
        )[0]
        self.assertEqual(say["body"], "hello there")

    def test_dump_requires_path_but_is_supported(self):
        command = snap.parse_command_bytes(
            DUMP, name="dump12345.txt", source="test:dump"
        )[0]
        self.assertEqual(command["kind"], "dump")

    def test_rejects_duplicate_malformed_and_crlf_text(self):
        cases = [
            (SURFACE + b"approved=YES\n", "duplicate key"),
            (SURFACE.replace(b"kind=surface\n", b"not-a-header\n"), "expected key=value"),
            (SURFACE.replace(b"\n", b"\r\n", 1), "forbidden control"),
        ]
        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(snap.SnapshotError, message):
                    snap.parse_command_bytes(
                        payload, name="driveprobe1.txt", source="hostile"
                    )

    def test_rejects_bom_invalid_utf8_and_controls(self):
        cases = [
            (b"\xef\xbb\xbf" + SURFACE, "BOM"),
            (SURFACE + b"\xff", "strict UTF-8"),
            (SURFACE.replace(b"GROK", b"GROK\x00"), "forbidden control"),
        ]
        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(snap.SnapshotError, message):
                    snap.parse_command_bytes(
                        payload, name="driveprobe1.txt", source="hostile"
                    )

    def test_requires_exact_authority_fields(self):
        cases = [
            (SURFACE.replace(b"approved=YES", b"approved=yes"), "approved"),
            (
                SURFACE.replace(
                    b"authenticated_player=UNKNOWN",
                    b"authenticated_player=GROK",
                ),
                "authenticated_player",
            ),
            (
                SURFACE.replace(b"claimed_from=GROK", b"claimed_from="),
                "claimed_from",
            ),
        ]
        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(snap.SnapshotError, message):
                    snap.parse_command_bytes(
                        payload, name="driveprobe1.txt", source="hostile"
                    )

    def test_kite_to_grok_requires_owner_ok(self):
        hostile = SAY.replace(b"from=GROK\nto=KITE", b"from=KITE\nto=GROK")
        with self.assertRaisesRegex(snap.SnapshotError, "owner_ok=BRYCE"):
            snap.parse_command_bytes(
                hostile, name="say12345.txt", source="hostile"
            )
        ratified = hostile.replace(b"owner_ok=", b"owner_ok=BRYCE")
        snap.parse_command_bytes(
            ratified, name="say12345.txt", source="ratified"
        )

    def test_json_duplicate_keys_nonfinite_and_controls_fail_closed(self):
        payloads = [
            b'{"id":"json1234","id":"other123","kind":"surface","approved":"YES","claimed_from":"GROK","authenticated_player":"UNKNOWN"}',
            b'{"id":"json1234","kind":"surface","approved":"YES","claimed_from":"GROK","authenticated_player":"UNKNOWN","n":NaN}',
            b'{"id":"json1234","kind":"surface","approved":"YES","claimed_from":"GROK","authenticated_player":"UNKNOWN","note":"a\\tb"}',
        ]
        messages = ["duplicate JSON key", "non-finite", "forbidden control"]
        for payload, message in zip(payloads, messages):
            with self.subTest(message=message):
                with self.assertRaisesRegex(snap.SnapshotError, message):
                    snap.parse_command_bytes(
                        payload, name="json1234.json", source="hostile-json"
                    )

    def test_stable_file_accepts_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "driveprobe1.txt"
            path.write_bytes(SURFACE)
            self.assertEqual(snap.read_stable_file(path), SURFACE)

    def test_stable_file_rejects_oversize_and_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            big = root / "big.txt"
            big.write_bytes(b"x" * (snap.MAX_COMMAND_BYTES + 1))
            with self.assertRaisesRegex(snap.SnapshotError, "exceeds"):
                snap.read_stable_file(big)

            directory = root / "dir.txt"
            directory.mkdir()
            with self.assertRaisesRegex(snap.SnapshotError, "regular file"):
                snap.read_stable_file(directory)

    def test_stable_file_detects_changed_second_read(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "driveprobe1.txt"
            path.write_bytes(SURFACE)
            real_read = snap._read_fd_bounded
            calls = 0

            def changed(fd):
                nonlocal calls
                calls += 1
                data = real_read(fd)
                if calls == 2:
                    return data.replace(b"GROK", b"KITE")
                return data

            with mock.patch.object(snap, "_read_fd_bounded", side_effect=changed):
                with self.assertRaisesRegex(snap.SnapshotError, "changed while being frozen"):
                    snap.read_stable_file(path)

    def test_stable_file_detects_path_replacement_before_open(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "driveprobe1.txt"
            replacement = root / "replacement"
            path.write_bytes(SURFACE)
            replacement.write_bytes(SURFACE.replace(b"GROK", b"KITE"))
            real_open = os.open
            swapped = False

            def replacing_open(open_path, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(open_path) == path:
                    os.replace(replacement, path)
                    swapped = True
                return real_open(open_path, flags, *args, **kwargs)

            with mock.patch.object(snap.os, "open", side_effect=replacing_open):
                with self.assertRaisesRegex(snap.SnapshotError, "changed before open"):
                    snap.read_stable_file(path)

    def test_local_snapshot_name_set_excludes_late_arrival(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = root / "driveprobe1.txt"
            late = root / "say12345.txt"
            first.write_bytes(SURFACE)
            real_listdir = os.listdir

            def listing(path):
                names = real_listdir(path)
                late.write_bytes(SAY)
                return names

            with mock.patch.object(snap.os, "listdir", side_effect=listing):
                commands = snap.load_local_commands(root)
            self.assertEqual(set(commands), {"driveprobe1"})

    def test_local_snapshot_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "same1234.jsonl"
            a.write_bytes(
                b'{"id":"same1234","kind":"surface","approved":"YES","claimed_from":"GROK","authenticated_player":"UNKNOWN"}\n'
                b'{"id":"same1234","kind":"surface","approved":"YES","claimed_from":"GROK","authenticated_player":"UNKNOWN"}\n'
            )
            with self.assertRaisesRegex(snap.SnapshotError, "duplicate command id"):
                snap.load_local_commands(root)

    def test_remote_snapshot_pins_one_commit_and_ignores_late_main(self):
        sha_a = "a" * 40
        item, obj = gh_item("driveprobe1.txt", SURFACE)
        calls = []
        main_reads = 0

        def fetch(endpoint):
            nonlocal main_reads
            calls.append(endpoint)
            if endpoint == "commits/main":
                main_reads += 1
                return {"sha": sha_a if main_reads == 1 else "b" * 40}
            if endpoint == f"contents/COMMANDS?ref={sha_a}":
                return [item]
            if endpoint == f"contents/COMMANDS/driveprobe1.txt?ref={sha_a}":
                return obj
            raise AssertionError(endpoint)

        commands, commit = snap.load_github_commands(fetch)
        self.assertEqual(commit, sha_a)
        self.assertEqual(set(commands), {"driveprobe1"})
        self.assertEqual(main_reads, 1)
        self.assertTrue(
            commands["driveprobe1"]["_source"].startswith(
                f"github:COMMANDS/driveprobe1.txt@{sha_a}:"
            )
        )
        self.assertEqual(
            calls,
            [
                "commits/main",
                f"contents/COMMANDS?ref={sha_a}",
                f"contents/COMMANDS/driveprobe1.txt?ref={sha_a}",
            ],
        )

    def test_remote_snapshot_rejects_listing_content_blob_mismatch(self):
        sha_a = "a" * 40
        item, obj = gh_item("driveprobe1.txt", SURFACE)
        obj = dict(obj)
        obj["sha"] = "c" * 40

        def fetch(endpoint):
            if endpoint == "commits/main":
                return {"sha": sha_a}
            if endpoint == f"contents/COMMANDS?ref={sha_a}":
                return [item]
            if endpoint == f"contents/COMMANDS/driveprobe1.txt?ref={sha_a}":
                return obj
            raise AssertionError(endpoint)

        with self.assertRaisesRegex(snap.SnapshotError, "listing/content blob SHA mismatch"):
            snap.load_github_commands(fetch)

    def test_remote_snapshot_rejects_bytes_that_do_not_match_git_blob(self):
        sha_a = "a" * 40
        item, obj = gh_item("driveprobe1.txt", SURFACE)
        fake_sha = "d" * 40
        item = dict(item, sha=fake_sha)
        obj = dict(obj, sha=fake_sha)

        def fetch(endpoint):
            if endpoint == "commits/main":
                return {"sha": sha_a}
            if endpoint == f"contents/COMMANDS?ref={sha_a}":
                return [item]
            if endpoint == f"contents/COMMANDS/driveprobe1.txt?ref={sha_a}":
                return obj
            raise AssertionError(endpoint)

        with self.assertRaisesRegex(snap.SnapshotError, "bytes do not match Git blob SHA"):
            snap.load_github_commands(fetch)

    def test_remote_snapshot_fails_whole_snapshot_on_bad_candidate(self):
        sha_a = "a" * 40
        good_item, good_obj = gh_item("driveprobe1.txt", SURFACE)
        bad_data = SURFACE.replace(b"\n", b"\r\n", 1)
        bad_item, bad_obj = gh_item("bad12345.txt", bad_data)

        def fetch(endpoint):
            if endpoint == "commits/main":
                return {"sha": sha_a}
            if endpoint == f"contents/COMMANDS?ref={sha_a}":
                return [good_item, bad_item]
            if endpoint == f"contents/COMMANDS/driveprobe1.txt?ref={sha_a}":
                return good_obj
            if endpoint == f"contents/COMMANDS/bad12345.txt?ref={sha_a}":
                return bad_obj
            raise AssertionError(endpoint)

        with self.assertRaises(snap.SnapshotError):
            snap.load_github_commands(fetch)

    def test_github_blob_sha_matches_known_fixture(self):
        self.assertEqual(
            snap.git_blob_sha(b"test\n"),
            "9daeafb9864cf43055ae93beb0afd6c7d144bfa4",
        )


if __name__ == "__main__":
    unittest.main()
