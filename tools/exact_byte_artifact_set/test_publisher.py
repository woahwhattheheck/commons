from __future__ import annotations

import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.exact_byte_artifact_set.publisher import (
    PartialPublicationError,
    PublicationError,
    publish_artifact_set,
)


class PublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="exact-byte-set-"))
        self.out = self.tmp / "out"
        self.out.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_multi_file_success_receipt_and_modes(self) -> None:
        artifacts = {"b.json": b"{\"b\":2}\n", "a.txt": b"alpha\n"}
        receipt = publish_artifact_set(self.out, artifacts)
        self.assertTrue(receipt["publication_complete"])
        self.assertEqual([r["name"] for r in receipt["artifacts"]], ["a.txt", "b.json"])
        self.assertEqual((self.out / "a.txt").read_bytes(), b"alpha\n")
        self.assertEqual((self.out / "b.json").read_bytes(), b"{\"b\":2}\n")
        self.assertEqual(stat.S_IMODE((self.out / "a.txt").stat().st_mode), 0o600)

    def test_receipt_order_invariant(self) -> None:
        first = self.tmp / "first"
        second = self.tmp / "second"
        first.mkdir()
        second.mkdir()
        a = publish_artifact_set(first, {"x": b"1", "y": b"2"})
        b = publish_artifact_set(second, {"y": b"2", "x": b"1"})
        self.assertEqual(a, b)

    def test_existing_leaf_fails_before_any_publication(self) -> None:
        (self.out / "occupied").write_bytes(b"sentinel")
        with self.assertRaises(PublicationError):
            publish_artifact_set(self.out, {"new": b"n", "occupied": b"x"})
        self.assertFalse((self.out / "new").exists())
        self.assertEqual((self.out / "occupied").read_bytes(), b"sentinel")

    def test_existing_symlink_leaf_fails_before_publication(self) -> None:
        target = self.tmp / "target"
        target.write_bytes(b"sentinel")
        (self.out / "link").symlink_to(target)
        with self.assertRaises(PublicationError):
            publish_artifact_set(self.out, {"link": b"x", "new": b"n"})
        self.assertEqual(target.read_bytes(), b"sentinel")
        self.assertFalse((self.out / "new").exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO requires POSIX")
    def test_existing_nonregular_leaf_fails_before_publication(self) -> None:
        os.mkfifo(self.out / "pipe")
        with self.assertRaises(PublicationError):
            publish_artifact_set(self.out, {"pipe": b"x"})

    def test_unsafe_leaf_names_rejected(self) -> None:
        for bad in ("../x", "a/b", ".", "..", "", "\\evil"):
            with self.subTest(bad=bad), self.assertRaises(PublicationError):
                publish_artifact_set(self.out, {bad: b"x"})

    def test_symlink_ancestor_rejected(self) -> None:
        real = self.tmp / "real"
        real.mkdir()
        link = self.tmp / "link"
        link.symlink_to(real, target_is_directory=True)
        with self.assertRaises((PublicationError, OSError)):
            publish_artifact_set(link, {"x": b"x"})
        self.assertFalse((real / "x").exists())

    def test_short_write_is_drained(self) -> None:
        original = os.write

        def short(fd, data):
            if len(data) > 1:
                return original(fd, data[: max(1, len(data) // 2)])
            return original(fd, data)

        with mock.patch("tools.exact_byte_artifact_set.publisher.os.write", side_effect=short):
            publish_artifact_set(self.out, {"x": b"abcdefghijk"})
        self.assertEqual((self.out / "x").read_bytes(), b"abcdefghijk")

    def test_partial_write_failure_preserves_created_leaf(self) -> None:
        original = os.write
        calls = 0

        def fail_after_fragment(fd, data):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original(fd, data[:1])
            raise OSError("injected write failure")

        with mock.patch("tools.exact_byte_artifact_set.publisher.os.write", side_effect=fail_after_fragment):
            with self.assertRaises(PartialPublicationError) as caught:
                publish_artifact_set(self.out, {"x": b"abcdef"})
        self.assertEqual(caught.exception.created_leaves, ("x",))
        self.assertTrue((self.out / "x").exists())
        self.assertEqual((self.out / "x").read_bytes(), b"a")

    def test_first_leaf_path_replacement_during_later_write_fails_closed(self) -> None:
        import tools.exact_byte_artifact_set.publisher as publisher

        original = publisher._write_all
        calls = 0

        def replace_first(fd, payload):
            nonlocal calls
            calls += 1
            original(fd, payload)
            if calls == 2:
                first = self.out / "a"
                first.unlink()
                first.write_bytes(b"foreign")

        with mock.patch.object(publisher, "_write_all", side_effect=replace_first):
            with self.assertRaises(PartialPublicationError) as caught:
                publish_artifact_set(self.out, {"a": b"owned-a", "b": b"owned-b"})
        self.assertEqual(caught.exception.created_leaves, ("a", "b"))
        self.assertEqual((self.out / "a").read_bytes(), b"foreign")
        self.assertEqual((self.out / "b").read_bytes(), b"owned-b")

    def test_same_inode_same_length_mutation_before_readback_fails_closed(self) -> None:
        import tools.exact_byte_artifact_set.publisher as publisher

        original = publisher._fsync_directory
        mutated = False

        def mutate(dir_fd):
            nonlocal mutated
            original(dir_fd)
            if not mutated:
                mutated = True
                path = self.out / "a"
                st = path.stat()
                with path.open("r+b", buffering=0) as handle:
                    handle.write(b"MUTATED!")  # same length as ORIGINAL
                    handle.flush()
                    os.fsync(handle.fileno())
                os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))

        with mock.patch.object(publisher, "_fsync_directory", side_effect=mutate):
            with self.assertRaises(PartialPublicationError):
                publish_artifact_set(self.out, {"a": b"ORIGINAL"})
        self.assertEqual((self.out / "a").read_bytes(), b"MUTATED!")

    def test_mutation_after_first_byte_pass_is_caught_by_second_fence(self) -> None:
        import tools.exact_byte_artifact_set.publisher as publisher

        original = publisher._assert_visible_identity
        calls = 0

        def mutate_after_first_visibility(dir_fd, name, expected, expected_size):
            nonlocal calls
            calls += 1
            original(dir_fd, name, expected, expected_size)
            if calls == 1:
                path = self.out / name
                with path.open("r+b", buffering=0) as handle:
                    handle.write(b"CHANGED!")
                    handle.flush()
                    os.fsync(handle.fileno())

        with mock.patch.object(publisher, "_assert_visible_identity", side_effect=mutate_after_first_visibility):
            with self.assertRaises(PartialPublicationError):
                publish_artifact_set(self.out, {"a": b"ORIGINAL"})
        self.assertEqual((self.out / "a").read_bytes(), b"CHANGED!")

    def test_parent_directory_path_replacement_never_redirects_writes(self) -> None:
        import tools.exact_byte_artifact_set.publisher as publisher

        moved = self.tmp / "retained"
        replacement = self.out
        original = publisher._write_all
        swapped = False

        def swap_parent(fd, payload):
            nonlocal swapped
            if not swapped:
                swapped = True
                self.out.rename(moved)
                replacement.mkdir()
            original(fd, payload)

        with mock.patch.object(publisher, "_write_all", side_effect=swap_parent):
            receipt = publish_artifact_set(self.out, {"a": b"owned-a", "b": b"owned-b"})
        self.assertTrue(receipt["publication_complete"])
        self.assertFalse((replacement / "a").exists())
        self.assertFalse((replacement / "b").exists())
        self.assertEqual((moved / "a").read_bytes(), b"owned-a")
        self.assertEqual((moved / "b").read_bytes(), b"owned-b")

    def test_mutation_during_final_directory_fsync_fails_closed(self) -> None:
        import tools.exact_byte_artifact_set.publisher as publisher

        original = publisher._fsync_directory
        calls = 0

        def mutate_on_second_fsync(dir_fd):
            nonlocal calls
            calls += 1
            original(dir_fd)
            if calls == 2:
                path = self.out / "a"
                st = path.stat()
                with path.open("r+b", buffering=0) as handle:
                    handle.write(b"MUTATED!")  # same length as ORIGINAL
                    handle.flush()
                    os.fsync(handle.fileno())
                os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))

        with mock.patch.object(publisher, "_fsync_directory", side_effect=mutate_on_second_fsync):
            with self.assertRaises(PartialPublicationError) as caught:
                publish_artifact_set(self.out, {"a": b"ORIGINAL"})
        self.assertEqual(caught.exception.created_leaves, ("a",))
        self.assertEqual((self.out / "a").read_bytes(), b"MUTATED!")

    def test_late_fsync_failure_preserves_all_created_evidence(self) -> None:
        import tools.exact_byte_artifact_set.publisher as publisher

        original = publisher._fsync_directory
        calls = 0

        def fail_second(dir_fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("late fsync failure")
            return original(dir_fd)

        with mock.patch.object(publisher, "_fsync_directory", side_effect=fail_second):
            with self.assertRaises(PartialPublicationError) as caught:
                publish_artifact_set(self.out, {"a": b"1", "b": b"2"})
        self.assertEqual(caught.exception.created_leaves, ("a", "b"))
        self.assertEqual((self.out / "a").read_bytes(), b"1")
        self.assertEqual((self.out / "b").read_bytes(), b"2")

    def test_type_and_size_guards(self) -> None:
        with self.assertRaises(PublicationError):
            publish_artifact_set(self.out, {"x": bytearray(b"x")})  # type: ignore[arg-type]
        with self.assertRaises(PublicationError):
            publish_artifact_set(self.out, {})


if __name__ == "__main__":
    unittest.main()
