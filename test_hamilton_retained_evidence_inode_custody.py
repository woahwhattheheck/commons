from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_hamilton_oh_data_integration_hub_065_26_jw as base


gate = base.gate


def _hardlink_case():
    sid = "source-hardlink-alias"
    eid = "evidence-hardlink-alias"
    rid = "integration_engineering"
    evidence_class = "OWNER_CAPABILITY"
    record = {
        "schema": gate.EVIDENCE_ARTIFACT_SCHEMA,
        "source_id": sid,
        "opportunity_id": gate.OPPORTUNITY_ID,
        "binding": {
            "requirement_id": rid,
            "evidence_class": evidence_class,
        },
        "evidence": {
            "kind": "OWNER_CAPABILITY_RECORD",
            "facts": ["outside-owned bytes must not mint retained qualification"],
            "refs": ["fixture://hardlink-alias"],
        },
    }
    raw = gate.canonical_bytes(record) + b"\n"
    sha = hashlib.sha256(raw).hexdigest()
    ledger = base.official(base.BASE_LEDGER)
    reqs = copy.deepcopy(base.BASE_REQS)
    manifest = copy.deepcopy(base.BASE_EVIDENCE)
    return sid, eid, rid, evidence_class, raw, sha, ledger, reqs, manifest


class HamiltonRetainedEvidenceInodeCustodyTests(unittest.TestCase):
    def test_outside_owned_hardlink_alias_cannot_mint_proven(self):
        sid, eid, rid, evidence_class, raw, sha, ledger, reqs, manifest = _hardlink_case()
        base.RETAINED.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside-owned.json"
            outside.write_bytes(raw)
            alias = base.RETAINED / f"test-hardlink-{os.getpid()}.json"
            try:
                os.link(outside, alias)
                self.assertFalse(alias.is_symlink())
                self.assertTrue(alias.is_file())
                self.assertEqual(alias.stat().st_ino, outside.stat().st_ino)
                self.assertGreaterEqual(alias.stat().st_nlink, 2)

                ledger["sources"].append(
                    {
                        "id": sid,
                        "authority": "INTERNAL_EVIDENCE",
                        "retrieved": True,
                        "content_sha256": sha,
                        "retained_artifact": {
                            "path": f"retained_evidence/{alias.name}",
                            "sha256": sha,
                        },
                        "url": f"repo://retained_evidence/{alias.name}",
                        "observed_at": "2026-09-18T00:00:00Z",
                        "claims": {},
                        "controls": [],
                    }
                )
                manifest["evidence"].append(
                    {
                        "id": eid,
                        "opportunity_id": gate.OPPORTUNITY_ID,
                        "requirement_id": rid,
                        "evidence_class": evidence_class,
                        "content_sha256": sha,
                        "source_id": sid,
                    }
                )
                base.row(reqs, rid).update({"state": "PROVEN", "evidence": [eid]})

                with self.assertRaisesRegex(
                    gate.GateError,
                    "exactly one filesystem link",
                ):
                    gate.compile_pursuit(
                        ledger,
                        reqs,
                        manifest,
                        now="2026-09-18T01:00:00Z",
                    )
            finally:
                try:
                    alias.unlink()
                except FileNotFoundError:
                    pass

    def test_hardlink_predecessor_runs_under_real_python_optimized_mode(self):
        if os.environ.get("HAMILTON_INODE_OPT_CHILD") == "1":
            return
        env = dict(os.environ)
        env["HAMILTON_INODE_OPT_CHILD"] = "1"
        subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-v",
                Path(__file__).stem,
            ],
            cwd=Path(__file__).resolve().parent,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
