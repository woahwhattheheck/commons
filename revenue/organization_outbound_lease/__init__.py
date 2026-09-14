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
_LOCAL_REFERENCE_PROTECTED_CLASS_NAMES = _LOCAL_REFERENCE_ACQUIRE_METHODS + (
    "root",
    "active",
    "outcomes",
    "__dict__",
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


def _build_local_reference_checker():
    """Freeze the local-reference identity used by the public acquire wrapper.

    The checker is built once while this facade is imported.  Its authoritative
    class, path type, protected names, and raw method descriptors live in closure
    cells rather than mutable module globals.  Later rebinding of facade helpers or
    exported symbols therefore cannot widen the verifier-injection seam.
    """
    reference_store_type = FileLeaseStore
    concrete_path_type = type(Path("."))
    acquire_names = tuple(_LOCAL_REFERENCE_ACQUIRE_METHODS)
    protected_names = frozenset(_LOCAL_REFERENCE_PROTECTED_CLASS_NAMES)
    base_forbidden_names = frozenset(_LOCAL_REFERENCE_BASE_FORBIDDEN_NAMES)
    reference_dict = type.__getattribute__(reference_store_type, "__dict__")
    acquire_impls = tuple((name, reference_dict[name]) for name in acquire_names)

    def resolve_raw(mro, name):
        for layer in mro:
            layer_dict = type.__getattribute__(layer, "__dict__")
            if name in layer_dict:
                return layer_dict[name]
        return None

    def mechanically_local_reference_store(store):
        """Return whether verifier injection stays inside the frozen local engine."""
        cls = type(store)
        mro = type.__getattribute__(cls, "__mro__")
        try:
            reference_index = mro.index(reference_store_type)
        except ValueError:
            return False

        # Inspect raw class dictionaries through type.__getattribute__, so a hostile
        # metaclass cannot lie about MRO/class attributes during this decision.
        current_reference_dict = type.__getattribute__(reference_store_type, "__dict__")
        if any(name in current_reference_dict for name in base_forbidden_names):
            return False
        for name, expected in acquire_impls:
            if current_reference_dict.get(name) is not expected:
                return False

        # Subclasses may customize terminal-only behavior, but nothing that can run
        # during acquire (including attribute interception or local path state).  A
        # subclass-level __dict__ descriptor is also forbidden because it could hide
        # rebound acquire methods from the instance-storage observation below.
        for layer in mro[:reference_index]:
            layer_dict = type.__getattribute__(layer, "__dict__")
            if any(name in layer_dict for name in protected_names):
                return False

        try:
            instance_dict = object.__getattribute__(store, "__dict__")
        except AttributeError:
            return False
        if any(name in instance_dict for name in acquire_names):
            return False

        # Resolve the raw descriptors ourselves instead of using getattr(cls, ...),
        # which a custom metaclass can intercept.
        for name, expected in acquire_impls:
            if resolve_raw(mro, name) is not expected:
                return False

        root = instance_dict.get("root")
        active = instance_dict.get("active")
        outcomes = instance_dict.get("outcomes")
        if not all(type(value) is concrete_path_type for value in (root, active, outcomes)):
            return False
        if active != root / "active" or outcomes != root / "outcomes":
            return False
        return True

    return (
        mechanically_local_reference_store,
        reference_store_type,
        concrete_path_type,
        acquire_impls,
    )


(
    _LOCAL_REFERENCE_CHECKER,
    _LOCAL_REFERENCE_STORE_TYPE,
    _LOCAL_REFERENCE_PATH_TYPE,
    _LOCAL_REFERENCE_ACQUIRE_IMPLS,
) = _build_local_reference_checker()
del _build_local_reference_checker


def _mechanically_local_reference_store(store):
    """Diagnostic view of the frozen local-reference checker used by acquire."""
    return _LOCAL_REFERENCE_CHECKER(store)


def _install_trusted_acquire(
    untrusted_acquire,
    local_reference_checker=_LOCAL_REFERENCE_CHECKER,
):
    # `local_reference_checker` is captured by the installed wrapper.  Do not resolve
    # the mutable module-global diagnostic helper when deciding verifier authority.
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
            if not local_reference_checker(store):
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
