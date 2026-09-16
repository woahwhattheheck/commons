"""Aggregate the complete Water4All readiness hostile suite."""

import unittest

from .test_ready_sources import ReadyPathTests, SourceAuthorityTests
from .test_consortium import ConsortiumTests
from .test_evidence_cli import ApplicantAndEvidenceTests, ParsingAndCliTests
from .test_security_regressions import AuthorityBoundaryRegressionTests, ConsortiumAndPartnerRegressionTests


class PackagePublicApiTests(unittest.TestCase):
    def test_engine_reexports_source_sealing_helpers(self):
        import revenue.water4all_2026_swm as pkg
        from revenue.water4all_2026_swm import engine

        self.assertIs(pkg.seal_source, engine.seal_source)
        self.assertIs(pkg.source_fact_commitment, engine.source_fact_commitment)
        self.assertIs(pkg.strict_json_loads, engine.strict_json_loads)
        self.assertTrue(callable(engine.seal_source))
        self.assertTrue(callable(engine.source_fact_commitment))
        self.assertTrue(callable(engine.strict_json_loads))

    def test_compile_at_cannot_mint_current_packets(self):
        from .test_support import T0, ReadinessError, base_valid, compile_at

        with self.assertRaisesRegex(ReadinessError, "cannot mint CURRENT"):
            compile_at(base_valid(), T0, "CURRENT")


__all__ = [
    "PackagePublicApiTests",
    "ReadyPathTests",
    "SourceAuthorityTests",
    "ConsortiumTests",
    "ApplicantAndEvidenceTests",
    "ParsingAndCliTests",
    "AuthorityBoundaryRegressionTests",
    "ConsortiumAndPartnerRegressionTests",
]

if __name__ == "__main__":
    unittest.main()
