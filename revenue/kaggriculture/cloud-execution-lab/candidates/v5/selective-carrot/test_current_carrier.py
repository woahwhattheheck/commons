# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import unittest

import build_current as build


HERE = Path(__file__).resolve().parent
LAB_ROOT = HERE.parents[2]


def git_blob_bytes(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def current_pointer_and_archive():
    pointer_path = LAB_ROOT / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    return pointer, LAB_ROOT / pointer["path"]


def extract_regular_members(archive: Path, destination: Path) -> None:
    destination.mkdir()
    with tarfile.open(archive, "r:*") as package:
        for member in package:
            rel = PurePosixPath(member.name)
            if (
                not member.name
                or "\\" in member.name
                or rel.is_absolute()
                or ".." in rel.parts
                or str(rel) != member.name.rstrip("/")
            ):
                raise AssertionError(f"unsafe CURRENT archive member: {member.name!r}")
            if member.isdir():
                continue
            if not member.isfile():
                raise AssertionError(
                    f"non-file CURRENT archive member: {member.name!r}"
                )
            stream = package.extractfile(member)
            if stream is None:
                raise AssertionError(f"unreadable CURRENT member: {member.name!r}")
            target = destination.joinpath(*rel.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise AssertionError(f"duplicate CURRENT member: {member.name!r}")
            target.write_bytes(stream.read())


class CurrentV5SelectiveCarrotCarrierTests(unittest.TestCase):
    def test_source_pins_match_canonical_tree(self):
        self.assertEqual(
            build.git_blob(LAB_ROOT / "main.py"), build.EXPECTED_PARENT_MAIN_BLOB
        )
        self.assertEqual(
            build.git_blob(HERE / "selective_carrot.py"),
            build.EXPECTED_SELECTIVE_BLOB,
        )
        self.assertEqual(
            build.git_blob(HERE / "current_entry.py"), build.EXPECTED_ENTRY_BLOB
        )

    def test_current_archive_packages_the_pinned_parent_main(self):
        pointer, archive = current_pointer_and_archive()
        self.assertEqual(pointer["path"], "exports/titan-current.tar.gz")
        self.assertEqual(archive.stat().st_size, pointer["bytes"])
        self.assertEqual(
            hashlib.sha256(archive.read_bytes()).hexdigest(), pointer["sha256"]
        )
        with tarfile.open(archive, "r:*") as package:
            member = package.getmember("main.py")
            self.assertTrue(member.isfile())
            stream = package.extractfile(member)
            self.assertIsNotNone(stream)
            main_bytes = stream.read()
        self.assertEqual(
            git_blob_bytes(main_bytes), build.EXPECTED_PARENT_MAIN_BLOB
        )

    def test_real_current_package_materializes_both_profiles(self):
        pointer, archive = current_pointer_and_archive()
        self.assertEqual(
            hashlib.sha256(archive.read_bytes()).hexdigest(), pointer["sha256"]
        )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            baseline = root / "current"
            extract_regular_members(archive, baseline)
            control_digest = build.package_digest(baseline)
            for cap in (4, 12):
                out = root / f"cap{cap}"
                receipt = build.build_candidate(baseline, out, cap)
                self.assertEqual(receipt["max_active"], cap)
                self.assertEqual(receipt["control_package_sha256"], control_digest)
                self.assertEqual(
                    build.git_blob(out / "baseline_main.py"),
                    build.EXPECTED_PARENT_MAIN_BLOB,
                )
                profile = json.loads(
                    (out / "CARROT-CAPACITY.json").read_text(encoding="utf-8")
                )
                self.assertEqual(profile["max_active"], cap)
                self.assertEqual(
                    profile["control_package_sha256"], control_digest
                )

    def test_materializes_cap4_and_cap12_from_one_implementation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            baseline = root / "baseline"
            baseline.mkdir()
            shutil.copyfile(LAB_ROOT / "main.py", baseline / "main.py")
            (baseline / "marker.txt").write_text("current-v5\n", encoding="utf-8")
            control_digest = build.package_digest(baseline)

            receipts = []
            for cap in (4, 12):
                out = root / f"cap{cap}"
                receipt = build.build_candidate(baseline, out, cap)
                receipts.append(receipt)
                self.assertEqual(receipt["max_active"], cap)
                self.assertEqual(receipt["control_package_sha256"], control_digest)
                self.assertNotEqual(
                    receipt["candidate_package_sha256"], control_digest
                )
                self.assertEqual(
                    (out / "baseline_main.py").read_bytes(),
                    (LAB_ROOT / "main.py").read_bytes(),
                )
                self.assertEqual(
                    (out / "selective_carrot.py").read_bytes(),
                    (HERE / "selective_carrot.py").read_bytes(),
                )
                self.assertEqual(
                    (out / "main.py").read_bytes(),
                    (HERE / "current_entry.py").read_bytes(),
                )
                self.assertEqual(
                    (out / "marker.txt").read_text(encoding="utf-8"),
                    "current-v5\n",
                )
                profile = json.loads(
                    (out / "CARROT-CAPACITY.json").read_text(encoding="utf-8")
                )
                self.assertEqual(profile["max_active"], cap)
                self.assertEqual(
                    profile["control_package_sha256"], control_digest
                )
                self.assertEqual(
                    profile["entry_git_blob"], build.EXPECTED_ENTRY_BLOB
                )
                self.assertEqual(
                    profile["entry_git_blob"],
                    build.git_blob(HERE / "current_entry.py"),
                )

            self.assertEqual(
                receipts[0]["selective_carrot_git_blob"],
                receipts[1]["selective_carrot_git_blob"],
            )
            self.assertEqual(
                receipts[0]["entry_git_blob"], receipts[1]["entry_git_blob"]
            )
            self.assertNotEqual(
                receipts[0]["candidate_package_sha256"],
                receipts[1]["candidate_package_sha256"],
            )

    def test_rejects_non_profile_capacity_and_parent_drift(self):
        for value in (True, 0, 8, 13):
            with self.assertRaises(ValueError):
                build._capacity(value)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            baseline = root / "baseline"
            baseline.mkdir()
            source = (LAB_ROOT / "main.py").read_text(encoding="utf-8")
            (baseline / "main.py").write_text(source + "\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError, "expected exact current-V5 parent main.py"
            ):
                build.build_candidate(baseline, root / "out", 4)

    def test_output_cannot_alias_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            baseline = Path(folder) / "baseline"
            baseline.mkdir()
            shutil.copyfile(LAB_ROOT / "main.py", baseline / "main.py")
            with self.assertRaisesRegex(ValueError, "outside baseline root"):
                build.build_candidate(baseline, baseline / "out", 4)


if __name__ == "__main__":
    unittest.main()
