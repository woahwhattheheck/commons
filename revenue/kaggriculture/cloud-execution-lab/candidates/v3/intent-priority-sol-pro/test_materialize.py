# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

import materialize


def deterministic_tar(files: dict[str, bytes], *, symlink: bool = False) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            for name, data in sorted(files.items()):
                info = tarfile.TarInfo(name)
                if symlink and name == "scheduler.py":
                    info.type = tarfile.SYMTYPE
                    info.linkname = "main.py"
                    info.size = 0
                    archive.addfile(info)
                else:
                    info.size = len(data)
                    info.mode = 0o644
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


class Fixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.lab = root / "lab"
        (self.lab / "exports").mkdir(parents=True)
        (self.lab / "runtime/integrated-selected").mkdir(parents=True)
        scheduler = (
            b"PRODUCTS=('MILK','EGG','WOOL')\n"
            b"class S:\n"
            b"    def f(self,shed):\n"
            + materialize.OLD
            + b"        return targets\n"
        )
        runtime = {
            "main.py": (
                b"def agent(observation, configuration=None):\n"
                b"    return {'farmer':['PASS'],'hands':[],'market':[]}\n"
            ),
            "scheduler.py": scheduler,
            "TITAN-CONFIG.json": b"{}\n",
        }
        source = {
            "entrypoint": "main.py::agent",
            "runtime": {
                name: {"bytes": len(data), "sha256": materialize.sha256(data)}
                for name, data in runtime.items()
            },
        }
        source_bytes = (
            json.dumps(source, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        files = dict(runtime)
        files["SOURCE.json"] = source_bytes
        archive = deterministic_tar(files)
        self.archive = archive
        self.archive_sha = materialize.sha256(archive)
        self.source_sha = materialize.sha256(source_bytes)
        self.scheduler_blob = materialize.git_blob_sha1(scheduler)
        (self.lab / "exports/titan-current.tar.gz").write_bytes(archive)
        receipt = {
            "path": "exports/titan-current.tar.gz",
            "entrypoint": "main.py::agent",
            "config": "TITAN-CONFIG.json",
            "sha256": self.archive_sha,
            "bytes": len(archive),
            "runtime_files": len(runtime),
            "source_manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
            "source_manifest_sha256": self.source_sha,
        }
        (
            self.lab / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
        ).write_text(json.dumps(receipt))

    def patches(self):
        return mock.patch.multiple(
            materialize,
            EXPECTED_ARCHIVE_SHA256=self.archive_sha,
            EXPECTED_ARCHIVE_BYTES=len(self.archive),
            EXPECTED_RUNTIME_FILES=3,
            EXPECTED_SOURCE_MANIFEST_SHA256=self.source_sha,
            EXPECTED_SCHEDULER_BLOB=self.scheduler_blob,
        )


class MaterializeTests(unittest.TestCase):
    def test_default_off_is_exact_and_enabled_is_scheduler_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            with fixture.patches():
                control = materialize.materialize(
                    lab=fixture.lab,
                    output=Path(temporary) / "control",
                    integration_head="head",
                    enabled=False,
                )
                candidate = materialize.materialize(
                    lab=fixture.lab,
                    output=Path(temporary) / "candidate",
                    integration_head="head",
                    enabled=True,
                )

            self.assertFalse(control["feature"]["enabled"])
            self.assertEqual(control["candidate"]["changed_files"], [])
            self.assertEqual(
                control["source"]["closure_sha256"],
                control["candidate"]["closure_sha256"],
            )
            self.assertTrue(candidate["feature"]["enabled"])
            self.assertEqual(
                candidate["candidate"]["changed_files"], ["scheduler.py"]
            )
            self.assertEqual(
                candidate["candidate"]["old_occurrences_after"], 0
            )
            self.assertEqual(
                candidate["candidate"]["new_occurrences_after"], 1
            )
            control_files = materialize.inventory_tree(
                Path(temporary) / "control"
            )
            candidate_files = materialize.inventory_tree(
                Path(temporary) / "candidate"
            )
            changed = [
                name
                for name in sorted(control_files)
                if control_files[name] != candidate_files[name]
            ]
            self.assertEqual(changed, ["scheduler.py"])

    def test_priority_preserves_domain_and_quantities(self) -> None:
        products = ("MILK", "EGG", "WOOL", "MANURE")
        shed = {"MILK": 4, "EGG": 2, "WOOL": 0, "MANURE": 7, "BAD": 9}
        canonical = materialize.canonical_targets(
            products=products, shed=shed
        )
        enabled = materialize.priority_targets(
            pending={"MANURE": 1, "BAD": 1},
            baseline_q={"EGG": 1, "MANURE": 2},
            products=products,
            shed=shed,
        )
        self.assertEqual(set(enabled), set(canonical))
        self.assertEqual(enabled, {
            "MANURE": 7,
            "EGG": 2,
            "MILK": 4,
        })
        self.assertEqual(
            {name: enabled[name] for name in canonical},
            canonical,
        )

    def test_pending_then_baseline_then_products_is_first_insertion(self) -> None:
        enabled = materialize.priority_targets(
            pending={"EGG": 1, "MILK": 1},
            baseline_q={"MILK": 2, "MANURE": 1},
            products=("MILK", "EGG", "WOOL", "MANURE"),
            shed={"MILK": 1, "EGG": 1, "WOOL": 1, "MANURE": 1},
        )
        self.assertEqual(
            list(enabled),
            ["EGG", "MILK", "MANURE", "WOOL"],
        )

    def test_source_expression_cardinality_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Fixture(Path(temporary))
            archive_path = fixture.lab / "exports/titan-current.tar.gz"
            # Rebuild an otherwise valid archive with two old expressions.
            source_scheduler = (
                b"class S:\n"
                b"    def f(self,shed):\n"
                + materialize.OLD
                + materialize.OLD
                + b"        return targets\n"
            )
            runtime = {
                "main.py": b"def agent(o,c=None): return {}\n",
                "scheduler.py": source_scheduler,
                "TITAN-CONFIG.json": b"{}\n",
            }
            source = {
                "runtime": {
                    name: {
                        "bytes": len(data),
                        "sha256": materialize.sha256(data),
                    }
                    for name, data in runtime.items()
                }
            }
            source_bytes = (
                json.dumps(source, sort_keys=True) + "\n"
            ).encode()
            payload = dict(runtime)
            payload["SOURCE.json"] = source_bytes
            archive = deterministic_tar(payload)
            archive_path.write_bytes(archive)
            receipt = {
                "path": "exports/titan-current.tar.gz",
                "entrypoint": "main.py::agent",
                "config": "TITAN-CONFIG.json",
                "sha256": materialize.sha256(archive),
                "bytes": len(archive),
                "runtime_files": 3,
                "source_manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
                "source_manifest_sha256": materialize.sha256(source_bytes),
            }
            (
                fixture.lab
                / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
            ).write_text(json.dumps(receipt))
            with mock.patch.multiple(
                materialize,
                EXPECTED_ARCHIVE_SHA256=materialize.sha256(archive),
                EXPECTED_ARCHIVE_BYTES=len(archive),
                EXPECTED_RUNTIME_FILES=3,
                EXPECTED_SOURCE_MANIFEST_SHA256=materialize.sha256(
                    source_bytes
                ),
                EXPECTED_SCHEDULER_BLOB=materialize.git_blob_sha1(
                    source_scheduler
                ),
            ):
                with self.assertRaisesRegex(
                    materialize.MaterializeError,
                    "expected one canonical target expression",
                ):
                    materialize.materialize(
                        lab=fixture.lab,
                        output=Path(temporary) / "out",
                        integration_head="head",
                        enabled=True,
                    )

    def test_link_member_is_rejected(self) -> None:
        files = {
            "main.py": b"",
            "scheduler.py": materialize.OLD,
        }
        archive = deterministic_tar(files, symlink=True)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "unsafe.tar.gz"
            path.write_bytes(archive)
            with mock.patch.multiple(
                materialize,
                EXPECTED_ARCHIVE_SHA256=materialize.sha256(archive),
                EXPECTED_ARCHIVE_BYTES=len(archive),
            ):
                with self.assertRaisesRegex(
                    materialize.MaterializeError,
                    "not a regular file",
                ):
                    materialize.read_archive(path)


if __name__ == "__main__":
    unittest.main()
