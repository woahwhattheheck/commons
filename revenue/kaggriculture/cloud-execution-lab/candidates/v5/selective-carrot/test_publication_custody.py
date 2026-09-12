# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import publication_custody as pc


class PublicationCustodyTests(unittest.TestCase):
    def test_success_publishes_exact_pair(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a, b = root/'candidate.tar.gz', root/'candidate.json'
            pc.publish_exclusive([(a, b'archive'), (b, b'{"ok":true}\n')])
            self.assertEqual(a.read_bytes(), b'archive')
            self.assertEqual(b.read_bytes(), b'{"ok":true}\n')

    def test_alias_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root/'candidate'
            with self.assertRaises(ValueError):
                pc.publish_exclusive([(a, b'a'), (root/'.'/'candidate', b'b')])
            self.assertFalse(a.exists())

    def test_preexisting_second_path_rolls_back_first_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a, b = root/'candidate.tar.gz', root/'candidate.json'
            b.write_bytes(b'sentinel')
            with self.assertRaises(FileExistsError):
                pc.publish_exclusive([(a, b'archive'), (b, b'receipt')])
            self.assertFalse(a.exists())
            self.assertEqual(b.read_bytes(), b'sentinel')

    def test_second_write_failure_rolls_back_both(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a, b = root/'candidate.tar.gz', root/'candidate.json'
            original = pc._write_all
            calls = 0

            def fail_second(fd, payload):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError('injected second write failure')
                return original(fd, payload)

            with mock.patch.object(pc, '_write_all', side_effect=fail_second):
                with self.assertRaisesRegex(OSError, 'injected'):
                    pc.publish_exclusive([(a, b'archive'), (b, b'receipt')])
            self.assertFalse(a.exists())
            self.assertFalse(b.exists())

    def test_foreign_replacement_is_detected_and_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a, b = root/'candidate.tar.gz', root/'candidate.json'
            original = pc._verify_final
            calls = 0

            def replace_before_verify(item):
                nonlocal calls
                calls += 1
                if calls == 1:
                    item.path.unlink()
                    item.path.write_bytes(b'foreign')
                return original(item)

            with mock.patch.object(pc, '_verify_final', side_effect=replace_before_verify):
                with self.assertRaisesRegex(OSError, 'identity changed'):
                    pc.publish_exclusive([(a, b'archive'), (b, b'receipt')])
            self.assertEqual(a.read_bytes(), b'foreign')
            self.assertFalse(b.exists())

    def test_single_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            a = Path(td)/'one'
            with self.assertRaises(ValueError):
                pc.publish_exclusive([(a, b'x')])
            self.assertFalse(a.exists())


if __name__ == '__main__':
    unittest.main()
