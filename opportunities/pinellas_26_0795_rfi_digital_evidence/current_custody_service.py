from __future__ import annotations

import copy
from typing import Any, Protocol

from custody_reference import AuthoritySnapshot, CustodyError, Evidence


class HostTrustProvider(Protocol):
    """Host-owned retention boundary for current custody state.

    The provider is installed by the embedding service, not supplied on an
    individual custody operation.  This module intentionally does not define
    authentication, credentials, or admission policy for that host boundary.
    """

    def retained_custody_witness(self, case_id: str, object_id: str) -> dict[str, Any]: ...

    def retain_custody_witness(
        self, case_id: str, object_id: str, witness: dict[str, Any]
    ) -> None: ...

    def current_authority_snapshot(
        self, case_id: str, object_id: str
    ) -> AuthoritySnapshot: ...

    def archived_authority_snapshot(
        self, case_id: str, object_id: str, root: str
    ) -> AuthoritySnapshot: ...


class CurrentCustodyService:
    """Current-positive custody API backed by one host-installed trust provider.

    Low-level ``Evidence`` methods are useful deterministic replay primitives,
    but caller-supplied witnesses, snapshots, or roots are not current trust.
    Current operations flow through this service, which captures the provider's
    bound methods at construction and never accepts those trust-bearing values
    from an operation caller.
    """

    def __init__(self, provider: HostTrustProvider):
        methods = {
            "retained_custody_witness": getattr(provider, "retained_custody_witness", None),
            "retain_custody_witness": getattr(provider, "retain_custody_witness", None),
            "current_authority_snapshot": getattr(provider, "current_authority_snapshot", None),
            "archived_authority_snapshot": getattr(provider, "archived_authority_snapshot", None),
        }
        if any(not callable(method) for method in methods.values()):
            raise CustodyError("host trust provider contract incomplete")
        # Capture the host integration once. Later attribute replacement on the
        # provider object cannot silently redirect this service's trust road.
        self._retained_witness = methods["retained_custody_witness"]
        self._retain_witness = methods["retain_custody_witness"]
        self._current_snapshot = methods["current_authority_snapshot"]
        self._archived_snapshot = methods["archived_authority_snapshot"]

    @staticmethod
    def _identity(evidence: Evidence) -> tuple[str, str]:
        if type(evidence) is not Evidence:
            raise CustodyError("Evidence instance required")
        return evidence.case_id, evidence.object_id

    def _snapshot_current(self, evidence: Evidence) -> AuthoritySnapshot:
        case_id, object_id = self._identity(evidence)
        snapshot = self._current_snapshot(case_id, object_id)
        if type(snapshot) is not AuthoritySnapshot:
            raise CustodyError("host current authority snapshot unavailable")
        return snapshot

    @staticmethod
    def _referenced_authority_roots(evidence: Evidence) -> set[str]:
        roots: set[str] = set()
        for event in evidence.events:
            if type(event) is not dict:
                continue
            data = event.get("data")
            if type(data) is not dict:
                continue
            root = data.get("authority_snapshot_root")
            if type(root) is str:
                roots.add(root)
        return roots

    def verify_current(self, evidence: Evidence) -> dict[str, Any]:
        case_id, object_id = self._identity(evidence)
        expected_witness = copy.deepcopy(self._retained_witness(case_id, object_id))
        snapshots: dict[str, AuthoritySnapshot] = {}
        for root in self._referenced_authority_roots(evidence):
            snapshot = self._archived_snapshot(case_id, object_id, root)
            if type(snapshot) is not AuthoritySnapshot or snapshot.root != root:
                raise CustodyError("host archived authority snapshot unavailable or root-mismatched")
            snapshots[root] = snapshot
        return evidence.verify(
            expected_witness=expected_witness,
            authority_snapshots=snapshots,
            trusted_snapshot_roots=set(snapshots),
        )

    def _retain_candidate(self, candidate: Evidence) -> None:
        case_id, object_id = self._identity(candidate)
        self._retain_witness(case_id, object_id, copy.deepcopy(candidate.witness()))

    @staticmethod
    def _replace_state(target: Evidence, candidate: Evidence) -> None:
        target.original_sha256 = candidate.original_sha256
        target.accepted = candidate.accepted
        target.legal_hold = candidate.legal_hold
        target.destroyed = candidate.destroyed
        target.events = copy.deepcopy(candidate.events)

    def _mutate_verified(self, evidence: Evidence, mutation) -> Any:
        self.verify_current(evidence)
        candidate = copy.deepcopy(evidence)
        result = mutation(candidate)
        # Retain the new witness before exposing the local state transition. If
        # the host store refuses the write, the caller's Evidence stays intact.
        self._retain_candidate(candidate)
        self._replace_state(evidence, candidate)
        return copy.deepcopy(result)

    def submit_current(
        self, *, case_id: str, object_id: str, original: bytes, actor: str, at: str
    ) -> Evidence:
        candidate = Evidence.submit(
            case_id=case_id, object_id=object_id, original=original, actor=actor, at=at
        )
        self._retain_candidate(candidate)
        return candidate

    def view_current(self, evidence: Evidence, *, actor: str, at: str, purpose: str) -> None:
        self._mutate_verified(
            evidence, lambda candidate: candidate.view(actor=actor, at=at, purpose=purpose)
        )

    def classify_current(
        self, evidence: Evidence, *, actor: str, at: str, status: str, confidential: bool
    ) -> None:
        self._mutate_verified(
            evidence,
            lambda candidate: candidate.classify(
                actor=actor, at=at, status=status, confidential=confidential
            ),
        )

    def accept_current(self, evidence: Evidence, *, actor: str, at: str) -> None:
        self._mutate_verified(
            evidence, lambda candidate: candidate.accept(actor=actor, at=at)
        )

    def replace_original_current(
        self, evidence: Evidence, *, new_bytes: bytes, actor: str, at: str
    ) -> None:
        self._mutate_verified(
            evidence,
            lambda candidate: candidate.replace_original(
                new_bytes=new_bytes, actor=actor, at=at
            ),
        )

    def set_hold_current(
        self, evidence: Evidence, *, actor: str, at: str, authority_evidence_id: str
    ) -> None:
        def mutate(candidate: Evidence) -> None:
            snapshot = self._snapshot_current(candidate)
            candidate.set_hold(
                actor=actor,
                at=at,
                snapshot=snapshot,
                trusted_snapshot_root=snapshot.root,
                authority_evidence_id=authority_evidence_id,
            )

        self._mutate_verified(evidence, mutate)

    def destroy_current(
        self,
        evidence: Evidence,
        *,
        actor: str,
        at: str,
        retention_evidence_id: str,
        notice_evidence_id: str,
        approval_evidence_ids: list[str],
        destruction_authority_evidence_id: str,
    ) -> dict[str, Any]:
        def mutate(candidate: Evidence) -> dict[str, Any]:
            snapshot = self._snapshot_current(candidate)
            return candidate.destroy(
                actor=actor,
                at=at,
                snapshot=snapshot,
                trusted_snapshot_root=snapshot.root,
                retention_evidence_id=retention_evidence_id,
                notice_evidence_id=notice_evidence_id,
                approval_evidence_ids=approval_evidence_ids,
                destruction_authority_evidence_id=destruction_authority_evidence_id,
            )

        return self._mutate_verified(evidence, mutate)
