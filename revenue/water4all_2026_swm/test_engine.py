"""Aggregate the complete Water4All readiness hostile suite."""

import unittest

from .test_ready_sources import ReadyPathTests, SourceAuthorityTests
from .test_consortium import ConsortiumTests
from .test_evidence_cli import ApplicantAndEvidenceTests, ParsingAndCliTests
from .test_red_recovery import RedRecoveryTests

__all__ = [
    "ReadyPathTests",
    "SourceAuthorityTests",
    "ConsortiumTests",
    "ApplicantAndEvidenceTests",
    "ParsingAndCliTests",
    "RedRecoveryTests",
]

if __name__ == "__main__":
    unittest.main()
