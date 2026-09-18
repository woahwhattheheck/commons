import unittest

from revenue.outbound_collision_guard import acquire, release_unsent, verify


INTENT = {
    "counterparty_key": "example.com",
    "route_key": "email:sales@example.com",
    "thread_key": "gmail:abc123",
    "purpose_key": "paid-workshare:freight-qa",
}
CLAIMANT = {"claimant_id": "astra-z", "session_id": "same-second"}
NOW = "2026-09-17T03:15:00Z"


class ReleaseBoundaryTests(unittest.TestCase):
    def test_same_second_release_is_valid_zero_duration_terminal(self):
        claimed = acquire(intent=INTENT, claimant=CLAIMANT, now=NOW, ttl_s=600)
        released = release_unsent(lease=claimed["lease"], claimant=CLAIMANT, now=NOW)
        self.assertEqual(released["state"], "RELEASED_UNSENT")
        self.assertEqual(released["lease"]["taken_at"], NOW)
        self.assertEqual(released["lease"]["expires_at"], NOW)
        self.assertTrue(verify(released))


if __name__ == "__main__":
    unittest.main()
