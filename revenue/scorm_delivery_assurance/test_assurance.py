from __future__ import annotations

import json
import tempfile
import unittest
import warnings
import zipfile
from io import BytesIO
from pathlib import Path

from revenue.scorm_delivery_assurance.assurance import (
    HOLD,
    READY,
    compile_assurance,
    default_policy,
    main as cli_main,
    verify_assurance,
)

MANIFEST = b'''<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
 xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2">
 <metadata><schema>ADL SCORM</schema><schemaversion>1.2</schemaversion></metadata>
 <organizations default="ORG"><organization identifier="ORG">
  <item identifier="ITEM1" identifierref="RES1"><title>Module One</title></item>
  <item identifier="ITEM2" identifierref="RES2"><title>Module Two</title></item>
 </organization></organizations>
 <resources>
  <resource identifier="RES1" type="webcontent" adlcp:scormtype="sco" href="m1/index.html">
   <file href="m1/index.html"/><file href="m1/app.js"/>
  </resource>
  <resource identifier="RES2" type="webcontent" adlcp:scormtype="sco" href="m2/index.html">
   <file href="m2/index.html"/>
  </resource>
 </resources>
</manifest>'''


def sidecar(caption2: str = "m2/captions.vtt") -> bytes:
    return json.dumps(
        {
            "schema": "tjlabs.scorm-course-evidence/v1",
            "course_id": "course-demo-01",
            "source_revision_sha256": "a" * 64,
            "modules": [
                {
                    "id": "m1",
                    "resource_id": "RES1",
                    "title": "Module One",
                    "assessment": {"required": True, "passing_score": 80},
                    "completion": {"required": True},
                    "accessibility": {
                        "transcript": "m1/transcript.txt",
                        "captions": ["m1/captions.vtt"],
                    },
                },
                {
                    "id": "m2",
                    "resource_id": "RES2",
                    "title": "Module Two",
                    "assessment": {"required": True, "passing_score": 75},
                    "completion": {"required": True},
                    "accessibility": {
                        "transcript": "m2/transcript.txt",
                        "captions": [caption2],
                    },
                },
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def make_zip(extra=None, manifest=MANIFEST, evidence=None, duplicate=None) -> bytes:
    files = {
        "imsmanifest.xml": manifest,
        "course.assurance.json": evidence if evidence is not None else sidecar(),
        "m1/index.html": b"<html><body>one</body></html>",
        "m1/app.js": b"console.log('one')",
        "m1/transcript.txt": b"Transcript one",
        "m1/captions.vtt": b"WEBVTT\n",
        "m2/index.html": b"<html><body>two</body></html>",
        "m2/transcript.txt": b"Transcript two",
        "m2/captions.vtt": b"WEBVTT\n",
    }
    if extra:
        files.update(extra)
    out = BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, files[name])
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(duplicate[0], duplicate[1])
    return out.getvalue()


class AssuranceTests(unittest.TestCase):
    def test_ready_two_module_package(self):
        package = make_zip()
        report = compile_assurance(package)
        self.assertEqual(READY, report["status"])
        self.assertEqual(2, report["facts"]["module_count"])
        self.assertEqual("SCORM_1_2", report["facts"]["standard"])
        self.assertTrue(verify_assurance(package, report))

    def test_missing_caption_holds(self):
        report = compile_assurance(make_zip(evidence=sidecar("m2/missing.vtt")))
        self.assertEqual(HOLD, report["status"])
        self.assertTrue(any("missing accessibility evidence" in x for x in report["reasons"]))

    def test_traversal_holds(self):
        report = compile_assurance(make_zip(extra={"../escape.txt": b"x"}))
        self.assertEqual(HOLD, report["status"])
        self.assertTrue(any("non-canonical" in x for x in report["reasons"]))

    def test_external_launch_holds(self):
        manifest = MANIFEST.replace(
            b'href="m1/index.html"', b'href="https://evil.invalid/a"', 1
        )
        report = compile_assurance(make_zip(manifest=manifest))
        self.assertEqual(HOLD, report["status"])
        self.assertTrue(any("external manifest href" in x for x in report["reasons"]))

    def test_duplicate_member_holds(self):
        report = compile_assurance(make_zip(duplicate=("m1/index.html", b"changed")))
        self.assertEqual(HOLD, report["status"])
        self.assertTrue(any("duplicate ZIP member" in x for x in report["reasons"]))

    def test_case_collision_holds(self):
        report = compile_assurance(make_zip(extra={"M1/INDEX.HTML": b"shadow"}))
        self.assertEqual(HOLD, report["status"])
        self.assertTrue(any("case-colliding" in x for x in report["reasons"]))

    def test_sidecar_resource_set_must_match_org(self):
        obj = json.loads(sidecar())
        obj["modules"] = obj["modules"][:1]
        report = compile_assurance(make_zip(evidence=json.dumps(obj).encode()))
        self.assertEqual(HOLD, report["status"])
        self.assertTrue(any("resource set" in x for x in report["reasons"]))

    def test_duplicate_json_key_holds(self):
        raw = (
            b'{"schema":"tjlabs.scorm-course-evidence/v1","schema":"x",'
            b'"course_id":"a","source_revision_sha256":"' + b"a" * 64 + b'","modules":[]}'
        )
        report = compile_assurance(make_zip(evidence=raw))
        self.assertEqual(HOLD, report["status"])
        self.assertTrue(any("duplicate JSON key" in x for x in report["reasons"]))

    def test_bool_as_integer_policy_rejected(self):
        policy = default_policy()
        policy["max_files"] = True
        with self.assertRaises(ValueError):
            compile_assurance(make_zip(), policy)

    def test_policy_file_threshold_holds(self):
        policy = default_policy()
        policy["max_files"] = 2
        report = compile_assurance(make_zip(), policy)
        self.assertEqual(HOLD, report["status"])
        self.assertTrue(any("file count" in x for x in report["reasons"]))

    def test_tamper_breaks_verify(self):
        package = make_zip()
        report = compile_assurance(package)
        changed = make_zip(extra={"note.txt": b"changed"})
        self.assertFalse(verify_assurance(changed, report))

    def test_exact_bytes_are_deterministic(self):
        package = make_zip()
        self.assertEqual(compile_assurance(package), compile_assurance(package))

    def test_authority_never_claims_certification_or_revenue(self):
        authority = compile_assurance(make_zip())["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))

    def test_cli_compile_verify_and_no_overwrite(self):
        package = make_zip()
        with tempfile.TemporaryDirectory() as directory:
            pkg = Path(directory) / "course.zip"
            receipt = Path(directory) / "receipt.json"
            pkg.write_bytes(package)
            self.assertEqual(0, cli_main(["compile", str(pkg), str(receipt)]))
            self.assertEqual(0, cli_main(["verify", str(pkg), str(receipt)]))
            self.assertEqual(2, cli_main(["compile", str(pkg), str(receipt)]))


if __name__ == "__main__":
    unittest.main()
