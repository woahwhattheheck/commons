from __future__ import annotations

import copy
import json
import unittest

from downselect import ContractError, compile_portfolio, parse_json_strict


SHA_A = "1" * 40
SHA_B = "2" * 40


def claim(name: str, state: str = "EVIDENCED") -> dict:
    return {
        "claimId": name,
        "state": state,
        "evidenceRef": f"evidence:{name}" if state == "EVIDENCED" else None,
    }


def candidate(
    cid: str,
    sha: str,
    *,
    evidence: bool = True,
    traction: bool = True,
    overlap: str = "NONE",
    usamrdc: bool = False,
) -> dict:
    state = "EVIDENCED" if evidence else "PROPOSED"
    return {
        "candidateId": cid,
        "source": {
            "repo": "woahwhattheheck/example",
            "commit": sha,
            "path": f"products/{cid}",
        },
        "priorityArea": "ADAPTIVE_SUSTAINMENT",
        "usamrdcExclusive": usamrdc,
        "federalSupportOverlap": overlap,
        "criteria": {
            "introduction": [claim(f"{cid}.intro", state)],
            "armyBenefits": [claim(f"{cid}.army", state)],
            "technicalApproach": [claim(f"{cid}.technical", state)],
            "commercialPotential": [claim(f"{cid}.commercial", state)],
            "proposalQuality": [claim(f"{cid}.quality", state)],
        },
        "traction": (
            [
                {
                    "evidenceId": f"{cid}.pilot",
                    "kind": "CUSTOMER_PILOT",
                    "evidenceRef": f"external:{cid}:pilot",
                }
            ]
            if traction
            else []
        ),
    }


def gate(state: str = "CONFIRMED_TRUE") -> dict:
    return {
        "state": state,
        "evidenceRef": "owner:evidence" if state != "UNKNOWN" else None,
    }


def ready_packet() -> dict:
    return {
        "version": "xtech.search10.portfolio/v1",
        "entityId": "owner-entity",
        "globalGates": {
            "forProfitIndependentUsSmallBusiness": gate(),
            "ownershipControlEligible": gate(),
            "employeeCeilingMet": gate(),
            "sbirSmallBusinessRequirementsMet": gate(),
            "federalSupportCensus": {"state": "CLEAR", "evidenceRef": "owner:federal-census"},
            "oneSubmissionSlot": {"state": "AVAILABLE", "evidenceRef": "owner:slot-census"},
            "officialTemplate": {"state": "BOUND", "evidenceRef": "provider:template-digest"},
        },
        "candidates": [
            candidate("alpha", SHA_A, evidence=True, traction=True),
            candidate("beta", SHA_B, evidence=False, traction=True),
        ],
    }


