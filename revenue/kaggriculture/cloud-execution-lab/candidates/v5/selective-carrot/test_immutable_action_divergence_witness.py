#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

import immutable_action_divergence_witness as immutable


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def archive(path: Path, files: dict[str, bytes]) -> dict[str, str]:
    with tarfile.open(path, "w:gz") as tar:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))
    return {name: sha(data) for name, data in sorted(files.items())}


def adapter(path: Path, contract: Path, main: Path) -> bytes:
    data = (
        "import importlib.util as _util\n_runner = None\n"
        "def agent(observation, configuration=None):\n"
        "    global _runner\n"
        "    if _runner is None:\n"
        f"        spec = _util.spec_from_file_location('kag_pack_contract', {str(contract)!r})\n"
        "        module = _util.module_from_spec(spec)\n"
        "        spec.loader.exec_module(module)\n"
        f"        _runner = module.make_agent({str(main)!r})\n"
        "    return _runner(observation, configuration or {})\n"
    ).encode()
    write(path, data)
    return data


class ImmutableActionWitnessTests(unittest.TestCase):
    def _fixture(self, root: Path):
        candidate = root / "candidate"
        contract = root / "pack"
        files = {
            "main.py": b"def agent(o, c=None): return {'farmer': 'PASS', 'hands': []}\n",
            "helper.py": b"VALUE = 7\n",
        }
        for name, data in files.items():
            write(candidate / name, data)
        contract_code = (
            b"def make_agent(path):\n"
            b"    def call(obs, cfg=None):\n"
            b"        return {'farmer': 'PASS', 'hands': []}\n"
            b"    return call\n"
        )
        write(contract / "official.py", contract_code)
        write(contract / "upstream" / "manifest.json", b"{}\n")
        archive_path = root / "candidate.tar.gz"
        members = archive(archive_path, files)
        entry = root / "adapter.py"
        adapter(entry, contract / "official.py", candidate / "main.py")
        return entry, candidate, contract, archive_path, members

    def test_capture_is_independent_of_later_source_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, candidate, contract, _archive_path, members = self._fixture(root)
            spec, meta = immutable._capture_agent(
                f"{entry}::agent", root / "snapshot", archive_members=members
            )
            snapshot_entry = Path(spec.partition("::")[0])
            before = {
                "entry": snapshot_entry.read_bytes(),
                "main": (snapshot_entry.parent / "candidate" / "main.py").read_bytes(),
                "helper": (snapshot_entry.parent / "candidate" / "helper.py").read_bytes(),
                "contract": (snapshot_entry.parent / "contract" / "official.py").read_bytes(),
            }

            entry.write_text("raise RuntimeError('mutated adapter')\n")
            (candidate / "main.py").write_text("raise RuntimeError('mutated main')\n")
            (candidate / "helper.py").write_text("VALUE = 99\n")
            (contract / "official.py").write_text("raise RuntimeError('mutated contract')\n")

            self.assertEqual(snapshot_entry.read_bytes(), before["entry"])
            self.assertEqual(
                (snapshot_entry.parent / "candidate" / "main.py").read_bytes(),
                before["main"],
            )
            self.assertEqual(
                (snapshot_entry.parent / "candidate" / "helper.py").read_bytes(),
                before["helper"],
            )
            self.assertEqual(
                (snapshot_entry.parent / "contract" / "official.py").read_bytes(),
                before["contract"],
            )
            self.assertTrue(meta["archive_members_verified"])

    def test_generated_entry_is_destination_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, _candidate, _contract, _archive_path, members = self._fixture(root)
            spec_a, meta_a = immutable._capture_agent(
                f"{entry}::agent", root / "snap-a", archive_members=members
            )
            spec_b, meta_b = immutable._capture_agent(
                f"{entry}::agent", root / "snap-b", archive_members=members
            )
            self.assertNotEqual(spec_a, spec_b)
            self.assertEqual(
                meta_a["snapshot_entry_sha256"], meta_b["snapshot_entry_sha256"]
            )
            self.assertEqual(
                meta_a["candidate_manifest_sha256"],
                meta_b["candidate_manifest_sha256"],
            )
            self.assertEqual(
                meta_a["contract_manifest_sha256"],
                meta_b["contract_manifest_sha256"],
            )

    def test_candidate_runtime_must_equal_authenticated_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, candidate, _contract, _archive_path, members = self._fixture(root)
            (candidate / "helper.py").write_text("VALUE = 8\n")
            with self.assertRaisesRegex(
                immutable.SnapshotError, "differs from authenticated archive"
            ):
                immutable._capture_agent(
                    f"{entry}::agent", root / "snapshot", archive_members=members
                )

    def test_runtime_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, candidate, _contract, _archive_path, members = self._fixture(root)
            target = candidate / "helper.py"
            target.unlink()
            try:
                target.symlink_to(candidate / "main.py")
            except OSError as exc:
                self.skipTest(f"Symlink creation not permitted: {exc}")
            with self.assertRaisesRegex(immutable.SnapshotError, "symlink"):
                immutable._capture_agent(
                    f"{entry}::agent", root / "snapshot", archive_members=members
                )

    def test_archive_snapshot_rejects_nonregular_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / "bad.tar.gz"
            with tarfile.open(bad, "w:gz") as tar:
                directory = tarfile.TarInfo("nested")
                directory.type = tarfile.DIRTYPE
                tar.addfile(directory)
                data = b"x\n"
                info = tarfile.TarInfo("main.py")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            expected = sha(bad.read_bytes())
            with self.assertRaisesRegex(
                immutable.SnapshotError, "not a regular file"
            ):
                immutable._archive_snapshot(
                    bad, expected, root / "snapshot" / "bad.tar.gz"
                )


    def _load_agent(self, entry_path: Path):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            f"test_entry_{entry_path.parent.name}_{entry_path.stat().st_mtime_ns}",
            entry_path,
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.agent

    def test_worker_private_tree_executes_and_survives_later_snapshot_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, _candidate, _contract, _archive_path, members = self._fixture(root)
            spec, _meta = immutable._capture_agent(
                f"{entry}::agent", root / "snapshot", archive_members=members
            )
            snapshot_entry = Path(spec.partition("::")[0])
            agent_fn = self._load_agent(snapshot_entry)

            # First step copies into private temp tree, verifies digest, and executes.
            action1 = agent_fn({"step": 0})
            self.assertEqual(action1, {"farmer": "PASS", "hands": []})

            # Mutating the shared snapshot after worker startup must not affect running worker.
            (snapshot_entry.parent / "candidate" / "helper.py").write_text("POISONED\n")
            action2 = agent_fn({"step": 1})
            self.assertEqual(action2, {"farmer": "PASS", "hands": []})

    def test_shared_snapshot_mutation_before_worker_load_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, _candidate, _contract, _archive_path, members = self._fixture(root)
            spec, _meta = immutable._capture_agent(
                f"{entry}::agent", root / "snapshot", archive_members=members
            )
            snapshot_entry = Path(spec.partition("::")[0])

            # Mutate shared snapshot after capture but before worker load.
            (snapshot_entry.parent / "candidate" / "helper.py").write_text("POISONED\n")

            agent_fn = self._load_agent(snapshot_entry)
            with self.assertRaisesRegex(RuntimeError, "candidate snapshot file helper.py drifted"):
                agent_fn({"step": 0})

    def test_shared_snapshot_contract_mutation_before_worker_load_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, _candidate, _contract, _archive_path, members = self._fixture(root)
            spec, _meta = immutable._capture_agent(
                f"{entry}::agent", root / "snapshot", archive_members=members
            )
            snapshot_entry = Path(spec.partition("::")[0])

            # Mutate contract after capture but before worker load.
            (snapshot_entry.parent / "contract" / "official.py").write_text("POISONED\n")

            agent_fn = self._load_agent(snapshot_entry)
            with self.assertRaisesRegex(RuntimeError, "contract snapshot file official.py drifted"):
                agent_fn({"step": 0})

    def test_apex_retained_map_missing_file_rejected_at_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, _candidate, _contract, _archive_path, members = self._fixture(root)
            with self.assertRaisesRegex(
                immutable.SnapshotError, r"captured candidate runtime differs.*missing=\['agent.so'"
            ):
                immutable._capture_agent(
                    f"{entry}::agent",
                    root / "snapshot",
                    archive_members=None,
                    expected_candidate_files=immutable.EXPECTED_APEX_RUNTIME,
                )

    def test_apex_retained_map_extra_file_rejected_at_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, _candidate, _contract, _archive_path, members = self._fixture(root)
            with self.assertRaisesRegex(
                immutable.SnapshotError, r"captured candidate runtime differs.*extra=\['helper.py'\]"
            ):
                immutable._capture_agent(
                    f"{entry}::agent",
                    root / "snapshot",
                    archive_members=None,
                    expected_candidate_files={"main.py": members["main.py"]},
                )

    def test_contract_retained_map_extra_file_rejected_at_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry, _candidate, contract, _archive_path, members = self._fixture(root)
            write(contract / "extra_shadow.py", b"EXTRA\n")
            adapter(entry, contract / "official.py", _candidate / "main.py")
            with self.assertRaisesRegex(
                immutable.SnapshotError, r"captured contract runtime differs.*extra=\['extra_shadow.py'\]"
            ):
                immutable._capture_agent(
                    f"{entry}::agent",
                    root / "snapshot",
                    archive_members=members,
                    expected_contract_files={
                        "official.py": sha((contract / "official.py").read_bytes()),
                        "upstream/manifest.json": sha((contract / "upstream" / "manifest.json").read_bytes()),
                    },
                )


if __name__ == "__main__":
    unittest.main()

