import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from . import security_questionnaire_desk as sq
    from . import _secure_publish as secure_publish
    from . import test_security_questionnaire_desk_legacy as legacy
    from ._test_questionnaire_common import fixture
except ImportError:
    import security_questionnaire_desk as sq
    import _secure_publish as secure_publish
    import test_security_questionnaire_desk_legacy as legacy
    from _test_questionnaire_common import fixture


@unittest.skipIf(os.name == "nt", "descriptor-relative POSIX tests")
class PublicationTests(unittest.TestCase):
    def test_symlinked_output_ancestor_is_refused(self):
        packet = sq.compile_packet(fixture(), legacy.NOW)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(sq.DeskError, "open output directory safely"):
                sq.publish_artifacts(packet, alias / "out")
            self.assertEqual(list(real.iterdir()), [])

    def test_parent_replacement_cannot_redirect_artifacts(self):
        packet = sq.compile_packet(fixture(), legacy.NOW)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            retained = root / "retained"
            foreign = root / "foreign"
            foreign.mkdir()
            real_open = secure_publish.os.open
            fired = False

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                nonlocal fired
                if (
                    not fired and dir_fd is not None and path == "packet.json"
                    and flags & os.O_CREAT
                ):
                    output.rename(retained)
                    output.symlink_to(foreign, target_is_directory=True)
                    fired = True
                return real_open(path, flags, mode, dir_fd=dir_fd)

            with mock.patch.object(secure_publish.os, "open", side_effect=racing_open):
                sq.publish_artifacts(packet, output)

            self.assertTrue(fired)
            self.assertTrue((retained / "packet.json").is_file())
            self.assertEqual(list(foreign.iterdir()), [])

    def test_replacement_between_outputs_stays_on_retained_generation(self):
        packet = sq.compile_packet(fixture(), legacy.NOW)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            retained = root / "retained"
            foreign = root / "foreign"
            foreign.mkdir()
            real_open = secure_publish.os.open
            fired = False

            def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                nonlocal fired
                if (
                    not fired and dir_fd is not None and path == "answers.csv"
                    and flags & os.O_CREAT
                ):
                    output.rename(retained)
                    output.symlink_to(foreign, target_is_directory=True)
                    fired = True
                return real_open(path, flags, mode, dir_fd=dir_fd)

            with mock.patch.object(secure_publish.os, "open", side_effect=racing_open):
                sq.publish_artifacts(packet, output)

            self.assertTrue(fired)
            self.assertEqual(
                sorted(path.name for path in retained.iterdir()),
                ["answers.csv", "packet.json", "public-safe.json", "receipt.sha256", "review.md"],
            )
            self.assertEqual(list(foreign.iterdir()), [])
