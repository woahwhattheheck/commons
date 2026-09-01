"""Synthetic ChartTrace fixtures. No real records. No live model calls."""

from charttrace.fixtures import oracle as _oracle
from charttrace.fixtures.oracle_overlay import (
    CANARY_PHI,
    GROUNDING_VERSION,
    NEGATIVE_CONTROL_IDS,
    ORACLE,
    OVERLAY_EXPORTS,
    PROMPT_INJECTION,
    SCHEMA_VERSION,
    SCOPE_STATEMENT,
    SIGNAL_IDS,
    TOOL_VERSION,
    UNIQUE_DOC_PAGES,
)

for _name in OVERLAY_EXPORTS:
    setattr(_oracle, _name, globals()[_name])

from charttrace.fixtures.builder import FixtureCase, build_fixture_case
from charttrace.fixtures.oracle import (
    CASE_ID,
    DOCUMENT_PLAN,
    FORBIDDEN_CLAIMS,
    INJECTION_TEXT,
    ORACLE_VERSION,
    STRUCTURAL,
    SyntheticOracle,
    build_oracle,
)

__all__ = (
    "CANARY_PHI",
    "CASE_ID",
    "DOCUMENT_PLAN",
    "FORBIDDEN_CLAIMS",
    "FixtureCase",
    "GROUNDING_VERSION",
    "INJECTION_TEXT",
    "NEGATIVE_CONTROL_IDS",
    "ORACLE",
    "ORACLE_VERSION",
    "PROMPT_INJECTION",
    "SCHEMA_VERSION",
    "SCOPE_STATEMENT",
    "SIGNAL_IDS",
    "STRUCTURAL",
    "SyntheticOracle",
    "TOOL_VERSION",
    "UNIQUE_DOC_PAGES",
    "build_fixture_case",
    "build_oracle",
)
