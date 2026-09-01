"""Headless-capable application controller and policy enforcement point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from charttrace.legal import (
    ConsentLedger,
    LegalState,
    TRUST_CENTER_VERSION,
    instrument_suite_hash,
)

from .audit import append_receipt
from .cases import CaseLifecycle, CaseRecord
from .evidence import SourceInput, seal_sources, synthetic_peer_output
from .offline_counsel import import_counsel_review
from .paths import PathEgressError, assert_local_filesystem_path
from .storage import LocalStateStore
from .vault import (
    VAULT_MODE,
    VaultError,
    build_envelope,
    initialize_verifier,
    inspect_envelope,
    verify_secret,
)


APP_VERSION = "1.1"
BUILD_LABEL = "UNSIGNED_SYNTHETIC"
SIGNING_STATE = "unsigned"


class ApplicationLockedError(PermissionError):
    pass


class AnalysisBlockedError(PermissionError):
    pass


class ReleaseBlockedError(PermissionError):
    pass


class ChartTraceController:
    """Policy-first controller shared by Tk and headless test clients."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        persist: bool = True,
    ):
        default_dir = Path.home() / "AppData" / "Local" / "ChartTrace"
        self.store = LocalStateStore(Path(data_dir) if data_dir else default_dir)
        self.persist = persist
        self.unlocked = False
        self.operator = ""
        self.consent = ConsentLedger()
        self.cases: Dict[str, CaseRecord] = {}
        self.vault_mode = VAULT_MODE
        self._verifier: Optional[Dict[str, Any]] = None
        self._sealed_envelope: Dict[str, Any] = {}
        if persist:
            self._load_vault_header()

    @property
    def legal_state(self) -> LegalState:
        return self.consent.acceptance_state

    @property
    def analysis_allowed(self) -> bool:
        return self.unlocked and self.consent.current_and_authorized

    def unlock(self, local_secret: str, operator: str = "Local operator") -> None:
        if not local_secret:
            raise ApplicationLockedError("Unlock requires a nonempty local secret.")
        if not operator.strip():
            raise ApplicationLockedError("Operator name is required.")
        try:
            if self._verifier is not None:
                verify_secret(local_secret, self._verifier)
            elif self._sealed_envelope:
                classification = inspect_envelope(self._sealed_envelope)
                if classification.get("legacy_plaintext"):
                    raise VaultError(
                        "Plaintext or unverified state cannot be unlocked."
                    )
                raise VaultError("Vault verifier is missing.")
            else:
                self._verifier = initialize_verifier(local_secret)
        except VaultError as error:
            raise ApplicationLockedError(str(error)) from error
        self.operator = operator.strip()
        self.unlocked = True
        if self.persist:
            self._materialize_consent_only()
            self._save()

    def lock(self) -> None:
        self.unlocked = False
        self.operator = ""

    def accept_legal(self, acknowledgements: Dict[str, bool], accepted_by: str) -> None:
        self.consent.accept(acknowledgements, accepted_by)
        self._revoke_all_transfer_authorizations("terms/authority reacceptance")
        for case in self.cases.values():
            if case.lifecycle in {
                CaseLifecycle.DRAFT,
                CaseLifecycle.HOLD_TERMS_OR_AUTHORITY,
            }:
                case.transition(CaseLifecycle.READY_TO_INGEST)
                append_receipt(
                    case,
                    "LEGAL_READY",
                    json.dumps(
                        {
                            "accepted_suite_hash": instrument_suite_hash(),
                            "accepted_suite_version": TRUST_CENTER_VERSION,
                            "detail": "Current suite and authority accepted.",
                            "signing_state": SIGNING_STATE,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
        self._save()

    def place_authority_hold(self, reason: str) -> None:
        self.consent.place_authority_hold(reason)
        self._revoke_all_transfer_authorizations("authority hold")
        for case in self.cases.values():
            append_receipt(case, "AUTHORITY_HOLD", "Analysis and release gates closed.")
        self._save()

    def clear_authority_hold(self) -> None:
        self.consent.clear_authority_hold()
        self._revoke_all_transfer_authorizations("authority hold cleared")
        for case in self.cases.values():
            append_receipt(
                case,
                "AUTHORITY_HOLD_CLEARED",
                "Fresh legal acceptance is required.",
            )
        self._save()

    def create_case(self, name: str) -> CaseRecord:
        self._require_unlocked()
        if not name.strip():
            raise ValueError("Case name is required.")
        case = CaseRecord(name=name.strip())
        if self.consent.current_and_authorized:
            case.transition(CaseLifecycle.READY_TO_INGEST)
        else:
            case.transition(CaseLifecycle.HOLD_TERMS_OR_AUTHORITY)
        append_receipt(case, "CASE_CREATED", "Local draft created.")
        self.cases[case.case_id] = case
        self._save()
        return case

    def list_cases(self) -> List[CaseRecord]:
        self._require_unlocked()
        return sorted(self.cases.values(), key=lambda case: case.updated_at, reverse=True)

    def secure_ingest(
        self,
        case_id: str,
        sources: Iterable[SourceInput],
    ) -> CaseRecord:
        self._require_analysis_gate("ingest")
        case = self.get_case(case_id)
        if case.lifecycle is not CaseLifecycle.READY_TO_INGEST:
            raise AnalysisBlockedError(
                "Case must be READY_TO_INGEST before secure ingest."
            )
        checked: List[SourceInput] = []
        for source in sources:
            if not isinstance(source, tuple):
                assert_local_filesystem_path(source)
            checked.append(source)
        case.sources = seal_sources(checked)
        case.transition(CaseLifecycle.INGESTED_SEALED)
        append_receipt(
            case,
            "INGESTED_SEALED",
            f"{len(case.sources)} local source(s) hash-sealed.",
        )
        self._save()
        return case

    def run_peer_analysis(self, case_id: str) -> dict:
        self._require_analysis_gate("peer analysis")
        case = self.get_case(case_id)
        if case.lifecycle is not CaseLifecycle.INGESTED_SEALED:
            raise AnalysisBlockedError(
                "Peer analysis requires an INGESTED_SEALED case."
            )
        output = synthetic_peer_output(case.sources)
        case.peer_outputs.append(output)
        case.transition(CaseLifecycle.PEER_ANALYSIS)
        append_receipt(
            case,
            "PEER_ANALYSIS_STARTED",
            "Unsigned synthetic envelope created for internal review.",
        )
        self._save()
        return output

    def complete_internal_qa(self, case_id: str) -> CaseRecord:
        self._require_analysis_gate("internal QA")
        case = self.get_case(case_id)
        if case.lifecycle is CaseLifecycle.PEER_ANALYSIS:
            case.transition(CaseLifecycle.INTERNAL_QA)
        if case.lifecycle is not CaseLifecycle.INTERNAL_QA:
            raise AnalysisBlockedError("Internal QA requires PEER_ANALYSIS.")
        case.transition(CaseLifecycle.HUMAN_RELEASE_REVIEW)
        append_receipt(case, "INTERNAL_QA_COMPLETE", "Sent to mandatory human review.")
        self._save()
        return case

    def complete_human_review(
        self,
        case_id: str,
        reviewer: str,
        approved: bool,
    ) -> CaseRecord:
        self._require_analysis_gate("human release review")
        case = self.get_case(case_id)
        if case.lifecycle is not CaseLifecycle.HUMAN_RELEASE_REVIEW:
            raise ReleaseBlockedError("Case is not in HUMAN_RELEASE_REVIEW.")
        if approved is not True:
            append_receipt(case, "HUMAN_REVIEW_HOLD", "Release was not approved.")
            self._save()
            return case
        if not reviewer.strip():
            raise ReleaseBlockedError("A named human reviewer is required.")
        case.human_reviewed_by = reviewer.strip()
        case.transition(CaseLifecycle.READY_TO_RELEASE)
        append_receipt(case, "HUMAN_REVIEW_APPROVED", "Named human approved release.")
        self._save()
        return case

    def import_offline_counsel_review(
        self,
        case_id: str,
        bundle_path: Path,
    ) -> dict:
        self._require_unlocked()
        case = self.get_case(case_id)
        review = import_counsel_review(bundle_path, case_id)
        prior_lifecycle = case.lifecycle
        prior_hold = self.consent.authority_hold_reason
        append_receipt(
            case,
            "OFFLINE_COUNSEL_REVIEW_IMPORTED",
            (
                "Non-authoritative review record imported; "
                f"claimed_decision={review['claimed_decision']}; "
                "does not approve release or clear a hold."
            ),
        )
        self._save()
        if case.lifecycle is not prior_lifecycle:
            raise RuntimeError("Counsel import must not change lifecycle.")
        if self.consent.authority_hold_reason != prior_hold:
            raise RuntimeError("Counsel import must not clear an authority hold.")
        return review

    def set_recipient(
        self,
        case_id: str,
        recipient: str,
        role: str = "recipient",
    ) -> CaseRecord:
        self._require_unlocked()
        case = self.get_case(case_id)
        old_recipient = case.recipient.recipient
        case.set_recipient(recipient, role)
        if old_recipient != case.recipient.recipient:
            append_receipt(
                case,
                "RECIPIENT_CHANGED",
                "Prior transfer authorization revoked; new authorization required.",
            )
        self._save()
        return case

    def authorize_recipient_transfer(
        self,
        case_id: str,
        affirmative_authorization: bool,
        authorized_by: str,
    ) -> CaseRecord:
        self._require_unlocked()
        case = self.get_case(case_id)
        case.authorize_transfer(
            self.legal_state,
            affirmative_authorization,
            authorized_by,
            TRUST_CENTER_VERSION,
        )
        case.recipient.authorization_epoch = self.consent.authority_epoch
        append_receipt(
            case,
            "TRANSFER_AUTHORIZED",
            "Separate authorization recorded for the current named recipient.",
        )
        self._save()
        return case

    def build_release(self, case_id: str, destination: Path) -> Path:
        self._require_release_gate(case_id)
        case = self.get_case(case_id)
        destination = assert_local_filesystem_path(destination)
        if destination.parent.exists() or destination.parent == destination:
            pass
        try:
            if destination.parent != destination:
                assert_local_filesystem_path(destination.parent)
                destination.parent.mkdir(parents=True, exist_ok=True)
        except PathEgressError:
            raise
        payload = {
            "format": "charttrace-release-v1.1",
            "build_label": BUILD_LABEL,
            "signing_state": SIGNING_STATE,
            "case_id": case.case_id,
            "recipient": case.recipient.recipient,
            "recipient_role": case.recipient.recipient_role,
            "source_seals": [source.to_dict() for source in case.sources],
            "peer_outputs": list(case.peer_outputs),
            "human_reviewed_by": case.human_reviewed_by,
            "deadline_warning": (
                "DEADLINE_COUNSEL_REVIEW_REQUIRED: do not rely on ChartTrace "
                "for limitation or repose deadlines."
            ),
        }
        with destination.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        append_receipt(case, "RELEASE_BUILT", "Local unsigned release bundle built.")
        self._save()
        return destination

    def release_to_named_recipient(self, case_id: str) -> CaseRecord:
        self._require_release_gate(case_id)
        case = self.get_case(case_id)
        case.transition(CaseLifecycle.RELEASED_TO_NAMED_RECIPIENT)
        append_receipt(
            case,
            "RELEASED_TO_NAMED_RECIPIENT",
            "Operator confirmed transfer to the separately authorized recipient.",
        )
        self._save()
        return case

    def place_retention_hold(self, case_id: str, reason: str) -> CaseRecord:
        self._require_unlocked()
        case = self.get_case(case_id)
        if case.lifecycle is not CaseLifecycle.RELEASED_TO_NAMED_RECIPIENT:
            raise ReleaseBlockedError("Retention hold requires a released case.")
        if not reason.strip():
            raise ValueError("Retention-hold reason is required.")
        case.retention_hold_reason = reason.strip()
        case.transition(CaseLifecycle.RETENTION_HOLD)
        append_receipt(case, "RETENTION_HOLD", "Local deletion blocked.")
        self._save()
        return case

    def clear_retention_hold(self, case_id: str) -> CaseRecord:
        self._require_unlocked()
        case = self.get_case(case_id)
        if case.lifecycle is not CaseLifecycle.RETENTION_HOLD:
            raise ReleaseBlockedError("Case does not have a retention hold.")
        case.retention_hold_reason = None
        append_receipt(case, "RETENTION_HOLD_CLEARED", "Local deletion is permitted.")
        self._save()
        return case

    def delete_case_material(self, case_id: str) -> CaseRecord:
        self._require_unlocked()
        case = self.get_case(case_id)
        if case.lifecycle not in {
            CaseLifecycle.RELEASED_TO_NAMED_RECIPIENT,
            CaseLifecycle.RETENTION_HOLD,
        }:
            raise ReleaseBlockedError("Only released cases may be deleted.")
        if case.retention_hold_reason:
            raise ReleaseBlockedError("Deletion is blocked by a retention hold.")
        append_receipt(
            case,
            "DELETION_RECEIPT",
            f"Deleted {len(case.sources)} source seal(s) and analysis output locally.",
        )
        case.sources.clear()
        case.peer_outputs.clear()
        case.deleted_at = case.updated_at
        case.transition(CaseLifecycle.DELETED_WITH_RECEIPT)
        self._save()
        return case

    def get_case(self, case_id: str) -> CaseRecord:
        self._require_unlocked()
        try:
            return self.cases[case_id]
        except KeyError as error:
            raise KeyError(f"Unknown case: {case_id}") from error

    def _revoke_all_transfer_authorizations(self, reason: str) -> None:
        for case in self.cases.values():
            if case.recipient.authorized_at or case.recipient.authorization_epoch is not None:
                case.recipient.revoke()
                append_receipt(
                    case,
                    "TRANSFER_AUTH_REVOKED",
                    f"Named-recipient authorization invalidated ({reason}).",
                )

    def _require_unlocked(self) -> None:
        if not self.unlocked:
            raise ApplicationLockedError("Unlock ChartTrace before accessing cases.")

    def _require_analysis_gate(self, operation: str) -> None:
        self._require_unlocked()
        if not self.consent.current_and_authorized:
            raise AnalysisBlockedError(
                f"{operation.capitalize()} blocked: current terms and "
                "lawful authority are required."
            )

    def _require_release_gate(self, case_id: str) -> None:
        self._require_analysis_gate("release")
        case = self.get_case(case_id)
        if case.lifecycle is not CaseLifecycle.READY_TO_RELEASE:
            raise ReleaseBlockedError("Case is not READY_TO_RELEASE.")
        if case.recipient.state is not LegalState.TRANSFER_AUTHORIZED:
            raise ReleaseBlockedError(
                "Separate transfer authorization for the named recipient is required."
            )
        if case.recipient.authorization_version != TRUST_CENTER_VERSION:
            raise ReleaseBlockedError("Recipient transfer authorization is outdated.")
        if case.recipient.authorization_epoch != self.consent.authority_epoch:
            raise ReleaseBlockedError(
                "Recipient transfer authorization is stale after a terms "
                "or authority change."
            )

    def _load_vault_header(self) -> None:
        if not self.store.state_path.exists():
            return
        try:
            value = self.store.load()
        except VaultError:
            raise
        if not value:
            return
        classification = inspect_envelope(value)
        if classification.get("legacy_plaintext"):
            raise VaultError("Plaintext or unverified state cannot be unlocked.")
        self._sealed_envelope = value
        self._verifier = classification.get("secret_verifier")
        consent_value = value.get("consent") or {}
        if consent_value:
            self.consent = ConsentLedger.from_dict(consent_value)

    def _materialize_consent_only(self) -> None:
        """Restore legal state only. Case names and sources stay out of the stub."""
        if not self._sealed_envelope:
            return
        consent_value = self._sealed_envelope.get("consent") or {}
        if consent_value:
            self.consent = ConsentLedger.from_dict(consent_value)

    def _save(self) -> None:
        if not self.persist:
            return
        if self._verifier is None:
            return
        self.store.save(
            build_envelope(
                verifier=self._verifier,
                consent=self.consent.to_dict(),
                cases=[case.to_dict() for case in self.cases.values()],
                app_version=APP_VERSION,
                build_label=BUILD_LABEL,
                signing_state=SIGNING_STATE,
            )
        )
