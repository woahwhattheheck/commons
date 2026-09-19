import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import compiler

FIX = json.loads((ROOT / "fixtures/pursuits.synthetic.json").read_text())


class CompilerTests(unittest.TestCase):
    def c(self, x=None):
        return compiler.compile_payload(copy.deepcopy(FIX if x is None else x))

    def test_states_and_shortlist(self):
        p = self.c()["payload"]
        states = {r["requirement_id"]: r["state"] for r in p["crosswalk"]}
        self.assertEqual(states, {"R1": "PASS", "R2": "PARTNER_REQUIRED", "R3": "PRIME_SUPPORTED"})
        self.assertEqual(p["partner_capability_shortlist"][0]["company"], "UNASSIGNED")
        self.assertEqual(p["partner_capability_shortlist"][0]["route"], "UNASSIGNED")

    def test_sensitive_generic_cannot_promote(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["evidence"].append({"evidence_id": "E3", "owner": "PRIME", "category": "GENERIC", "status": "VERIFIED", "source_uri": "f/g", "source_sha256": "d" * 64, "observed_at": "2026-09-17T12:00:00-04:00", "valid_until": None, "covers_requirement_ids": ["R2"]})
        self.assertEqual({r["requirement_id"]: r["state"] for r in self.c(x)["payload"]["crosswalk"]}["R2"], "OWNER_INPUT")

    def test_bad_mapped_evidence_holds_even_with_other_prime(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["evidence"] += [
            {"evidence_id": "BAD", "owner": "TJLABS", "category": "REFERENCE", "status": "UNVERIFIED", "source_uri": "f/bad", "source_sha256": "d" * 64, "observed_at": "2026-09-17T12:00:00-04:00", "valid_until": None, "covers_requirement_ids": ["R2"]},
            {"evidence_id": "OTHER", "owner": "PRIME", "category": "REFERENCE", "status": "VERIFIED", "source_uri": "f/other", "source_sha256": "e" * 64, "observed_at": "2026-09-17T12:00:00-04:00", "valid_until": None, "covers_requirement_ids": []}
        ]
        row = [r for r in self.c(x)["payload"]["crosswalk"] if r["requirement_id"] == "R2"][0]
        self.assertEqual(row["state"], "OWNER_INPUT")

    def test_stale_pursuit_source_holds(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["source_valid_until"] = "2026-09-16T00:00:00Z"
        self.assertTrue(all(r["state"] == "OWNER_INPUT" for r in self.c(x)["payload"]["crosswalk"]))

    def test_live_missing_carriers_exact_blocker(self):
        x = copy.deepcopy(FIX)
        x["materialization_mode"] = "LIVE"
        out = self.c(x)["payload"]
        self.assertEqual(out["status"], compiler.BLOCKED_NO_CARRIER)
        self.assertEqual(out["blockers"], [compiler.BLOCKED_NO_CARRIER])

    def test_live_caller_carriers_cannot_self_authenticate(self):
        x = copy.deepcopy(FIX)
        x["materialization_mode"] = "LIVE"
        x["verified_carrier_set"] = [{"pursuit_id": "SYN-001", "source_uri": "f/a", "source_sha256": "1" * 64, "observed_at": "2026-09-17T12:00:00-04:00", "valid_until": "2026-09-20T00:00:00Z", "verified": True}]
        for i in range(2, 6):
            x["verified_carrier_set"].append({"pursuit_id": f"C{i}", "source_uri": f"f/{i}", "source_sha256": str(i) * 64, "observed_at": "2026-09-17T12:00:00-04:00", "valid_until": "2026-09-20T00:00:00Z", "verified": True})
        out = self.c(x)["payload"]
        self.assertEqual(out["status"], compiler.BLOCKED_NO_CARRIER)
        self.assertEqual(out["blockers"], [compiler.BLOCKED_NO_CARRIER])

    def test_dedup_shortlist(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["requirements"].append({"requirement_id": "R4", "text": "Second reference", "mandatory": True, "partner_eligible": True, "category": "REFERENCE", "capability_key": "public-sector-reference"})
        out = self.c(x)["payload"]["partner_capability_shortlist"]
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]["requirement_refs"]), 2)

    def test_deterministic_permutation(self):
        a = self.c()
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["requirements"].reverse()
        x["pursuits"][0]["evidence"].reverse()
        b = self.c(x)
        self.assertEqual(a["receipt"], b["receipt"])
        self.assertEqual(a["markdown"], b["markdown"])

    def test_duplicate_requirement_rejected(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["requirements"].append(copy.deepcopy(x["pursuits"][0]["requirements"][0]))
        with self.assertRaises(compiler.InputError):
            self.c(x)

    def test_unknown_key_rejected(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["requirements"][0]["company"] = "Acme"
        with self.assertRaises(compiler.InputError):
            self.c(x)

    def test_https_userinfo_rejected(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["source_uri"] = "https://user:pw@example.com/x"
        with self.assertRaises(compiler.InputError):
            self.c(x)

    def test_future_evidence_holds(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["evidence"][0]["observed_at"] = "2026-09-18T12:00:00-04:00"
        row = [r for r in self.c(x)["payload"]["crosswalk"] if r["requirement_id"] == "R1"][0]
        self.assertEqual(row["state"], "OWNER_INPUT")

    def test_compile_verify_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            inp = Path(d) / "in.json"
            out = Path(d) / "out"
            inp.write_text(json.dumps(FIX))
            compiler.compile_to_dir(inp, out)
            self.assertTrue(compiler.verify(inp, out))
            (out / "shortlist.md").write_text("tampered")
            self.assertFalse(compiler.verify(inp, out))

    def test_create_exclusive_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            inp = Path(d) / "in.json"
            out = Path(d) / "out"
            inp.write_text(json.dumps(FIX))
            compiler.compile_to_dir(inp, out)
            with self.assertRaises(FileExistsError):
                compiler.compile_to_dir(inp, out)

    def test_authority_all_false(self):
        authority = self.c()["payload"]["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(v is False for v in authority.values()))

    def test_trusted_generation_is_receipt_bound(self):
        out = self.c()
        n = out["normalized_input"]
        self.assertRegex(n["trusted_generation_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(n["currentness_basis"], "CALLER_HISTORICAL_SYNTHETIC")
        self.assertEqual(
            out["payload"]["trusted_generation_sha256"],
            n["trusted_generation_sha256"],
        )
        self.assertEqual(
            out["receipt"]["trusted_generation_sha256"],
            n["trusted_generation_sha256"],
        )

    def test_forged_tjlabs_verified_digest_cannot_promote(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["evidence"][0]["source_sha256"] = "d" * 64
        row = [
            r for r in self.c(x)["payload"]["crosswalk"]
            if r["requirement_id"] == "R1"
        ][0]
        self.assertEqual(row["state"], "OWNER_INPUT")
        self.assertEqual(row["reason"], "MAPPED_EVIDENCE_NOT_AUTHENTICATED")

    def test_forged_prime_source_cannot_promote(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["evidence"][1]["source_uri"] = "fixtures/e1.json"
        x["pursuits"][0]["evidence"][1]["source_sha256"] = (
            "cd9ada0ba1c2654c738c618008f1627c0744e5a9e840544de377ed0fcb94abce"
        )
        row = [
            r for r in self.c(x)["payload"]["crosswalk"]
            if r["requirement_id"] == "R3"
        ][0]
        self.assertEqual(row["state"], "OWNER_INPUT")
        self.assertNotEqual(row["state"], "PRIME_SUPPORTED")

    def test_owner_relabel_cannot_promote(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["evidence"][1]["owner"] = "TJLABS"
        row = [
            r for r in self.c(x)["payload"]["crosswalk"]
            if r["requirement_id"] == "R3"
        ][0]
        self.assertEqual(row["state"], "OWNER_INPUT")
        self.assertNotEqual(row["state"], "PASS")

    def test_requirement_mapping_transplant_cannot_promote(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["evidence"][0]["covers_requirement_ids"] = ["R2"]
        rows = {
            r["requirement_id"]: r
            for r in self.c(x)["payload"]["crosswalk"]
        }
        self.assertNotIn(rows["R1"]["state"], {"PASS", "PRIME_SUPPORTED"})
        self.assertEqual(rows["R2"]["state"], "OWNER_INPUT")

    def test_requirement_contract_remint_cannot_promote(self):
        x = copy.deepcopy(FIX)
        x["pursuits"][0]["requirements"][0]["text"] = (
            "Reminted requirement wording"
        )
        row = [
            r for r in self.c(x)["payload"]["crosswalk"]
            if r["requirement_id"] == "R1"
        ][0]
        self.assertEqual(row["state"], "OWNER_INPUT")
        self.assertEqual(
            row["reason"],
            "REQUIREMENT_CONTRACT_NOT_AUTHENTICATED",
        )

    def test_synthetic_trust_generation_grants_no_live_authority(self):
        x = copy.deepcopy(FIX)
        x["materialization_mode"] = "LIVE"
        out = self.c(x)
        self.assertEqual(out["payload"]["status"], compiler.BLOCKED_NO_CARRIER)
        self.assertEqual(
            out["normalized_input"]["currentness_basis"],
            "PROCESS_UTC",
        )
        self.assertFalse(
            out["normalized_input"]["pursuits"][0]["source_authenticated"]
        )
        self.assertTrue(
            all(r["state"] == "OWNER_INPUT" for r in out["payload"]["crosswalk"])
        )

    def test_live_saved_compiler_ignores_module_classifier_rebind(self):
        x = copy.deepcopy(FIX)
        x["materialization_mode"] = "LIVE"
        saved_compile = compiler.compile_payload
        classifier_before = compiler._state_for
        try:
            compiler._state_for = lambda *_: (
                "PASS",
                "CURRENT_EXACT_TJLABS_EVIDENCE",
            )
            out = saved_compile(x)
        finally:
            compiler._state_for = classifier_before

        rows = out["payload"]["crosswalk"]
        self.assertTrue(rows)
        self.assertTrue(all(r["state"] == "OWNER_INPUT" for r in rows))
        self.assertTrue(all(
            r["state"] not in {"PASS", "PRIME_SUPPORTED"}
            for r in rows
        ))
        self.assertEqual(out["payload"]["status"], compiler.BLOCKED_NO_CARRIER)

    def test_live_caller_clock_rollback_cannot_revive_expired_source(self):
        x = copy.deepcopy(FIX)
        x["materialization_mode"] = "LIVE"
        x["as_of"] = "2020-01-05T00:00:00Z"
        x["pursuits"][0]["source_observed_at"] = "2020-01-01T00:00:00Z"
        x["pursuits"][0]["source_valid_until"] = "2020-01-10T00:00:00Z"
        out = self.c(x)
        p = out["normalized_input"]["pursuits"][0]
        self.assertEqual(
            out["normalized_input"]["currentness_basis"],
            "PROCESS_UTC",
        )
        self.assertFalse(p["source_current"])
        self.assertTrue(
            all(r["state"] == "OWNER_INPUT" for r in out["payload"]["crosswalk"])
        )

    def test_real_python_O_guard(self):
        with tempfile.TemporaryDirectory() as d:
            x = copy.deepcopy(FIX)
            x["pursuits"][0]["requirements"][0]["company"] = "forbidden"
            inp = Path(d) / "bad.json"
            inp.write_text(json.dumps(x))
            p = subprocess.run([sys.executable, "-O", str(ROOT / "compiler.py"), "compile", "--input", str(inp), "--out-dir", str(Path(d) / "out")], capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("unexpected keys", p.stderr)


if __name__ == "__main__":
    unittest.main()
