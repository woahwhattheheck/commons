import copy
import hashlib
import os
import pathlib
import tempfile
import unittest
from unittest import mock

import opportunities.hamilton_oh_data_integration_hub_065_26_jw.gate as gate

PACKAGE = pathlib.Path(gate.__file__).resolve().parent
RETAINED = PACKAGE / "retained_evidence"
NOW = "2026-09-18T01:00:00Z"
RID = "integration_engineering"
EVIDENCE_CLASS = "OWNER_CAPABILITY"

BASE_LEDGER = {
    "opportunity_id": gate.OPPORTUNITY_ID,
    "sources": [
        {
            "id": "portal",
            "authority": "OFFICIAL_PORTAL_ENTRY",
            "retrieved": False,
            "url": "https://hamiltoncountyohio.gob2g.com/",
            "observed_at": "2026-09-17T07:05:00Z",
            "claims": {},
            "controls": [],
        }
    ],
}
BASE_REQS = {
    "opportunity_id": gate.OPPORTUNITY_ID,
    "requirements": [
        {"id": rid, "state": "UNKNOWN", "evidence": []}
        for rid in gate.ALL_GATES
    ],
}
BASE_MANIFEST = {"opportunity_id": gate.OPPORTUNITY_ID, "evidence": []}


def artifact_bytes(source_id: str) -> bytes:
    record = {
        "schema": gate.EVIDENCE_ARTIFACT_SCHEMA,
        "source_id": source_id,
        "opportunity_id": gate.OPPORTUNITY_ID,
        "binding": {"requirement_id": RID, "evidence_class": EVIDENCE_CLASS},
        "evidence": {
            "kind": gate.INTERNAL_EVIDENCE_KIND[EVIDENCE_CLASS],
            "facts": ["source-controlled integration capability evidence"],
            "refs": ["fixture://integration-capability"],
        },
    }
    return gate.canonical_bytes(record) + b"\n"


def inputs_for(path: pathlib.Path, source_id: str, raw: bytes):
    sha = hashlib.sha256(raw).hexdigest()
    ledger = copy.deepcopy(BASE_LEDGER)
    reqs = copy.deepcopy(BASE_REQS)
    manifest = copy.deepcopy(BASE_MANIFEST)
    ledger["sources"].append(
        {
            "id": source_id,
            "authority": "INTERNAL_EVIDENCE",
            "retrieved": True,
            "content_sha256": sha,
            "retained_artifact": {
                "path": f"retained_evidence/{path.name}",
                "sha256": sha,
            },
            "url": f"repo://retained_evidence/{path.name}",
            "observed_at": "2026-09-18T00:00:00Z",
            "claims": {},
            "controls": [],
        }
    )
    eid = f"evidence-{source_id}"
    manifest["evidence"].append(
        {
            "id": eid,
            "opportunity_id": gate.OPPORTUNITY_ID,
            "requirement_id": RID,
            "evidence_class": EVIDENCE_CLASS,
            "content_sha256": sha,
            "source_id": source_id,
        }
    )
    row = next(item for item in reqs["requirements"] if item["id"] == RID)
    row.update({"state": "PROVEN", "evidence": [eid]})
    return ledger, reqs, manifest


class RetainedEvidenceCustodyTests(unittest.TestCase):
    def setUp(self):
        RETAINED.mkdir(exist_ok=True)
        self.created = []

    def tearDown(self):
        for path in self.created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def retained_file(self, source_id: str, raw: bytes | None = None) -> tuple[pathlib.Path, bytes]:
        raw = artifact_bytes(source_id) if raw is None else raw
        fh = tempfile.NamedTemporaryFile(
            mode="wb", dir=RETAINED, prefix="custody-", suffix=".json", delete=False
        )
        path = pathlib.Path(fh.name)
        fh.write(raw)
        fh.close()
        self.created.append(path)
        return path, raw

    def test_single_link_regular_file_is_accepted(self):
        source_id = "source-positive"
        path, raw = self.retained_file(source_id)
        ledger, reqs, manifest = inputs_for(path, source_id, raw)
        packet = gate.compile_pursuit(ledger, reqs, manifest, now=NOW)
        self.assertEqual(
            packet["evidence_bindings"][RID],
            [f"evidence-{source_id}"],
        )

    def test_hard_link_alias_into_retained_directory_is_rejected(self):
        source_id = "source-hardlink"
        raw = artifact_bytes(source_id)
        with tempfile.TemporaryDirectory(dir=PACKAGE.parent) as outside_dir:
            outside = pathlib.Path(outside_dir) / "outside.json"
            outside.write_bytes(raw)
            link = RETAINED / "custody-hardlink.json"
            try:
                os.link(outside, link)
            except OSError as exc:
                self.skipTest(f"hard links unavailable on test filesystem: {exc}")
            self.created.append(link)
            ledger, reqs, manifest = inputs_for(link, source_id, raw)
            with self.assertRaisesRegex(gate.GateError, "exactly one filesystem link"):
                gate.compile_pursuit(ledger, reqs, manifest, now=NOW)

    def test_generation_swap_between_lstat_and_open_is_rejected(self):
        source_id = "source-preopen-swap"
        path, raw = self.retained_file(source_id)
        replacement, _ = self.retained_file(source_id, raw)
        ledger, reqs, manifest = inputs_for(path, source_id, raw)
        real_open = os.open
        real_replace = os.replace
        swapped = False

        def swapping_open(target, flags, *args, **kwargs):
            nonlocal swapped
            if pathlib.Path(target) == path and not swapped:
                swapped = True
                real_replace(replacement, path)
            return real_open(target, flags, *args, **kwargs)

        with mock.patch.object(gate.os, "open", new=swapping_open):
            with self.assertRaisesRegex(gate.GateError, "generation changed before read"):
                gate.compile_pursuit(ledger, reqs, manifest, now=NOW)

    def test_path_swap_after_descriptor_open_is_rejected(self):
        source_id = "source-postopen-swap"
        path, raw = self.retained_file(source_id)
        replacement, _ = self.retained_file(source_id, raw)
        ledger, reqs, manifest = inputs_for(path, source_id, raw)
        real_read = os.read
        real_replace = os.replace
        swapped = False

        def swapping_read(fd, count):
            nonlocal swapped
            chunk = real_read(fd, count)
            if chunk and not swapped:
                swapped = True
                real_replace(replacement, path)
            return chunk

        with mock.patch.object(gate.os, "read", new=swapping_read):
            with self.assertRaisesRegex(gate.GateError, "exactly one filesystem link|generation changed during read"):
                gate.compile_pursuit(ledger, reqs, manifest, now=NOW)


if __name__ == "__main__":
    unittest.main()
