import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_collection as gc


class DestinationGuard(unittest.TestCase):
    """--out is caller-supplied and was passed straight to shutil.rmtree."""

    def test_refuses_a_directory_this_tool_did_not_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            victim = Path(tmp) / "someone_elses_work"
            victim.mkdir()
            (victim / "important.txt").write_text("do not delete me")
            with self.assertRaises(gc.UnsafeDestination):
                gc.generate(victim, gc.PROFILES["small"])
            self.assertTrue((victim / "important.txt").is_file(),
                            "foreign file was destroyed")
            self.assertEqual((victim / "important.txt").read_text(),
                             "do not delete me")

    def test_allows_a_nonexistent_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fresh"
            gc.generate(out, gc.PROFILES["small"])
            self.assertTrue((out / "manifest.json").is_file())
            self.assertTrue((out / gc._MARKER).is_file(), "marker not written")

    def test_allows_an_empty_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "empty"
            out.mkdir()
            gc.generate(out, gc.PROFILES["small"])
            self.assertTrue((out / "manifest.json").is_file())

    def test_regeneration_into_our_own_output_still_works(self):
        # The guard must not break the legitimate workflow it protects.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "mine"
            gc.generate(out, gc.PROFILES["small"])
            gc.generate(out, gc.PROFILES["small"])
            self.assertTrue((out / "manifest.json").is_file())

    def test_refuses_a_file_as_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "afile"
            f.write_text("x")
            with self.assertRaises(gc.UnsafeDestination):
                gc.generate(f, gc.PROFILES["small"])
            self.assertTrue(f.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
