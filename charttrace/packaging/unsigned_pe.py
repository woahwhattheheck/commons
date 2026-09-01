"""Retired synthetic PE compatibility tombstone.

The old 1,536-byte ExitProcess image was not ChartTrace and must never be
accepted as build, launch, or release evidence.  The import remains only to
make stale callers fail explicitly.
"""

from pathlib import Path
from typing import Dict

ARTIFACT_LABEL = "UNSIGNED_SYNTHETIC"
SIGNING_STATE = "unsigned"
SYNTHETIC_PE_GENERATION_ENABLED = False
RETIREMENT_REASON = "stub-was-not-the-frozen-charttrace-application"


def build_unsigned_pe_bytes() -> bytes:
    """Reject synthetic executable generation."""
    raise RuntimeError(
        "Synthetic PE generation is retired; build pinned ChartTrace.spec."
    )


def write_unsigned_pe(dest: Path) -> Dict[str, object]:
    """Reject synthetic executable writes."""
    del dest
    raise RuntimeError(
        "Synthetic PE output is retired; supply the frozen ChartTrace.exe."
    )

