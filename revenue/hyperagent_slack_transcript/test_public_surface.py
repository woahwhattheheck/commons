from __future__ import annotations

import unittest

from revenue.hyperagent_slack_transcript import (
    TranscriptProjector as PackageProjector,
    project_fixture as package_project_fixture,
)
from revenue.hyperagent_slack_transcript.adapter import (
    TranscriptProjector as AdapterProjector,
    project_fixture as adapter_project_fixture,
)
from revenue.hyperagent_slack_transcript.stateful import (
    TranscriptProjector as StatefulProjector,
    project_fixture as stateful_project_fixture,
)


class PublicSurfaceTests(unittest.TestCase):
    def test_all_public_surfaces_share_canonical_projector(self):
        self.assertIs(AdapterProjector, PackageProjector)
        self.assertIs(StatefulProjector, PackageProjector)
        self.assertIs(adapter_project_fixture, package_project_fixture)
        self.assertIs(stateful_project_fixture, package_project_fixture)


if __name__ == "__main__":
    unittest.main()
