import unittest

from coordination import outbound_delivery_truth as m
from test_outbound_delivery_truth import event, legacy_packet, packet


class ProviderSubmissionObservedTruthTests(unittest.TestCase):
    def test_real_provider_submission_without_events_is_observed(self):
        artifact = m.compile_delivery_truth(packet())
        self.assertEqual(artifact["delivery_state"], "PROVIDER_SUBMITTED_PENDING_DELIVERY")
        self.assertTrue(artifact["collision_projection"]["provider_submission_observed"])

    def test_legacy_local_sent_without_events_is_not_provider_observed(self):
        artifact = m.compile_delivery_truth(legacy_packet())
        self.assertEqual(artifact["delivery_state"], "DELIVERY_UNKNOWN")
        self.assertFalse(artifact["collision_projection"]["provider_submission_observed"])

    def test_legacy_local_sent_with_late_hard_failure_is_not_provider_observed(self):
        artifact = m.compile_delivery_truth(legacy_packet([event()]))
        self.assertEqual(artifact["delivery_state"], "DELIVERY_FAILED")
        self.assertFalse(artifact["collision_projection"]["provider_submission_observed"])

    def test_legacy_local_sent_with_late_delivery_evidence_is_not_provider_observed(self):
        delivered = event(
            kind="PROVIDER_DELIVERY_CONFIRMATION",
            action="delivered",
            status="2.0.0",
            diagnostic="synthetic retained delivery confirmation",
        )
        artifact = m.compile_delivery_truth(legacy_packet([delivered]))
        self.assertEqual(artifact["delivery_state"], "DELIVERED_EVIDENCE")
        self.assertFalse(artifact["collision_projection"]["provider_submission_observed"])


if __name__ == "__main__":
    unittest.main()
