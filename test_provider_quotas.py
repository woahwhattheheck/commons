#!/usr/bin/env python3
"""Corrected free-compute caps + GitLab/Woodpecker configs call the shared walk."""
from __future__ import annotations

import json
import os
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()


class ProviderQuotas(unittest.TestCase):
    def test_caps_are_not_unlimited(self):
        data = json.loads(read("ci/provider_quotas.json"))
        roads = {row["road"]: row for row in data["roads"]}
        cirrus = roads["Cirrus CI"]
        gitlab = roads["GitLab CI"]
        wood = roads["Codeberg/Woodpecker"]
        fly = roads["Fly.io"]
        self.assertEqual(cirrus["state"], "UNMEASURED")
        self.assertIn("50 compute credits", cirrus["free_quota"])
        self.assertIn("not unlimited", cirrus["free_quota"])
        self.assertIn("2h", cirrus["per_job_ceiling"])
        self.assertEqual(cirrus["config"], ".cirrus.yml")
        self.assertEqual(gitlab["state"], "UNMEASURED")
        self.assertIn("400 compute-min", gitlab["free_quota"])
        self.assertIn("not generic unlimited", gitlab["free_quota"])
        self.assertEqual(gitlab["config"], ".gitlab-ci.yml")
        self.assertIn("ONBOARDING", wood["state"])
        self.assertEqual(wood["config"], ".woodpecker.yml")
        self.assertEqual(fly["state"], "DEAD/EXCLUDED")

    def test_shared_header_census_is_the_walk(self):
        gitlab = read(".gitlab-ci.yml")
        wood = read(".woodpecker.yml")
        cirrus = read(".cirrus.yml")
        gha = read(".github/workflows/header-census.yml")
        for text in (gitlab, wood, cirrus, gha):
            self.assertIn("host_offload/header_census.py", text)
            self.assertNotIn("DEPTH", text)
        self.assertIn("400 compute minutes", gitlab)
        self.assertIn("Not unlimited", gitlab)
        self.assertIn("UNMEASURED/ONBOARDING", wood)
        self.assertIn("Not unlimited", cirrus)
        self.assertIn("timeout_in: 20m", cirrus)
        self.assertIn(".gitlab-ci.yml", gha)
        self.assertIn(".woodpecker.yml", gha)

    def test_resources_encode_caps(self):
        html = read("resources.html")
        self.assertIn("ci/provider_quotas.json", html)
        self.assertIn(".gitlab-ci.yml", html)
        self.assertIn(".woodpecker.yml", html)
        self.assertIn("50 compute credits", html)
        self.assertIn("400 compute-min", html)
        self.assertNotIn("second unlimited OSS", html)
        self.assertIn("DEAD/EXCLUDED", html)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
