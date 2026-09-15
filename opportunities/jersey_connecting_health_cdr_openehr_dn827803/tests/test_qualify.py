from __future__ import annotations
import copy, hashlib, json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import qualify

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode() + b"\n"

def load(path):
    return qualify.load_json_bytes(path.read_bytes(), str(path))

class Tests(unittest.TestCase):
    def setUp(self):
        self.source = load(ROOT / "sources.json")
        self.manifest = load(ROOT / "fixtures/public_hold.json")

    def run_case(self, source=None, manifest=None, pack=None):
        source = copy.deepcopy(source if source is not None else self.source)
        manifest = copy.deepcopy(manifest if manifest is not None else self.manifest)
        raw = canonical(source)
        manifest["source_ledger_sha256"] = hashlib.sha256(raw).hexdigest()
        return qualify.evaluate(manifest, source, raw, tender_pack_bytes=pack)

    def acquired(self, reviewed=True, pack=b"TEST-ONLY synthetic tender pack\n"):
        source = copy.deepcopy(self.source)
        source["tender_pack"] = {
            "acquired": True,
            "reviewed": reviewed,
            "sha256": hashlib.sha256(pack).hexdigest(),
            "state": "TENDER_PACK_ACQUIRED_REVIEWED" if reviewed else "TENDER_PACK_ACQUIRED_UNREVIEWED",
        }
        return source, pack

    @staticmethod
    def proven(route):
        return {
            "schema_version": 1,
            "notice_id": qualify.NOTICE_ID,
            "evaluated_at": "2026-09-13T11:20:00Z",
            "source_ledger_sha256": "0" * 64,
            "route": route,
            "partner_prime_confirmed": True,
            "authority": {k: False for k in qualify.AUTHORITY_FLAGS},
            "capabilities": {g: {"status": "PROVEN", "evidence_refs": [f"evidence:{g}"]} for g in qualify.ROUTES[route]},
        }

    def test_public_holds_pack(self):
        r = self.run_case(); self.assertEqual(r.state, "HOLD_TENDER_PACK_REQUIRED"); self.assertEqual(r.exit_code, 3)
        self.assertFalse(r.payload["tender_submission_authorized"])

    def test_deterministic(self):
        self.assertEqual(self.run_case().bytes(), self.run_case().bytes())

    def test_duplicate_key(self):
        with self.assertRaisesRegex(qualify.QualificationError, "DUPLICATE_JSON_KEY"):
            qualify.load_json_bytes(b'{"a":1,"a":2}', "x")

    def test_bool_as_int(self):
        m = copy.deepcopy(self.manifest); m["schema_version"] = True
        with self.assertRaisesRegex(qualify.QualificationError, "MUST_BE_INT_NOT_BOOL"):
            self.run_case(manifest=m)

    def test_authority_escalation(self):
        m = copy.deepcopy(self.manifest); m["authority"]["tender_submission"] = True
        with self.assertRaisesRegex(qualify.QualificationError, "AUTHORITY_ESCALATION_FORBIDDEN"):
            self.run_case(manifest=m)

    def test_proven_requires_evidence(self):
        m = copy.deepcopy(self.manifest); gate = next(iter(m["capabilities"])); m["capabilities"][gate] = {"status":"PROVEN","evidence_refs":[]}
        with self.assertRaisesRegex(qualify.QualificationError, "PROVEN_REQUIRES_EVIDENCE"):
            self.run_case(manifest=m)

    def test_pack_digest_mismatch(self):
        s, pack = self.acquired(); s["tender_pack"]["sha256"] = "a"*64
        with self.assertRaisesRegex(qualify.QualificationError, "TENDER_PACK_DIGEST_MISMATCH"):
            self.run_case(source=s, manifest=self.proven("TEAMING_ACCEPTANCE_EVIDENCE"), pack=pack)

    def test_declared_pack_without_bytes_holds(self):
        s, _ = self.acquired(); r = self.run_case(source=s, manifest=self.proven("TEAMING_ACCEPTANCE_EVIDENCE"), pack=None)
        self.assertEqual(r.state, "HOLD_TENDER_PACK_FILE_REQUIRED")

    def test_unreviewed_pack_holds(self):
        s, pack = self.acquired(reviewed=False); r = self.run_case(source=s, manifest=self.proven("TEAMING_ACCEPTANCE_EVIDENCE"), pack=pack)
        self.assertEqual(r.state, "HOLD_TENDER_PACK_REVIEW")

    def test_missing_evidence_holds(self):
        s, pack = self.acquired(); m = copy.deepcopy(self.manifest); m["route"] = "PRIME_CDR"
        m["capabilities"] = {g:{"status":"UNKNOWN","evidence_refs":[]} for g in qualify.ROUTES["PRIME_CDR"]}
        r = self.run_case(source=s, manifest=m, pack=pack); self.assertEqual(r.state, "HOLD_EVIDENCE_GAPS")

    def test_teaming_requires_prime(self):
        s, pack = self.acquired(); m = self.proven("TEAMING_INTEROPERABILITY_SPECIALIST"); m["partner_prime_confirmed"] = False
        r = self.run_case(source=s, manifest=m, pack=pack); self.assertEqual(r.state, "HOLD_PARTNER_REQUIRED")

    def test_ready_is_owner_review_only(self):
        s, pack = self.acquired(); r = self.run_case(source=s, manifest=self.proven("TEAMING_ACCEPTANCE_EVIDENCE"), pack=pack)
        self.assertEqual(r.state, "READY_FOR_OWNER_TENDER_REVIEW"); self.assertEqual(r.exit_code, 0)
        self.assertFalse(r.payload["tender_submission_authorized"])

    def test_stale_source_holds(self):
        s, pack = self.acquired(); s["checked_at"] = "2026-07-01T00:00:00+00:00"
        r = self.run_case(source=s, manifest=self.proven("TEAMING_ACCEPTANCE_EVIDENCE"), pack=pack)
        self.assertEqual(r.state, "HOLD_SOURCE_STALE")

    def test_source_digest_binding(self):
        m = copy.deepcopy(self.manifest); m["source_ledger_sha256"] = "0"*64
        raw = canonical(self.source)
        with self.assertRaisesRegex(qualify.QualificationError, "SOURCE_LEDGER_DIGEST_MISMATCH"):
            qualify.evaluate(m, self.source, raw)

if __name__ == "__main__": unittest.main()
