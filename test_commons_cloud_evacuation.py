import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


MODULE_PATH = Path(__file__).parent / "host" / "commons_cloud_evacuation.py"
SPEC = importlib.util.spec_from_file_location("commons_cloud_evacuation", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CommonsCloudEvacuationTests(unittest.TestCase):
    def test_inventory_is_read_only_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            first = tmp_path / "first"
            second = tmp_path / "second"
            first.mkdir()
            second.mkdir()
            payload = b"same Commons bytes\n"
            (first / "a.bin").write_bytes(payload)
            (second / "b.bin").write_bytes(payload)
            before = {path: path.read_bytes() for path in (first / "a.bin", second / "b.bin")}

            inventory = MODULE.build_inventory([first, second])
            plan = MODULE.cloud_plan(inventory, "gdrive:commons")

            self.assertTrue(inventory["complete"])
            self.assertEqual(inventory["file_count"], 2)
            self.assertEqual(inventory["source_bytes"], 2 * len(payload))
            self.assertEqual(inventory["unique_object_count"], 1)
            self.assertEqual(inventory["unique_bytes"], len(payload))
            self.assertEqual(len(plan["objects"]), 1)
            self.assertEqual(len(plan["objects"][0]["sources"]), 2)
            self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_missing_root_never_claims_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inventory = MODULE.build_inventory([Path(directory) / "missing"])
            self.assertFalse(inventory["complete"])
            self.assertTrue(inventory["errors"])

    def test_stage_copies_once_and_requires_remote_hash_readback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            payload = b"cloud me once"
            (source / "one").write_bytes(payload)
            (source / "two").write_bytes(payload)
            inventory = MODULE.build_inventory([source])
            remote: dict[str, bytes] = {}
            calls: list[list[str]] = []

            def runner(command: list[str], *, input_bytes: bytes | None = None):
                calls.append(command)
                operation = command[1]
                if operation == "cat":
                    if command[2] not in remote:
                        return subprocess.CompletedProcess(command, 1, b"", b"not found")
                    return subprocess.CompletedProcess(command, 0, remote[command[2]], b"")
                if operation == "copyto":
                    remote[command[3]] = Path(command[2]).read_bytes()
                    return subprocess.CompletedProcess(command, 0, b"", b"")
                if operation == "rcat":
                    remote[command[2]] = input_bytes or b""
                    return subprocess.CompletedProcess(command, 0, b"", b"")
                raise AssertionError(command)

            receipt = MODULE.stage(inventory, "gdrive:commons", runner)

            self.assertTrue(receipt["cloud_complete"])
            self.assertFalse(receipt["local_sources_modified"])
            self.assertTrue(receipt["local_release_eligible"])
            self.assertFalse(receipt["local_release_performed"])
            self.assertEqual(sum(command[1] == "copyto" for command in calls), 1)
            self.assertEqual((source / "one").read_bytes(), payload)
            self.assertEqual((source / "two").read_bytes(), payload)

    def test_stage_rejects_bad_cloud_readback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            (source / "file").write_bytes(b"original")
            inventory = MODULE.build_inventory([source])

            def runner(command: list[str], *, input_bytes: bytes | None = None):
                if command[1] == "copyto":
                    return subprocess.CompletedProcess(command, 0, b"", b"")
                if command[1] == "cat":
                    return subprocess.CompletedProcess(command, 0, b"wrong", b"")
                raise AssertionError(command)

            with self.assertRaisesRegex(RuntimeError, "hash readback failed"):
                MODULE.stage(inventory, "gdrive:commons", runner)

    def test_stage_rejects_source_changed_after_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            target = source / "file"
            target.write_bytes(b"original")
            inventory = MODULE.build_inventory([source])
            target.write_bytes(b"changed")

            def runner(command: list[str], *, input_bytes: bytes | None = None):
                if command[1] == "cat":
                    return subprocess.CompletedProcess(command, 1, b"", b"not found")
                raise AssertionError(command)

            with self.assertRaisesRegex(RuntimeError, "source changed after inventory"):
                MODULE.stage(inventory, "gdrive:commons", runner)

    def test_source_contains_no_destructive_operation(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        forbidden = ["unlink(", "rmtree(", "os.remove(", "shutil.move(", '\"--delete\"']
        self.assertFalse([needle for needle in forbidden if needle in source])

    def test_inventory_identity_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            (source / "a").write_bytes(b"a")
            first = MODULE.build_inventory([source])
            second = MODULE.build_inventory([source])
            self.assertEqual(first["inventory_sha256"], second["inventory_sha256"])
            self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
