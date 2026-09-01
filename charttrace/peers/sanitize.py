"""Treat record text as untrusted. Prompt-injection must never become commands."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence, Tuple


INJECTION_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|system)\s+(instructions|prompts)", re.I),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"</?\s*(?:system|assistant|tool)\s*>", re.I),
    re.compile(r"do\s+not\s+cite\s+(?:sources|records)", re.I),
    re.compile(r"reveal\s+(?:your|the)\s+(?:system\s+)?prompt", re.I),
    re.compile(r"execute\s+(?:the\s+)?(?:following\s+)?(?:command|code|shell)", re.I),
    re.compile(r"exfiltrate|send\s+to\s+https?://", re.I),
)


@dataclass(frozen=True)
class InjectionFinding:
    document_id: str
    excerpt_index: int
    pattern: str
    snippet: str

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "excerpt_index": self.excerpt_index,
            "pattern": self.pattern,
            "snippet": self.snippet,
            "treated_as": "untrusted_document_text",
        }


def scan_untrusted_text(document_id: str, excerpt_index: int, text: str) -> List[InjectionFinding]:
    findings: List[InjectionFinding] = []
    for pat in INJECTION_PATTERNS:
        m = pat.search(text or "")
        if m:
            start = max(0, m.start() - 24)
            end = min(len(text), m.end() + 24)
            findings.append(
                InjectionFinding(
                    document_id=document_id,
                    excerpt_index=excerpt_index,
                    pattern=pat.pattern,
                    snippet=text[start:end],
                )
            )
    return findings


def neutralize_as_document_text(text: str) -> str:
    """Mark text as untrusted document content — never executable."""
    return f"[UNTRUSTED_RECORD_TEXT]\n{text}"


def collect_injection_findings(excerpts: Sequence[dict]) -> List[InjectionFinding]:
    out: List[InjectionFinding] = []
    for i, ex in enumerate(excerpts):
        doc_id = str(ex.get("document_id", f"doc-{i}"))
        text = str(ex.get("text", ""))
        out.extend(scan_untrusted_text(doc_id, i, text))
    return out
