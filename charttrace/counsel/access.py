"""Counsel access controls — cannot read unreleased or unrelated cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from charttrace.export.ctpkg import CtpkgBuildError, CtpkgPackage, verify_ctpkg


class CounselAccessError(PermissionError):
    """Fail-closed counsel mode access denial."""


@dataclass
class CounselSession:
    counsel_id: str
    recipient_id: str
    licensed: bool = True
    allowed_case_ids: Set[str] = field(default_factory=set)
    _opened: Dict[str, CtpkgPackage] = field(default_factory=dict)

    def assert_can_open(self, *, case_id: str, package: CtpkgPackage) -> None:
        if not self.licensed:
            raise CounselAccessError("Counsel mode requires licensed counsel identity")
        if package.recipient_id != self.recipient_id:
            raise CounselAccessError(
                f"Wrong recipient package: {package.recipient_id} != session {self.recipient_id}"
            )
        release_state = (package.payload.get("peer_review_release_manifest") or {}).get(
            "release_state"
        )
        if release_state and release_state not in (
            "RELEASED_TO_NAMED_RECIPIENT",
            "released",
        ):
            raise CounselAccessError("Cannot read unreleased package in counsel mode")
        if case_id not in self.allowed_case_ids:
            raise CounselAccessError(
                f"Cannot read unrelated or unauthorized case '{case_id}'"
            )
        try:
            verify_ctpkg(package, expected_recipient_id=self.recipient_id)
        except CtpkgBuildError as exc:
            raise CounselAccessError(str(exc)) from exc

    def open_package(self, *, case_id: str, package: CtpkgPackage) -> CtpkgPackage:
        self.assert_can_open(case_id=case_id, package=package)
        self._opened[case_id] = package
        return package

    def fill_legal_fields(
        self,
        *,
        case_id: str,
        lead_id: str,
        legal_relevance: Optional[str] = None,
        legal_viability: Optional[str] = None,
    ) -> Dict[str, object]:
        if case_id not in self._opened:
            raise CounselAccessError("Open a released package before filling legal fields")
        if not self.licensed:
            raise CounselAccessError("Only licensed counsel may fill legal fields")
        return {
            "case_id": case_id,
            "lead_id": lead_id,
            "legal_relevance": legal_relevance,
            "legal_viability": legal_viability,
            "counsel_filled": True,
            "counsel_id": self.counsel_id,
        }
