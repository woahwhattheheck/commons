import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

HOST = Path(__file__).resolve().parents[1] / "host"
if str(HOST) not in sys.path:
    sys.path.insert(0, str(HOST))

import muhl_command_snapshot as snapshot
import muhl_github_drive as drive


class DriveWrapperTests(unittest.TestCase):
    def test_pinned_legacy_source_blob_matches_wrapper_constant(self):
        source = snapshot.read_stable_file(drive.LEGACY_SOURCE)
        self.assertEqual(snapshot.git_blob_sha(source), drive.LEGACY_GIT_BLOB)

    def test_host_and_infra_mirrors_are_byte_exact(self):
        repo = Path(__file__).resolve().parents[1]
        pairs = [
            (repo / "host" / "muhl_github_drive.py", repo / "infra" / "host" / "muhl_github_drive.py"),
            (repo / "host" / "muhl_command_snapshot.py", repo / "infra" / "host" / "muhl_command_snapshot.py"),
            (repo / "host" / "_muhl_github_drive_legacy_source.txt", repo / "infra" / "host" / "_muhl_github_drive_legacy_source.txt"),
        ]
        for left, right in pairs:
            with self.subTest(path=left.name):
                self.assertEqual(left.read_bytes(), right.read_bytes())

    def test_installs_snapshot_loaders_before_legacy_dispatch(self):
        namespace = {"CMD_ROOT": "X"}
        events = []

        def legacy_main():
            events.append(("local", namespace["load_local_commands"]()))
            events.append(("remote", namespace["load_github_commands"]("TOKEN")))
            events.append(("dispatch", True))
            return 0

        namespace["main"] = legacy_main

        with mock.patch.object(drive, "_load_legacy_namespace", return_value=namespace), \
             mock.patch.object(snapshot, "load_local_commands", return_value={"L": {}}) as local, \
             mock.patch.object(
                 snapshot,
                 "load_github_commands",
                 return_value=({"R": {}}, "a" * 40),
             ) as remote, \
             mock.patch.object(drive, "_github_json", return_value={}):
            self.assertEqual(drive.main(), 0)

        local.assert_called_once_with("X")
        remote.assert_called_once()
        self.assertEqual(events[-1], ("dispatch", True))

    def test_snapshot_failure_holds_before_dispatch(self):
        namespace = {"CMD_ROOT": "X"}
        dispatched = False

        def legacy_main():
            nonlocal dispatched
            namespace["load_local_commands"]()
            namespace["load_github_commands"]()
            dispatched = True
            return 0

        namespace["main"] = legacy_main
        stderr = io.StringIO()
        stdout = io.StringIO()
        with mock.patch.object(drive, "_load_legacy_namespace", return_value=namespace), \
             mock.patch.object(
                 snapshot,
                 "load_local_commands",
                 side_effect=snapshot.SnapshotError("changed generation"),
             ), \
             contextlib.redirect_stdout(stdout), \
             contextlib.redirect_stderr(stderr):
            self.assertEqual(drive.main(), 2)

        self.assertFalse(dispatched)
        self.assertIn("REFUSE command snapshot", stdout.getvalue())

    def test_remote_snapshot_failure_holds_before_dispatch(self):
        namespace = {"CMD_ROOT": "X"}
        dispatched = False

        def legacy_main():
            nonlocal dispatched
            namespace["load_local_commands"]()
            namespace["load_github_commands"]()
            dispatched = True
            return 0

        namespace["main"] = legacy_main
        with mock.patch.object(drive, "_load_legacy_namespace", return_value=namespace), \
             mock.patch.object(snapshot, "load_local_commands", return_value={}), \
             mock.patch.object(
                 snapshot,
                 "load_github_commands",
                 side_effect=snapshot.SnapshotError("moving remote"),
             ):
            self.assertEqual(drive.main(), 2)

        self.assertFalse(dispatched)

    def test_malformed_optional_legacy_field_holds_before_any_dispatch(self):
        for field, bad_value in (("purpose", {}), ("owner_ok", True)):
            with self.subTest(field=field):
                namespace = {"CMD_ROOT": "X"}
                dispatched = []

                def legacy_main():
                    local = namespace["load_local_commands"]()
                    remote = namespace["load_github_commands"]()
                    commands = dict(local)
                    commands.update(remote)
                    for command_id in sorted(commands):
                        dispatched.append(command_id)
                    return 0

                namespace["main"] = legacy_main
                commands = {
                    "a-valid": {"id": "a-valid"},
                    "z-bad": {"id": "z-bad", field: bad_value},
                }
                with mock.patch.object(
                    drive, "_load_legacy_namespace", return_value=namespace
                ), mock.patch.object(
                    snapshot, "load_local_commands", return_value=commands
                ), mock.patch.object(
                    snapshot,
                    "load_github_commands",
                    return_value=({}, "a" * 40),
                ):
                    self.assertEqual(drive.main(), 2)

                self.assertEqual(dispatched, [])

    def test_local_remote_id_collision_holds_before_any_dispatch(self):
        namespace = {"CMD_ROOT": "X"}
        dispatched = []

        def legacy_main():
            local = namespace["load_local_commands"]()
            remote = namespace["load_github_commands"]()
            commands = dict(local)
            commands.update(remote)
            dispatched.extend(sorted(commands))
            return 0

        namespace["main"] = legacy_main
        with mock.patch.object(drive, "_load_legacy_namespace", return_value=namespace), \
             mock.patch.object(
                 snapshot,
                 "load_local_commands",
                 return_value={"same-id": {"id": "same-id"}},
             ), \
             mock.patch.object(
                 snapshot,
                 "load_github_commands",
                 return_value=({"same-id": {"id": "same-id"}}, "a" * 40),
             ):
            self.assertEqual(drive.main(), 2)

        self.assertEqual(dispatched, [])

    def test_schema_closure_rejects_mapping_key_id_mismatch(self):
        with self.assertRaisesRegex(snapshot.SnapshotError, "map key/id mismatch"):
            drive._close_legacy_schema(
                {"map-id": {"id": "different-id"}}, source="test"
            )


if __name__ == "__main__":
    unittest.main()
