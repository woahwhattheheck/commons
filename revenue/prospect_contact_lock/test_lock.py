"""Preserve the landed byte-level CAS hostile corpus against the private core.

Production callers import :mod:`revenue.prospect_contact_lock.lock`.  The
historical state-machine tests intentionally exercise the byte-preserved private
engine so transport faults remain deterministic without reopening a production
transport-injection API.
"""
from . import _core
from . import _legacy_test_lock as _legacy

# The preserved test module imported the historical public `lock` symbol. Rebind
# only its module-local test dependency to the now-private engine before any
# TestCase setUp executes.
_legacy.mod = _core

DATE = _legacy.DATE
FakeTransport = _legacy.FakeTransport
ProspectContactLockTests = _legacy.ProspectContactLockTests

__all__ = ["DATE", "FakeTransport", "ProspectContactLockTests"]
