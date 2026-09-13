from .test_support import *


class TeamingConversionCoreTests(BaseTeamingConversionTest):
    def test_core_dispositions_and_authority(self):
        r = self.comp()
        self.assertEqual(r["payload"]["disposition"], "FOLLOWUP_READY")
        a = r["payload"]["authority"]
        self.assertTrue(a["owner_review_only"])
        self.assertTrue(all(not v for k, v in a.items() if k != "owner_review_only"))
        for interpretation, expected in [
            ("CONDITIONAL_INTEREST", "FOLLOWUP_READY"), ("REQUESTED_MORE_INFO", "NEEDS_CLARIFICATION"),
            ("AMBIGUOUS", "NEEDS_CLARIFICATION"), ("DECLINED", "DECLINED")]:
            with self.subTest(interpretation=interpretation):
                p = packet(); p["observations"][0]["interpretation"] = interpretation
                self.assertEqual(self.comp(p)["payload"]["disposition"], expected)

    def test_internal_assets_never_project(self):
        r = self.comp(); payload = r["payload"]
        self.assertNotIn("asset-internal-method", {x["asset_id"] for x in payload["safe_assets"]})
        self.assertNotIn("THIS MUST NEVER LEAK", str(payload))
        self.assertNotIn("THIS MUST NEVER LEAK", render_markdown(r))
        p = packet(); p["requested_asset_ids"] = ["asset-internal-method"]
        r = self.comp(p)
        self.assertEqual(r["payload"]["disposition"], "ASSET_PREP_REQUIRED")

    def test_required_asset_states_and_exact_owner_release(self):
        for mutation, blocker in [
            (lambda p: p.__setitem__("assets", [p["assets"][1]]), "required_asset_missing:asset-summary"),
            (lambda p: p["assets"][0].__setitem__("prep_state", "DRAFT"), "required_asset_not_ready:asset-summary"),
        ]:
            p = packet(); mutation(p); r = self.comp(p)
            self.assertEqual(r["payload"]["disposition"], "ASSET_PREP_REQUIRED")
            self.assertIn(blocker, r["payload"]["asset_blockers"])
        p = packet(); p["assets"][0]["release_class"] = "OWNER_APPROVAL_REQUIRED"
        pol = policy(); pol["asset_rules"][0] = asset_rule(p["assets"][0])
        self.assertEqual(self.comp(p, pol)["payload"]["disposition"], "ASSET_PREP_REQUIRED")
        p["release_records"] = [{
            "release_id": "rel-1", "asset_id": "asset-summary", "asset_version": "v1",
            "asset_sha256": F, "approved_at": "2026-09-13T12:40:00Z", "approved_by_ref": "owner-1",
        }]
        self.assertEqual(self.comp(p, pol)["payload"]["disposition"], "FOLLOWUP_READY")
        p["release_records"][0]["asset_sha256"] = D
        self.assertEqual(self.comp(p, pol)["payload"]["disposition"], "ASSET_PREP_REQUIRED")

    def test_asset_release_policy_is_independent_authority(self):
        # Packet cannot relabel an owner-policy INTERNAL_ONLY asset as prospect-safe.
        p = packet(); p["assets"][1]["release_class"] = "PROSPECT_SAFE_SUMMARY"
        r = self.comp(p)
        self.assertEqual(r["payload"]["disposition"], "HOLD")
        self.assertIn("asset_release_policy_mismatch:asset-internal-method", r["payload"]["blockers"])
        self.assertNotIn("THIS MUST NEVER LEAK", str(r["payload"]))

        # Even same class/digest/version cannot mutate the approved title/snippet projection.
        p = packet(); p["assets"][0]["safe_snippets"] = ["UNAPPROVED PROSPECT COPY"]
        r = self.comp(p)
        self.assertEqual(r["payload"]["disposition"], "HOLD")
        self.assertIn("asset_release_policy_mismatch:asset-summary", r["payload"]["blockers"])
        self.assertNotIn("UNAPPROVED PROSPECT COPY", r["payload"]["talking_points"])

        # Exact asset version/digest is also owner-policy authority, not packet authority.
        for field, value in (("version", "v2"), ("sha256", D)):
            p = packet(); p["assets"][0][field] = value
            r = self.comp(p)
            self.assertEqual(r["payload"]["disposition"], "HOLD")
            self.assertIn("asset_release_policy_mismatch:asset-summary", r["payload"]["blockers"])
            self.assertNotIn("asset-summary", {x["asset_id"] for x in r["payload"]["safe_assets"]})

        # Missing or duplicate independent rules fail closed before owner-ready projection.
        pol = policy(); pol["asset_rules"] = [x for x in pol["asset_rules"] if x["asset_id"] != "asset-summary"]
        r = self.comp(packet(), pol)
        self.assertEqual(r["payload"]["disposition"], "HOLD")
        self.assertIn("asset_release_policy_missing:asset-summary", r["payload"]["blockers"])
        pol = policy(); pol["asset_rules"].append(copy.deepcopy(pol["asset_rules"][0]))
        with self.assertRaises(ControlError):
            self.comp(packet(), pol)

    def test_qualification_and_commitment_fences(self):
        for state in ("BLOCKED", "UNKNOWN", "CURABLE"):
            p = packet(); p["qualification_gates"][0]["state"] = state
            self.assertEqual(self.comp(p)["payload"]["disposition"], "QUALIFICATION_BLOCKED")
        p = packet(); p["commitments"] = [{
            "commitment_id": "commit-staff", "kind": "STAFFING", "required_for_followup": True,
            "approved": False, "safe_fact": None, "approval_ref": None,
        }]
        self.assertEqual(self.comp(p)["payload"]["disposition"], "QUALIFICATION_BLOCKED")
        p["commitments"][0].update(approved=True, safe_fact="Approved staffing fact.", approval_ref="approval-1")
        r = self.comp(p)
        self.assertEqual(r["payload"]["disposition"], "FOLLOWUP_READY")
        self.assertIn("Approved staffing fact.", r["payload"]["talking_points"])
        p["commitments"][0].update(approved=False, safe_fact="smuggle", approval_ref=None)
        with self.assertRaises(ControlError): self.comp(p)

    def test_observation_conflict_thread_supersession_and_time(self):
        p = packet(); p["observations"].append(copy.deepcopy(p["observations"][0]))
        self.assertIn("observation_duplicate_id:obs-1", self.comp(p)["payload"]["blockers"])
        p = packet(); bad = copy.deepcopy(p["observations"][0]); bad["content_sha256"] = F
        p["observations"].append(bad)
        self.assertEqual(self.comp(p)["payload"]["disposition"], "HOLD")
        p = packet(); p["observations"][0]["thread_id"] = "thread-other"
        self.assertIn("cross_thread_observation:obs-1", self.comp(p)["payload"]["blockers"])
        p = packet(); p["observations"].append(obs2())
        self.assertEqual(self.comp(p)["payload"]["disposition"], "DECLINED")
        p = packet(); p["observations"].append(obs2(supersedes="obs-missing"))
        self.assertEqual(self.comp(p)["payload"]["disposition"], "HOLD")
        for field, value, blocker in [
            (("observations", 0, "received_at"), "2026-09-13T13:02:00Z", "future_observation:obs-1"),
            (("observations", 0, "received_at"), "2026-09-01T12:30:00Z", "current_observation_stale"),
            (("opportunity", "source_checked_at"), "2026-09-01T12:00:00Z", "opportunity_source_stale"),
        ]:
            p = packet()
            if len(field) == 3: p[field[0]][field[1]][field[2]] = value
            else: p[field[0]][field[1]] = value
            self.assertIn(blocker, self.comp(p)["payload"]["blockers"])

    def test_future_release_fails_closed(self):
        p = packet(); p["assets"][0]["release_class"] = "OWNER_APPROVAL_REQUIRED"
        pol = policy(); pol["asset_rules"][0] = asset_rule(p["assets"][0])
        p["release_records"] = [{
            "release_id": "rel-1", "asset_id": "asset-summary", "asset_version": "v1",
            "asset_sha256": F, "approved_at": "2026-09-13T13:02:00Z", "approved_by_ref": "owner-1",
        }]
        r = self.comp(p, pol); self.assertEqual(r["payload"]["disposition"], "HOLD")
        self.assertIn("future_release_record:rel-1", r["payload"]["blockers"])
