"""Synthetic ChartTrace fixtures. No PHI. Generated at test time; not real records."""

from .oracle import ORACLE, SCHEMA_VERSION, TOOL_VERSION
from .builder import build_fixture_case, FixtureCase

__all__ = ["ORACLE", "SCHEMA_VERSION", "TOOL_VERSION", "build_fixture_case", "FixtureCase"]
