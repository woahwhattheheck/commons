"""Atomic organization-wide outbound lease.

Internal coordination only. This package never authorizes or performs an external send.
The public acquire surface installs a fixed-host pressure-verifier trust boundary before
exporting either package-level or direct-core acquisition.
"""

from . import core as _core
from .stores import FileLeaseStore, GitHubContentsLeaseStore, StoreConflict, StoreUncertain


def _install_trusted_acquire(untrusted_acquire):
    def trusted_acquire(store, request, *, lease_nonce_key, pressure_verifier=None):
        """Acquire with a host-pinned verifier for every production store.

        `pressure_verifier` survives only as a deterministic exact local-reference test
        seam. Subclasses are not local-reference authority: they can override the store
        protocol and route writes into a production backend, so verifier injection must
        fail before request parsing or store I/O for every non-exact FileLeaseStore.
        """
        if pressure_verifier is None:
            from .trust import load_pressure_verifier
            verifier = load_pressure_verifier()
        else:
            if type(store) is not FileLeaseStore:
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
