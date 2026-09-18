"""Hard-false authority predecessor for the public APProof API.

The advertised compatibility object may be mutated or rebound by ordinary Python
callers, but projection authority is code-owned and must remain false.  This file
also runs the exact hostile under an optimized child interpreter so the closure
is not assertion-mode dependent.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from revenue.ohsu_ap_ai_rfi_approof import approof, common, engine

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "revenue" / "ohsu_ap_ai_rfi_approof" / "fixture.json"
AUTHORITY_FIELDS = {
    "oracle_ebs_write_authorized",
    "invoice_approval_authorized",
    "payment_authorized",
    "supplier_contact_authorized",
    "buyer_submission_authorized",
    "contract_award_claimed",
    "revenue_claimed",
}


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class AuthorityBoundaryTests(unittest.TestCase):
    def test_public_authority_mutation_cannot_promote_projection(self):
        self.assertIs(approof.AUTHORITY, common.AUTHORITY)
        original_object = common.AUTHORITY
        original_values = dict(original_object)
        had_engine_name = hasattr(engine, "AUTHORITY")
        original_engine_name = getattr(engine, "AUTHORITY", None)
        malicious = {field: True for field in AUTHORITY_FIELDS}

        try:
            # Exercise the exact predecessor: mutate the exported shared dict,
            # then also replace every public/module-facing authority name a caller
            # can reasonably reach.  Compilation must consult none of them.
            original_object.clear()
            original_object.update(malicious)
            approof.AUTHORITY = dict(malicious)
            common.AUTHORITY = dict(malicious)
            engine.AUTHORITY = dict(malicious)

            packet = load_fixture()
            projection = approof.compile_packet(packet)
            self.assertEqual(set(projection["authority"]), AUTHORITY_FIELDS)
            self.assertTrue(all(value is False for value in projection["authority"].values()))
            self.assertTrue(projection["oracle_shadow_rows"])
            self.assertTrue(all(row["posting_authorized"] is False for row in projection["oracle_shadow_rows"]))
            self.assertTrue(approof.verify_projection(packet, projection))

            promoted = copy.deepcopy(projection)
            for field in AUTHORITY_FIELDS:
                promoted["authority"][field] = True
            for row in promoted["oracle_shadow_rows"]:
                row["posting_authorized"] = True
            self.assertFalse(approof.verify_projection(packet, promoted))
        finally:
            original_object.clear()
            original_object.update(original_values)
            common.AUTHORITY = original_object
            approof.AUTHORITY = original_object
            if had_engine_name:
                engine.AUTHORITY = original_engine_name
            else:
                try:
                    del engine.AUTHORITY
                except AttributeError:
                    pass

    def test_same_predecessor_under_python_optimized(self):
        cp = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-v",
                "test_ohsu_ap_ai_rfi_approof_authority.AuthorityBoundaryTests.test_public_authority_mutation_cannot_promote_projection",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        self.assertEqual(cp.returncode, 0, cp.stdout.decode() + cp.stderr.decode())


if __name__ == "__main__":
    unittest.main(verbosity=2)
