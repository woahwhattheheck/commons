from . import engine as _engine
from .boundary import strict_json_loads

# Supported package import installs the hardened byte parser into the retained
# commercial engine without changing its state-machine or receipt semantics.
_engine.strict_json_loads = strict_json_loads

AUTHORITY = _engine.AUTHORITY
ContractError = _engine.ContractError
CURRENT_FOR_OWNER_USE = _engine.CURRENT_FOR_OWNER_USE
EXPIRED_REQUOTE_REQUIRED = _engine.EXPIRED_REQUOTE_REQUIRED
HOLD_NO_VALIDITY_BASIS = _engine.HOLD_NO_VALIDITY_BASIS
HOLD_SOURCE_DRIFT = _engine.HOLD_SOURCE_DRIFT
SUPERSEDED = _engine.SUPERSEDED
canonical_bytes = _engine.canonical_bytes
compile_at = _engine.compile_at
compile_current = _engine.compile_current
verify_at = _engine.verify_at
verify_current = _engine.verify_current

__all__ = [
    "AUTHORITY",
    "ContractError",
    "CURRENT_FOR_OWNER_USE",
    "EXPIRED_REQUOTE_REQUIRED",
    "HOLD_NO_VALIDITY_BASIS",
    "HOLD_SOURCE_DRIFT",
    "SUPERSEDED",
    "canonical_bytes",
    "compile_at",
    "compile_current",
    "strict_json_loads",
    "verify_at",
    "verify_current",
]
