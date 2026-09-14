"""Aggregate DCSA carrier hostile suites for direct module execution."""

from .test_contracts import StrictInputTests
from .test_qualification import QualificationTests
from .test_current import CurrentBoundaryTests
from .test_rendering import RenderingTests
from .test_custody import FileCustodyTests
from .test_artifacts import RepositoryArtifactTests
from .test_cli_surface import CliTests

__all__ = [
    "StrictInputTests",
    "QualificationTests",
    "CurrentBoundaryTests",
    "RenderingTests",
    "FileCustodyTests",
    "RepositoryArtifactTests",
    "CliTests",
]
