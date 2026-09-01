"""Declarative native screen catalog used by Tk and headless tests."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple

from charttrace.app.cases import DEADLINE_BANNER


LEGAL_ACTION_ID = "legal_data_terms"


class ScreenId(str, Enum):
    UNLOCK = "unlock"
    CASE_LIBRARY = "case_library"
    NEW_CASE_PREFLIGHT = "new_case_preflight"
    SECURE_INGEST = "secure_ingest"
    PEER_RUN = "peer_run"
    EVIDENCE_STUDIO = "evidence_studio"
    HYPOTHESIS_LAB = "hypothesis_lab"
    REVIEW_CONSOLE = "review_console"
    RELEASE_BUILDER = "release_builder"
    AUDIT_RECEIPTS = "audit_receipts"
    LEGAL_DATA_TERMS = "legal_data_terms"
    COUNSEL_REVIEW_IMPORT = "counsel_review_import"
    COMMERCIAL_CONSOLE = "commercial_console"


@dataclass(frozen=True)
class ScreenDefinition:
    screen_id: ScreenId
    title: str
    summary: str
    persistent_actions: Tuple[str, ...] = (LEGAL_ACTION_ID,)
    deadline_banner: str = DEADLINE_BANNER

    @property
    def has_legal_button(self) -> bool:
        return LEGAL_ACTION_ID in self.persistent_actions


SCREEN_CATALOG: Dict[ScreenId, ScreenDefinition] = {
    ScreenId.UNLOCK: ScreenDefinition(
        ScreenId.UNLOCK,
        "Unlock",
        "Open the local operator session. Unlock secrets are never persisted.",
    ),
    ScreenId.CASE_LIBRARY: ScreenDefinition(
        ScreenId.CASE_LIBRARY,
        "Case Library",
        "Local cases and lifecycle status.",
    ),
    ScreenId.NEW_CASE_PREFLIGHT: ScreenDefinition(
        ScreenId.NEW_CASE_PREFLIGHT,
        "New Case Preflight",
        "Confirm current terms and lawful authority before ingest.",
    ),
    ScreenId.SECURE_INGEST: ScreenDefinition(
        ScreenId.SECURE_INGEST,
        "Secure Ingest",
        "Hash-seal local sources without uploading them.",
    ),
    ScreenId.PEER_RUN: ScreenDefinition(
        ScreenId.PEER_RUN,
        "Peer Run",
        "Create an unsigned synthetic analysis envelope behind the legal gate.",
    ),
    ScreenId.EVIDENCE_STUDIO: ScreenDefinition(
        ScreenId.EVIDENCE_STUDIO,
        "Evidence Studio",
        "Inspect source seals, provenance, and citation coverage.",
    ),
    ScreenId.HYPOTHESIS_LAB: ScreenDefinition(
        ScreenId.HYPOTHESIS_LAB,
        "Hypothesis Lab",
        "Develop non-factual hypotheses for internal review.",
    ),
    ScreenId.REVIEW_CONSOLE: ScreenDefinition(
        ScreenId.REVIEW_CONSOLE,
        "Review Console",
        "Complete internal QA and mandatory named-human release review.",
    ),
    ScreenId.RELEASE_BUILDER: ScreenDefinition(
        ScreenId.RELEASE_BUILDER,
        "Release Builder",
        "Build a local unsigned bundle for one separately authorized recipient.",
    ),
    ScreenId.AUDIT_RECEIPTS: ScreenDefinition(
        ScreenId.AUDIT_RECEIPTS,
        "Audit & Receipts",
        "Verify the local hash-chained event and deletion receipts.",
    ),
    ScreenId.LEGAL_DATA_TERMS: ScreenDefinition(
        ScreenId.LEGAL_DATA_TERMS,
        "Legal, Data & Terms",
        "Local Trust Center and separate affirmative acknowledgements.",
    ),
    ScreenId.COUNSEL_REVIEW_IMPORT: ScreenDefinition(
        ScreenId.COUNSEL_REVIEW_IMPORT,
        "Offline Counsel Review / Import",
        "Import a local counsel decision bundle without network access.",
    ),
    ScreenId.COMMERCIAL_CONSOLE: ScreenDefinition(
        ScreenId.COMMERCIAL_CONSOLE,
        "Commercial Console",
        "Isolated account and licensing metadata only.",
    ),
}
