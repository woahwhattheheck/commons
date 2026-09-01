"""Offline Counsel Review mode facade."""

from __future__ import annotations

from typing import Any, Dict, Optional

from charttrace.counsel.access import CounselAccessError, CounselSession
from charttrace.export.ctpkg import CtpkgPackage


class CounselReviewMode:
    def __init__(self, session: CounselSession) -> None:
        self.session = session

    def import_package(self, *, case_id: str, package: CtpkgPackage) -> Dict[str, Any]:
        opened = self.session.open_package(case_id=case_id, package=package)
        return {
            "case_id": case_id,
            "recipient_id": opened.recipient_id,
            "release_version": opened.release_version,
            "package_hash": opened.package_hash,
            "signature_state": opened.signature_state,
            "section_order": opened.payload.get("section_order"),
            "weak_appendix_count": len(opened.payload.get("weak_appendix") or []),
            "source_manifest_count": len(opened.payload.get("source_manifest") or []),
        }

    def try_import(self, *, case_id: str, package: CtpkgPackage) -> Dict[str, Any]:
        try:
            return {"ok": True, "result": self.import_package(case_id=case_id, package=package)}
        except CounselAccessError as exc:
            return {"ok": False, "error": str(exc)}

    def set_legal_assessment(
        self,
        *,
        case_id: str,
        lead_id: str,
        legal_relevance: Optional[str] = None,
        legal_viability: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.session.fill_legal_fields(
            case_id=case_id,
            lead_id=lead_id,
            legal_relevance=legal_relevance,
            legal_viability=legal_viability,
        )
