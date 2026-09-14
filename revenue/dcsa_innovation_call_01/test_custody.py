from .test_support import *  # noqa: F401,F403

class FileCustodyTests(unittest.TestCase):
    def test_read_rejects_final_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            real = root / "real.json"
            link = root / "link.json"
            real.write_text("{}")
            link.symlink_to(real)
            with self.assertRaises(strict.CustodyError):
                strict.read_bounded_regular_file(link)

    def test_read_rejects_symlinked_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            real_dir = root / "real"
            real_dir.mkdir()
            (real_dir / "input.json").write_text("{}")
            (root / "alias").symlink_to(real_dir, target_is_directory=True)
            with self.assertRaises(strict.CustodyError):
                strict.read_bounded_regular_file(root / "alias" / "input.json")

    def test_read_detects_ctime_change_with_restored_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "input.bin"
            original = b"a" * (128 * 1024)
            path.write_bytes(original)
            before = path.stat()
            real_read = os.read
            mutated = False

            def racing_read(fd: int, n: int) -> bytes:
                nonlocal mutated
                chunk = real_read(fd, n)
                if chunk and not mutated:
                    mutated = True
                    path.write_bytes(b"b" * len(original))
                    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
                return chunk

            with mock.patch("revenue.dcsa_innovation_call_01.strict.os.read", side_effect=racing_read):
                with self.assertRaises(strict.CustodyError):
                    strict.read_bounded_regular_file(path)

    def test_write_is_create_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "out.json"
            strict.write_exclusive_regular_file(path, b"one")
            with self.assertRaises(strict.CustodyError):
                strict.write_exclusive_regular_file(path, b"two")
            self.assertEqual(path.read_bytes(), b"one")

    def test_write_rejects_symlinked_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            real_dir = root / "real"
            real_dir.mkdir()
            (root / "alias").symlink_to(real_dir, target_is_directory=True)
            with self.assertRaises(strict.CustodyError):
                strict.write_exclusive_regular_file(root / "alias" / "out", b"x")

