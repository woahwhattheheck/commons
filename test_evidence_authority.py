"""Root unittest enrollment for the evidence-authority kernel.

Existing Commons unittest discovery already collects test_*.py at the
repository root. This wrapper adds the kernel hostiles to that surface
without a new Actions workflow.
"""

from tools.evidence_authority.test_hostiles import *  # noqa: F401,F403
