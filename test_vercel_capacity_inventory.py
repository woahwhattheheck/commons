import json
import unittest

from host.vercel_capacity_inventory import _json_bytes, build_snapshot


BASE = {
    "observed_at": "2026-09-01T21:58:58Z",
    "source_commit": "5abd1b8259cbb307c33e3e9cbcfc810a36585c92",
    "team_plans": ["hobby"],
    "project_count": 0,
    "deployments_queried": False,
    "deployment_count": None,
}


class VercelCapacityInventoryTests(unittest.TestCase):
    def build(self, **changes):
        values = dict(BASE)
        values.update(changes)
        return build_snapshot(**values)

    def test_zero_project_result_fails_closed(self):
        value = self.build()
        self.assertEqual(value["consumer"]["decision"], "NO_PROJECT_READY")
        self.assertEqual(value["aggregate"]["deployment_routes_ready"], 0)
        self.assertEqual(value["aggregate"]["deployment_query"], "SKIPPED_NO_PROJECTS")
        self.assertIsNone(value["aggregate"]["deployments_observed"])

    def test_connector_success_is_separate_from_project_capacity(self):
        value = self.build()
        self.assertTrue(value["truth"]["connector_read_succeeded"])
        self.assertTrue(value["truth"]["zero_projects_is_not_zero_account_capacity"])
        self.assertEqual(value["aggregate"]["projects"], 0)

    def test_private_identifiers_are_never_fields(self):
        payload = json.dumps(self.build(), sort_keys=True)
        for forbidden in ("team_id", "team_slug", "team_name", "project_id", "account_id"):
            self.assertNotIn(f'"{forbidden}"', payload)

    def test_no_mutation_or_secret_claim(self):
        truth = self.build()["truth"]
        for field in (
            "deployment_created",
            "project_mutated",
            "configuration_mutated",
            "environment_read",
            "domain_read",
            "secret_read",
        ):
            self.assertFalse(truth[field])

    def test_projects_require_deployment_enumeration(self):
        with self.assertRaises(ValueError):
            self.build(project_count=1)

    def test_project_route_ready_after_enumeration(self):
        value = self.build(
            project_count=2,
            deployments_queried=True,
            deployment_count=3,
        )
        self.assertEqual(value["consumer"]["decision"], "PROJECT_ROUTE_READY")
        self.assertEqual(value["aggregate"]["deployment_routes_ready"], 2)
        self.assertEqual(value["aggregate"]["deployments_observed"], 3)

    def test_zero_projects_rejects_fake_deployment_count(self):
        with self.assertRaises(ValueError):
            self.build(deployment_count=0)

    def test_counts_reject_boolean_and_negative(self):
        for bad in (-1, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.build(project_count=bad)

    def test_invalid_sha_and_timestamp_fail(self):
        with self.assertRaises(ValueError):
            self.build(source_commit="main")
        with self.assertRaises(ValueError):
            self.build(observed_at="2026-09-01T21:58:58")

    def test_plan_labels_are_aggregate_safe(self):
        self.assertEqual(self.build(team_plans=["pro", "hobby", "hobby"])["aggregate"]["team_plan_counts"], {"hobby": 2, "pro": 1})
        with self.assertRaises(ValueError):
            self.build(team_plans=["woahwhattheheck's projects"])

    def test_output_is_deterministic(self):
        first = self.build(team_plans=["pro", "hobby"])
        second = self.build(team_plans=["hobby", "pro"])
        self.assertEqual(_json_bytes(first), _json_bytes(second))


if __name__ == "__main__":
    unittest.main()
