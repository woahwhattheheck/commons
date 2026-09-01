"""Clause-level citation resolution and entailment."""

from __future__ import annotations

from charttrace.review.models import Citation, FactualClause, SourceUniverse


def resolve_citation(citation: Citation, universe: SourceUniverse) -> str | None:
    document = universe.get(citation.document_id)
    if document is None:
        return "unknown-document"
    if citation.source_sha256 != document.sha256:
        return "hash-mismatch"
    if citation.page < 1 or citation.page > document.page_count:
        return "page-out-of-range"
    page_text = document.page_texts[citation.page - 1]
    if citation.span_start < 0 or citation.span_end <= citation.span_start:
        return "span-invalid"
    if citation.span_end > len(page_text):
        return "span-out-of-range"
    excerpt = page_text[citation.span_start : citation.span_end]
    if excerpt != citation.text:
        return "excerpt-mismatch"
    return None


def clause_entailed(clause: FactualClause, universe: SourceUniverse) -> bool:
    if clause.invented or not clause.citations:
        return False
    pages: list[str] = []
    for citation in clause.citations:
        if resolve_citation(citation, universe) is not None:
            return False
        document = universe.get(citation.document_id)
        if document is None:
            return False
        pages.append(document.page_texts[citation.page - 1])
    union = "\n".join(pages)
    tokens = [
        token.strip(".,;:?")
        for token in clause.text.split()
        if token.startswith("SYN-") or token.startswith("lead-")
    ]
    if tokens:
        return all(token in union for token in tokens)
    return all(citation.text in union for citation in clause.citations)
