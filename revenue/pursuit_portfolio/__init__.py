"""Evidence-bound pursuit portfolio allocation.

Top-level package exports are the authenticated current-use path.  Deterministic
engine/replay helpers remain available from ``revenue.pursuit_portfolio.core``
for tests and historical integrity work, but they are not an authority boundary.
"""
from .core import PortfolioError
from .current import (
    AuthorityKey,
    compile_authorized_current,
    load_authority_key,
    load_current_input,
    read_published_authorized,
    verify_authorized_current,
)
from .publisher import publish_authorized

__all__ = [
    "AuthorityKey",
    "PortfolioError",
    "compile_authorized_current",
    "load_authority_key",
    "load_current_input",
    "publish_authorized",
    "read_published_authorized",
    "verify_authorized_current",
]
