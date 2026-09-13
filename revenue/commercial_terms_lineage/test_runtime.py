from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import inspect
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import runtime
from lineage import TermsLineageError, canonical_bytes
from test_lineage import NOW, authority_one, review_for


class RuntimeBoundaryTests(unittest.TestCase):
    def test_public_current_apis_have_no_time_override(self):
        self.assertNotIn("as_of", inspect.signature(runtime.compile_current).parameters)
        self.assertNotIn("trusted_now", inspect.signature(runtime.verify_current).parameters)

    def test_compile_current_uses_private_process_clock(self):
        auth = authority_one()
        review = review_for(auth)
        fixed = datetime(2026, 9, 13, 13, 45, 0, tzinfo=timezone.utc)
        with mock.patch("runtime._utc_now", return_value=fixed):
            receipt = runtime.compile_current(auth, review)
        self.assertEqual(receipt["compiled_at"], "2026-09-13T13:45:00Z")

    def test_verify_current_rejects_future_receipt_without_caller_clock_escape(self):
        auth = authority_one()
        review = review_for(auth)
        future = datetime(2026, 9, 14, 0, 0, 0, tzinfo=timezone.utc)
        with mock.patch("runtime._utc_now", return_value=future):
            receipt = runtime.compile_current(auth, review)
        with mock.patch("runtime._utc_now", return_value=NOW):
            with self.assertRaisesRegex(TermsLineageError, "future"):
                runtime.verify_current(auth, review, receipt)

    def test_regular_file_swap_between_lstat_and_open_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "authority.json"
            replacement = root / "replacement.json"
            target.write_bytes(canonical_bytes(authority_one()))
            forged = deepcopy(authority_one())
            forged["authority_id"] = "forged-authority"
            replacement.write_bytes(canonical_bytes(forged))
            real_open = os.open
            swapped = False

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                nonlocal swapped
                if not swapped and Path(path) == target:
                    replacement.replace(target)
                    swapped = True
                if dir_fd is None:
                    return real_open(path, flags, mode)
                return real_open(path, flags, mode, dir_fd=dir_fd)

            with mock.patch("runtime.os.open", side_effect=racing_open):
                with self.assertRaisesRegex(TermsLineageError, "path generation changed"):
                    runtime.read_json_file(target)

    def test_in_read_generation_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "authority.json"
            target.write_bytes(canonical_bytes(authority_one()))
            real_read = os.read
            mutated = False

            def racing_read(fd, count):
                nonlocal mutated
                chunk = real_read(fd, count)
                if chunk and not mutated:
                    mutated = True
                    with target.open("ab") as handle:
                        handle.write(b" ")
                return chunk

            with mock.patch("runtime.os.read", side_effect=racing_read):
                with self.assertRaisesRegex(TermsLineageError, "changed while being read"):
                    runtime.read_json_file(target)

    def test_write_exclusive_handles_short_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.txt"
            real_write = os.write

            def short_write(fd, data):
                return real_write(fd, data[:3] if len(data) > 3 else data)

            with mock.patch("runtime.os.write", side_effect=short_write):
                runtime.write_exclusive(out, "abcdefghijk")
            self.assertEqual(out.read_text(encoding="utf-8"), "abcdefghijk")

    def test_write_exclusive_refuses_existing_and_symlink_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "existing.txt"
            existing.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(TermsLineageError, "overwrite"):
                runtime.write_exclusive(existing, "new")
            link = root / "link.txt"
            try:
                link.symlink_to(existing)
            except (OSError, NotImplementedError):
                return
            with self.assertRaises(TermsLineageError):
                runtime.write_exclusive(link, "new")
            self.assertEqual(existing.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
