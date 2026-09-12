# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import unittest

import ablate_e20_productive_detour as ablation
import build_submitted_v4_treatment as builder

HERE = Path(__file__).resolve().parent
REPO = HERE
while REPO != REPO.parent and not (REPO / ".git").exists():
    REPO = REPO.parent


def git_show(commit: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{ablation.HELPER_PATH}"],
        cwd=REPO,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def pack(members: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            for name, data in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


def unpack(data: bytes) -> dict[str, bytes]:
    return {
        info.name: archive.extractfile(info).read()
        for archive in [tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")]
        for info in archive.getmembers()
        if info.isfile()
    }


class SubmittedV4TreatmentArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v4_helper = git_show(ablation.V4_COMMIT)
        cls.v31_helper = git_show(ablation.V31_COMMIT)
        cls.manifest = {
            "runtime": {
                ablation.HELPER_PATH: {
                    "source_path": ablation.HELPER_PATH,
                    "sha256": hashlib.sha256(cls.v4_helper).hexdigest(),
                    "bytes": len(cls.v4_helper),
                },
                "main.py": {
                    "source_path": "main.py",
                    "sha256": hashlib.sha256(b"print('control')\n").hexdigest(),
                    "bytes": len(b"print('control')\n"),
                },
            },
            "default": {"redundant_hire": True},
        }
        cls.control = pack(
            {
                "main.py": b"print('control')\n",
                ablation.HELPER_PATH: cls.v4_helper,
                "SOURCE.json": (json.dumps(cls.manifest, indent=2, sort_keys=True) + "\n").encode(),
                "TITAN-CONFIG.json": b'{"redundant_hire":true}\n',
            }
        )
        cls.control_sha = builder.sha256(cls.control)

    def test_builder_changes_only_helper_semantics_and_source_metadata(self):
        treatment, receipt = builder.build_treatment_archive(
            self.control,
            self.v31_helper,
            expected_control_sha256=self.control_sha,
        )
        control = unpack(self.control)
        changed = unpack(treatment)
        self.assertEqual(set(control), set(changed))
        self.assertEqual(
            receipt["changed_members"],
            ["SOURCE.json", ablation.HELPER_PATH],
        )
        self.assertEqual(receipt["semantic_changed_members"], [ablation.HELPER_PATH])
        self.assertEqual(receipt["metadata_changed_members"], ["SOURCE.json"])
        self.assertEqual(changed["main.py"], control["main.py"])
        self.assertEqual(changed["TITAN-CONFIG.json"], control["TITAN-CONFIG.json"])
        self.assertEqual(
            ablation.git_blob(changed[ablation.HELPER_PATH]),
            receipt["treatment_helper_git_blob"],
        )
        self.assertNotEqual(changed[ablation.HELPER_PATH], control[ablation.HELPER_PATH])

        manifest = json.loads(changed["SOURCE.json"])
        entry = manifest["runtime"][ablation.HELPER_PATH]
        self.assertEqual(entry["sha256"], hashlib.sha256(changed[ablation.HELPER_PATH]).hexdigest())
        self.assertEqual(entry["bytes"], len(changed[ablation.HELPER_PATH]))
        self.assertEqual(
            manifest["experiment"]["control_archive_sha256"],
            self.control_sha,
        )
        self.assertTrue(manifest["default"]["redundant_hire"])

    def test_builder_is_deterministic(self):
        first, first_receipt = builder.build_treatment_archive(
            self.control,
            self.v31_helper,
            expected_control_sha256=self.control_sha,
        )
        second, second_receipt = builder.build_treatment_archive(
            self.control,
            self.v31_helper,
            expected_control_sha256=self.control_sha,
        )
        self.assertEqual(first, second)
        self.assertEqual(first_receipt, second_receipt)

    def test_wrong_archive_hash_and_helper_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "archive SHA256 mismatch"):
            builder.build_treatment_archive(
                self.control,
                self.v31_helper,
                expected_control_sha256="0" * 64,
            )
        with self.assertRaisesRegex(ValueError, "V3.1 .* drift"):
            builder.build_treatment_archive(
                self.control,
                self.v31_helper + b"\n# drift\n",
                expected_control_sha256=self.control_sha,
            )

    def test_source_manifest_identity_must_match_helper_member(self):
        bad_manifest = json.loads(json.dumps(self.manifest))
        bad_manifest["runtime"][ablation.HELPER_PATH]["sha256"] = "0" * 64
        bad = pack(
            {
                "main.py": b"print('control')\n",
                ablation.HELPER_PATH: self.v4_helper,
                "SOURCE.json": (json.dumps(bad_manifest, indent=2, sort_keys=True) + "\n").encode(),
            }
        )
        with self.assertRaisesRegex(ValueError, "identity does not match"):
            builder.build_treatment_archive(
                bad,
                self.v31_helper,
                expected_control_sha256=builder.sha256(bad),
            )

    def test_real_cli_constant_is_exact_retained_submission_digest(self):
        self.assertEqual(
            builder.SUBMITTED_V4_ARCHIVE_SHA256,
            "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b",
        )


if __name__ == "__main__":
    unittest.main()
