"""Synthetic ChartTrace fixtures. No real records. No live model calls."""

from charttrace.fixtures.oracle import (
    CASE_ID,
    ORACLE_VERSION,
    STRUCTURAL,
    SyntheticOracle,
    build_oracle,
)

__all__ = (
    "CASE_ID",
    "ORACLE_VERSION",
    "STRUCTURAL",
    "SyntheticOracle",
    "build_oracle",
)
