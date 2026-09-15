"""Reload-stable public facade for the NIH SPARK pre-launch baseline.

The byte-exact landed predecessor implementation lives in the private
`_baseline_core` module. Public imports stay on this facade so every ordinary
`importlib.reload(baseline)` generation deterministically re-exports the hardened
retrieval authority instead of reviving the predecessor evaluator/receipt path.
"""

from __future__ import annotations

from . import _baseline_core as _core

# Preserve the complete historical direct-baseline surface, including private
# helpers used by repository tests, while keeping this module's import metadata.
for _name, _value in vars(_core).items():
    if _name.startswith("__") and _name.endswith("__"):
        continue
    globals()[_name] = _value

# These three public entrypoints are intentionally resolved after the core copy on
# every facade generation. retrieval_authority depends only on the private core,
# so this import has no baseline<->authority cycle and is stable under reload.
from .retrieval_authority import (  # noqa: E402
    build_run_receipt,
    evaluate_bundle,
    verify_run_receipt,
)

del _core
del _name
del _value
