"""Current-authority cross-site clinical fill tech-transfer evidence gate.

Deterministic explicit-time replay is intentionally not re-exported here; use
the explicit ``historical`` test/replay namespace when historical authority is
required.
"""

from .engine import (
    TransferError,
    compile_transfer,
    render_markdown,
    verify_report_current,
)

__all__ = [
    "TransferError",
    "compile_transfer",
    "render_markdown",
    "verify_report_current",
]