class DownselectTests(unittest.TestCase):
    def test_unique_fully_gated_leader_is_internal_selected_only(self) -> None:
        report = compile_portfolio(ready_packet())
        self.assertEqual(report["state"], "SELECTED")
        self.assertEqual(report["selectedCandidateId"], "alpha")
        self.assertFalse(report["authority"]["submissionAuthorized"])
        self.assertFalse(report["authority"]["entitySlotConsumed"])

    def test_unknown_entity_facts_force_hold(self) -> None:
        packet = ready_packet()
        packet["globalGates"]["ownershipControlEligible"] = gate("UNKNOWN")
        report = compile_portfolio(packet)
        self.assertEqual(report["state"], "HOLD")
        self.assertEqual(report["holdReason"], "GLOBAL_GATES")
        self.assertIsNone(report["selectedCandidateId"])

    def test_missing_template_forces_hold(self) -> None:
        packet = ready_packet()
        packet["globalGates"]["officialTemplate"] = {"state": "UNKNOWN", "evidenceRef": None}
        report = compile_portfolio(packet)
        self.assertEqual(report["state"], "HOLD")
        self.assertTrue(any("officialTemplate" in row for row in report["globalBlockers"]))

    def test_consumed_entity_slot_forces_hold(self) -> None:
        packet = ready_packet()
        packet["globalGates"]["oneSubmissionSlot"] = {
            "state": "CONSUMED_OR_RESERVED",
            "evidenceRef": "provider:slot",
        }
        self.assertEqual(compile_portfolio(packet)["state"], "HOLD")

    def test_support_census_blocked_forces_hold(self) -> None:
        packet = ready_packet()
        packet["globalGates"]["federalSupportCensus"] = {
            "state": "BLOCKED",
            "evidenceRef": "owner:collision",
        }
        self.assertEqual(compile_portfolio(packet)["state"], "HOLD")

    def test_candidate_support_overlap_is_hard_blocker(self) -> None:
        packet = ready_packet()
        packet["candidates"][0] = candidate(
            "alpha", SHA_A, evidence=True, traction=True, overlap="POTENTIALLY_SAME"
        )
        report = compile_portfolio(packet)
        self.assertEqual(report["state"], "HOLD")
        alpha = next(row for row in report["projections"] if row["candidateId"] == "alpha")
        self.assertIn("federal_support_overlap:POTENTIALLY_SAME", alpha["hardBlockers"])

    def test_no_external_traction_is_hard_blocker(self) -> None:
        packet = ready_packet()
        packet["candidates"][0] = candidate("alpha", SHA_A, evidence=True, traction=False)
        report = compile_portfolio(packet)
        alpha = next(row for row in report["projections"] if row["candidateId"] == "alpha")
        self.assertIn("commercial_traction:missing_external_evidence", alpha["hardBlockers"])

    def test_repo_activity_cannot_become_traction(self) -> None:
        packet = ready_packet()
        packet["candidates"][0]["traction"] = [
            {
                "evidenceId": "stars",
                "kind": "GITHUB_STARS",
                "evidenceRef": None,
            }
        ]
        report = compile_portfolio(packet)
        alpha = next(row for row in report["projections"] if row["candidateId"] == "alpha")
        self.assertIn("fake_traction:stars:GITHUB_STARS", alpha["hardBlockers"])
        self.assertEqual(alpha["externalTractionEvidenceCount"], 0)

    def test_forbidden_claim_is_hard_blocker(self) -> None:
        packet = ready_packet()
        packet["candidates"][0]["criteria"]["technicalApproach"][0] = claim(
            "alpha.weapon-control", "FORBIDDEN"
        )
        report = compile_portfolio(packet)
        alpha = next(row for row in report["projections"] if row["candidateId"] == "alpha")
        self.assertIn("claim:alpha.weapon-control:FORBIDDEN", alpha["hardBlockers"])

    def test_usamrdc_exclusive_candidate_is_hard_blocked(self) -> None:
        packet = ready_packet()
        packet["candidates"][0]["usamrdcExclusive"] = True
        report = compile_portfolio(packet)
        alpha = next(row for row in report["projections"] if row["candidateId"] == "alpha")
        self.assertIn("scope:USAMRDC_EXCLUSIVE", alpha["hardBlockers"])

    def test_equal_readiness_tie_holds_without_arbitrary_winner(self) -> None:
        packet = ready_packet()
        packet["candidates"][1] = candidate("beta", SHA_B, evidence=True, traction=True)
        report = compile_portfolio(packet)
        self.assertEqual(report["state"], "HOLD")
        self.assertEqual(report["holdReason"], "TOP_READINESS_TIE")
        self.assertIsNone(report["selectedCandidateId"])

    def test_duplicate_candidate_id_fails_closed(self) -> None:
        packet = ready_packet()
        packet["candidates"][1]["candidateId"] = "alpha"
        with self.assertRaisesRegex(ContractError, "DUPLICATE_CANDIDATE_ID"):
            compile_portfolio(packet)

    def test_invalid_source_generation_fails_closed(self) -> None:
        packet = ready_packet()
        packet["candidates"][0]["source"]["commit"] = "main"
        with self.assertRaisesRegex(ContractError, "INVALID_SOURCE_COMMIT"):
            compile_portfolio(packet)

    def test_single_candidate_packet_fails_closed(self) -> None:
        packet = ready_packet()
        packet["candidates"] = packet["candidates"][:1]
        with self.assertRaisesRegex(ContractError, "CANDIDATE_COUNT"):
            compile_portfolio(packet)

    def test_extra_root_field_fails_closed(self) -> None:
        packet = ready_packet()
        packet["surprise"] = True
        with self.assertRaisesRegex(ContractError, "OBJECT_SHAPE"):
            compile_portfolio(packet)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "JSON_DUPLICATE_KEY"):
            parse_json_strict('{"version":1,"version":2}')

    def test_float_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "JSON_FLOAT_FORBIDDEN"):
            parse_json_strict('{"score":1.5}')

    def test_receipt_is_deterministic(self) -> None:
        packet = ready_packet()
        first = compile_portfolio(copy.deepcopy(packet))
        second = compile_portfolio(copy.deepcopy(packet))
        self.assertEqual(first["receiptSha256"], second["receiptSha256"])
        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(second, sort_keys=True, separators=(",", ":")),
        )

    def test_readiness_metric_is_not_sponsor_score(self) -> None:
        report = compile_portfolio(ready_packet())
        self.assertIn("not an Army score", report["readinessMetricMeaning"])
        self.assertNotIn("probability", report["projections"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
