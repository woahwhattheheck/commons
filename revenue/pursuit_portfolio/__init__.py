"""Evidence-bound pursuit portfolio allocation.

Top-level package exports are the fixed-host authenticated current-use path.
Deterministic engine/replay helpers and explicit-key test machinery remain in
``core`` and ``current``; they are not production authority roots.
"""
from .core import PortfolioError
from .host import compile_current, verify_current
from .current import load_current_input, read_published_authorized
from .publisher import publish_authorized

__all__ = [
    "PortfolioError",
    "compile_current",
    "load_current_input",
    "publish_authorized",
    "read_published_authorized",
    "verify_current",
]
