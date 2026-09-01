import tempfile
import unittest
from pathlib import Path

from charttrace.app import (
    AnalysisBlockedError,
    CaseLifecycle,
    ChartTraceController,
)
from charttrace.legal import ConsentError, ConsentLedger, LegalState


class LegalGateTests(unittest.TestCase):
    def setUp(self):
        self.controller = ChartTraceController(persist=False)
        self.controller.unlock("test-only-secret", "Test operator")

    def accept_current_suite(self):
        acknowledgements = self.controller.consent.blank_acknowledgements()
        for instrument_id in acknowledgements:
            acknowledgements[instrument_id] = True
        self.controller.accept_legal(acknowledgements, "Test operator")

    def test_all_acknowledgements_start_unchecked_and_are_separate(self):
        acknowledgements = ConsentLedger.blank_acknowledgements()
        self.assertEqual(7, len(acknowledgements))
        self.assertTrue(all(value is False for value in acknowledgements.values()))
        acknowledgements["terms"] = True
        with self.assertRaises(ConsentError):
            self.controller.accept_legal(acknowledgements, "Test operator")
        self.assertEqual(LegalState.NOT_ACCEPTED, self.controller.legal_state)

    def test_analysis_and_ingest_are_held_before_acceptance(self):
        case = self.controller.create_case("Synthetic test case")
        self.assertEqual(
            CaseLifecycle.HOLD_TERMS_OR_AUTHORITY, case.lifecycle
        )
        with self.assertRaises(AnalysisBlockedError):
            self.controller.secure_ingest(
                case.case_id, [("source.txt", b"synthetic test bytes")]
            )
        with self.assertRaises(AnalysisBlockedError):
            self.controller.run_peer_analysis(case.case_id)

    def test_current_acceptance_opens_ingest_and_analysis(self):
        case = self.controller.create_case("Synthetic test case")
        self.accept_current_suite()
        self.assertEqual(CaseLifecycle.READY_TO_INGEST, case.lifecycle)
        self.controller.secure_ingest(
            case.case_id, [("source.txt", b"synthetic test bytes")]
        )
        output = self.controller.run_peer_analysis(case.case_id)
        self.assertEqual("UNSIGNED_SYNTHETIC", output["kind"])
        self.assertEqual("unsigned", output["signing_state"])
        self.assertEqual(CaseLifecycle.PEER_ANALYSIS, case.lifecycle)

    def test_authority_hold_closes_analysis_gate(self):
        self.accept_current_suite()
        case = self.controller.create_case("Synthetic test case")
        self.controller.secure_ingest(
            case.case_id, [("source.txt", b"synthetic test bytes")]
        )
        self.controller.place_authority_hold("Authority requires confirmation")
        self.assertEqual(LegalState.AUTHORITY_HOLD, self.controller.legal_state)
        with self.assertRaises(AnalysisBlockedError):
            self.controller.run_peer_analysis(case.case_id)
        self.controller.clear_authority_hold()
        self.assertEqual(
            LegalState.REACCEPT_REQUIRED, self.controller.legal_state
        )


class RecipientAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.controller = ChartTraceController(persist=False)
        self.controller.unlock("test-only-secret", "Test operator")
        acknowledgements = self.controller.consent.blank_acknowledgements()
        self.controller.accept_legal(
            {key: True for key in acknowledgements}, "Test operator"
        )
        self.case = self.controller.create_case("Synthetic release case")

    def test_transfer_defaults_off_and_recipient_change_requires_new_authorization(self):
        self.assertEqual(
            LegalState.TRANSFER_NOT_AUTHORIZED, self.case.transfer_state
        )
        self.controller.set_recipient(
            self.case.case_id, "First named attorney", "attorney"
        )
        self.assertEqual(
            LegalState.TRANSFER_NOT_AUTHORIZED, self.case.transfer_state
        )
        self.controller.authorize_recipient_transfer(
            self.case.case_id, True, "Test operator"
        )
        self.assertEqual(LegalState.TRANSFER_AUTHORIZED, self.case.transfer_state)

        self.controller.set_recipient(
            self.case.case_id, "Second named attorney", "attorney"
        )
        self.assertEqual(
            LegalState.TRANSFER_NOT_AUTHORIZED, self.case.transfer_state
        )
        self.assertIsNone(self.case.recipient.authorized_at)

    def test_release_lifecycle_requires_human_review_and_transfer(self):
        self.controller.secure_ingest(
            self.case.case_id, [("source.bin", b"non-sensitive synthetic input")]
        )
        self.controller.run_peer_analysis(self.case.case_id)
        self.controller.complete_internal_qa(self.case.case_id)
        self.controller.complete_human_review(
            self.case.case_id, "Named reviewer", approved=True
        )
        self.controller.set_recipient(
            self.case.case_id, "Named recipient", "attorney"
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "release.json"
            with self.assertRaises(PermissionError):
                self.controller.build_release(self.case.case_id, destination)
            self.controller.authorize_recipient_transfer(
                self.case.case_id, True, "Test operator"
            )
            self.controller.build_release(self.case.case_id, destination)
            self.assertTrue(destination.is_file())
        self.controller.release_to_named_recipient(self.case.case_id)
        self.assertEqual(
            CaseLifecycle.RELEASED_TO_NAMED_RECIPIENT, self.case.lifecycle
        )


if __name__ == "__main__":
    unittest.main()
