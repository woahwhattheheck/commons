"""Compatibility test entry point; the suite is split for focused review."""

from .test_core import TeamingConversionCoreTests
from .test_security import TeamingConversionSecurityTests

__all__ = ["TeamingConversionCoreTests", "TeamingConversionSecurityTests"]
