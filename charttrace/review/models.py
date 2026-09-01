"""Self-contained review objects. Lane D does not import other lane trees."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Citation:
    document_id: str
    page: int
    source_sha256: str
    span_start: int
    span_end: int
    text: str


@dataclass(frozen=True, slots=True)
class FactualClause:
    clause_id: str
    text: str
    citations: tuple[Citation, ...]
    invented: bool = False


@dataclass(frozen=True, slots=True)
class AuthorityRef:
    authority_id: str
    jurisdiction: str
    effective_from: str
    effective_to: str | None
    care_date: str
    applicability: str


@dataclass(frozen=True, slots=True)
class LeadCandidate:
    lead_id: str
    title: str
    band: str  # obvious | subtle | weak
    clauses: tuple[FactualClause, ...]
    counterevidence: tuple[str, ...]
    alternatives: tuple[str, ...]
    weak_grounded: bool = False
    duplicate_of: str | None = None
    followed_source_instruction: bool = False
    unbounded_absence: bool = False
    problem_list_as_diagnosis: bool = False
    ordered_as_completed: bool = False
    ocr_guess_as_verified: bool = False
    impossible_chronology: bool = False
    unit_or_laterality_error: bool = False
    authority: AuthorityRef | None = None


@dataclass(frozen=True, slots=True)
class SourceDocument:
    document_id: str
    sha256: str
    page_count: int
    page_texts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceUniverse:
    case_id: str
    documents: Mapping[str, SourceDocument] = field(default_factory=dict)

    def get(self, document_id: str) -> SourceDocument | None:
        return self.documents.get(document_id)
