# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import audit


UNSAFE = b'''\
KEEP = 72

def patch_routes(routes):
    sites = [(t, i) for t, row in enumerate(routes) for i, action in enumerate(row) if action == "PLANT"]
    extra = max(0, len(sites) - KEEP)
    for t, i in sites[-extra:]:
        routes[t][i] = "PASS"
'''

SAFE_IF = b'''\
KEEP = 72

def patch_routes(routes):
    sites = [(t, i) for t, row in enumerate(routes) for i, action in enumerate(row) if action == "PLANT"]
    extra = max(0, len(sites) - KEEP)
    if extra:
        for t, i in sites[-extra:]:
            routes[t][i] = "PASS"
'''

SAFE_EARLY_RETURN = b'''\
KEEP = 72

def patch_routes(routes):
    sites = [(t, i) for t, row in enumerate(routes) for i, action in enumerate(row) if action == "PLANT"]
    extra = max(0, len(sites) - KEEP)
    if extra == 0:
        return routes
    for t, i in sites[-extra:]:
        routes[t][i] = "PASS"
'''


def make_bundle(files: dict[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as bundle:
            for name, content in sorted(files.items()):
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mtime = 0
                info.mode = 0o644
                bundle.addfile(info, io.BytesIO(content))
    return raw.getvalue()


class StaticRuleTests(unittest.TestCase):
    def test_unsafe_negative_zero_slice_is_proved(self):
        findings = audit.analyze_source("overlay/l01.py", UNSAFE)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.keep_value, 72)
        self.assertTrue(finding.mutation_observed)
        exact = finding.metamorphic_counterexamples["exact_target_fixed_point"]
        repeat = finding.metamorphic_counterexamples["repeat_application"]
        alias = finding.metamorphic_counterexamples["shared_object_alias"]
        self.assertEqual(
            (exact["input_site_count"], exact["observed_output_site_count"]),
            (72, 0),
        )
        self.assertEqual(
            (
                repeat["input_site_count"],
                repeat["after_first_application"],
                repeat["after_second_application"],
            ),
            (164, 72, 0),
        )
        self.assertEqual(alias["independent_deepcopy_each_key"], [72, 72])
        self.assertEqual(alias["after_second_alias_key"], 0)

    def test_positive_if_guard_closes_hazard(self):
        self.assertEqual(audit.analyze_source("overlay/l01.py", SAFE_IF), [])

    def test_terminating_zero_guard_closes_hazard(self):
        self.assertEqual(
            audit.analyze_source("overlay/l01.py", SAFE_EARLY_RETURN), []
        )

    def test_symbolic_keep_still_reports(self):
        source = UNSAFE.replace(b"KEEP = 72", b"KEEP = int('72')")
        finding = audit.analyze_source("overlay/l01.py", source)[0]
        self.assertIsNone(finding.keep_value)
        self.assertEqual(finding.severity, "critical")
        self.assertEqual(finding.metamorphic_counterexamples["status"], "symbolic")

    def test_report_is_deterministic(self):
        files = {"z.py": SAFE_IF, "a.py": UNSAFE}
        custody = {
            "archive_sha256": "x",
            "archive_bytes": 1,
            "member_count": 2,
            "members": {},
        }
        one = audit._canonical_json(audit.build_report(files, custody))
        two = audit._canonical_json(
            audit.build_report(dict(reversed(list(files.items()))), custody)
        )
        self.assertEqual(one, two)
        self.assertEqual(
            hashlib.sha256(one).hexdigest(), hashlib.sha256(two).hexdigest()
        )


class CustodyTests(unittest.TestCase):
    def _write_encoded(self, directory: Path, archive: bytes) -> Path:
        path = directory / "handoff.b64"
        path.write_bytes(base64.encodebytes(archive))
        return path

    def test_authenticated_safe_bundle(self):
        archive = make_bundle(
            {"overlay/l01.py": UNSAFE, "README.md": b"ok\n"}
        )
        with tempfile.TemporaryDirectory() as td:
            path = self._write_encoded(Path(td), archive)
            files, custody = audit.read_handoff(
                path,
                expected_sha256=hashlib.sha256(archive).hexdigest(),
                expected_bytes=len(archive),
                expected_members=frozenset({"overlay/l01.py", "README.md"}),
            )
        self.assertEqual(files["overlay/l01.py"], UNSAFE)
        self.assertEqual(custody["member_count"], 2)

    def test_hash_mismatch_fails_closed(self):
        archive = make_bundle({"a.py": b"pass\n"})
        with tempfile.TemporaryDirectory() as td:
            path = self._write_encoded(Path(td), archive)
            with self.assertRaisesRegex(audit.AuditError, "sha256 mismatch"):
                audit.read_handoff(
                    path,
                    expected_sha256="0" * 64,
                    expected_bytes=len(archive),
                    expected_members=frozenset({"a.py"}),
                )

    def test_traversal_member_fails_closed(self):
        archive = make_bundle({"../escape.py": b"pass\n"})
        with tempfile.TemporaryDirectory() as td:
            path = self._write_encoded(Path(td), archive)
            with self.assertRaisesRegex(audit.AuditError, "unsafe tar member"):
                audit.read_handoff(
                    path,
                    expected_sha256=hashlib.sha256(archive).hexdigest(),
                    expected_bytes=len(archive),
                    expected_members=None,
                )

    def test_duplicate_normalized_member_fails_closed(self):
        raw = io.BytesIO()
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as bundle:
                for name in ("a.py", "./a.py"):
                    content = b"pass\n"
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    bundle.addfile(info, io.BytesIO(content))
        archive = raw.getvalue()
        with tempfile.TemporaryDirectory() as td:
            path = self._write_encoded(Path(td), archive)
            with self.assertRaisesRegex(audit.AuditError, "duplicate normalized"):
                audit.read_handoff(
                    path,
                    expected_sha256=hashlib.sha256(archive).hexdigest(),
                    expected_bytes=len(archive),
                    expected_members=None,
                )

    def test_non_regular_member_fails_closed(self):
        raw = io.BytesIO()
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as bundle:
                info = tarfile.TarInfo("dir")
                info.type = tarfile.DIRTYPE
                bundle.addfile(info)
        archive = raw.getvalue()
        with tempfile.TemporaryDirectory() as td:
            path = self._write_encoded(Path(td), archive)
            with self.assertRaisesRegex(audit.AuditError, "non-regular"):
                audit.read_handoff(
                    path,
                    expected_sha256=hashlib.sha256(archive).hexdigest(),
                    expected_bytes=len(archive),
                    expected_members=None,
                )


if __name__ == "__main__":
    unittest.main()
