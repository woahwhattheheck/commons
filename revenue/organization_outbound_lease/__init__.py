"""Atomic organization-wide outbound lease.

Internal coordination only. This package never authorizes or performs an external send.
The public acquire surface installs a fixed-host pressure-verifier trust boundary before
exporting either package-level or direct-core acquisition.
"""

from pathlib import Path

from . import core as _core
from .stores import FileLeaseStore, GitHubContentsLeaseStore, StoreConflict, StoreUncertain


_LOCAL_REFERENCE_ACQUIRE_METHODS = (
    "get_active",
    "get_outcome",
    "create_active",
    "_read",
    "_create",
    "_org_lock",
    "_generation",
)
_LOCAL_REFERENCE_ACQUIRE_IMPLS = {
    name: getattr(FileLeaseStore, name) for name in _LOCAL_REFERENCE_ACQUIRE_METHODS
}
_LOCAL_REFERENCE_PROTECTED_CLASS_NAMES = _LOCAL_REFERENCE_ACQUIRE_METHODS + (
    "root",
    "active",
    "outcomes",
    "__getattribute__",
    "__setattr__",
    "__getattr__",
)
_LOCAL_REFERENCE_BASE_FORBIDDEN_NAMES = (
    "root",
    "active",
    "outcomes",
    "__getattribute__",
    "__setattr__",
    "__getattr__",
)


def _mechanically_local_reference_store(store):
    """Return whether verifier injection is confined to the local reference engine.

    A mere ``isinstance(FileLeaseStore)`` check is not an authority boundary: a
    subclass can delegate the store protocol to a production backend, and an exact
    FileLeaseStore instance can replace methods through its instance dictionary.
    The test seam therefore accepts only the unmodified local acquisition call graph.
    Terminal-only subclass behavior (for example a lost DELETE response simulator)
    remains usable because it cannot participate in acquire.
    """
    if not isinstance(store, FileLeaseStore):
        return False

    # Catch later monkeypatches to the base reference class itself, not just subclass
    # overrides. These attributes were absent or snapshotted when this facade loaded.
    if any(name in FileLeaseStore.__dict__ for name in _LOCAL_REFERENCE_BASE_FORBIDDEN_NAMES):
        return False
    for name, expected in _LOCAL_REFERENCE_ACQUIRE_IMPLS.items():
        if getattr(FileLeaseStore, name, None) is not expected:
            return False

    cls = type(store)
    for layer in cls.__mro__:
        if layer is FileLeaseStore:
            break
        if any(name in layer.__dict__ for name in _LOCAL_REFERENCE_PROTECTED_CLASS_NAMES):
            return False
    else:
        return False

    instance_dict = getattr(store, "__dict__", {})
    if any(name in instance_dict for name in _LOCAL_REFERENCE_ACQUIRE_METHODS):
        return False

    # The inherited implementation must still resolve to the exact reference methods.
    for name, expected in _LOCAL_REFERENCE_ACQUIRE_IMPLS.items():
        if getattr(cls, name, None) is not expected:
            return False

    concrete_path_type = type(Path("."))
    root = getattr(store, "root", None)
    active = getattr(store, "active", None)
    outcomes = getattr(store, "outcomes", None)
    if not all(type(value) is concrete_path_type for value in (root, active, outcomes)):
        return False
    if active != root / "active" or outcomes != root / "outcomes":
        return False
    return True


def _install_trusted_acquire(untrusted_acquire):
    def trusted_acquire(store, request, *, lease_nonce_key, pressure_verifier=None):
        """Acquire under the pinned verifier, with one mechanically local test seam.

        Production callers cannot select verifier identity. ``pressure_verifier`` is
        accepted only when the store retains the exact filesystem-reference acquire
        implementation; subclass/proxy/delegated or instance-rebound stores fail
        before the underlying acquire function performs any store I/O.
        """
        if pressure_verifier is None:
            from .trust import load_pressure_verifier
            verifier = load_pressure_verifier()
        else:
            if not _mechanically_local_reference_store(store):
                raise ValueError(
                    "caller-supplied pressure verifier is forbidden for production stores"
                )
            verifier = pressure_verifier
        return untrusted_acquire(
            store,
            request,
            pressure_verifier=verifier,
            lease_nonce_key=lease_nonce_key,
        )
    trusted_acquire.__name__ = "acquire_lease"
    trusted_acquire.__qualname__ = "acquire_lease"
    trusted_acquire.__doc__ = "Acquire one organization lease under the pinned pressure trust root."
    return trusted_acquire


# Patch the core symbol itself before exporting it. Python loads this package initializer
# before satisfying `import revenue.organization_outbound_lease.core`, so direct supported
# core imports receive the hardened wrapper rather than the raw verifier-parameter function.
_core.acquire_lease = _install_trusted_acquire(_core.acquire_lease)
del _install_trusted_acquire

READY_STATE = _core.READY_STATE
TERMINAL_STATES = _core.TERMINAL_STATES
RsaPublicKey = _core.RsaPublicKey
acquire_lease = _core.acquire_lease
canonical_json = _core.canonical_json
finalize_lease = _core.finalize_lease
fingerprint_organization = _core.fingerprint_organization
holder_capability_commitment = _core.holder_capability_commitment
normalize_organization_fingerprint = _core.normalize_organization_fingerprint
verify_lease_document = _core.verify_lease_document
verify_outcome_document = _core.verify_outcome_document
verify_pressure_attestation = _core.verify_pressure_attestation

__all__ = [
    "READY_STATE",
    "TERMINAL_STATES",
    "RsaPublicKey",
    "FileLeaseStore",
    "GitHubContentsLeaseStore",
    "StoreConflict",
    "StoreUncertain",
    "acquire_lease",
    "canonical_json",
    "finalize_lease",
    "fingerprint_organization",
    "holder_capability_commitment",
    "normalize_organization_fingerprint",
    "verify_lease_document",
    "verify_outcome_document",
    "verify_pressure_attestation",
]
