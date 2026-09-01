"""Export-language and presentation lints for ChartTrace Lane D."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence


FORBIDDEN_PHRASES = (
    "the patient was not told",
    "patient was not told",
    "was never told",
    "never told the patient",
    "no follow-up occurred",
    "there was no follow-up",
    "malpractice",
    "negligence",
    "negligent",
    "standard of care",
    "standard-of-care",
    "causation",
    "actionability",
    "actionable",
    "case value",
    "damages owed",
    "win probability",
)

UNBOUNDED_ABSENCE_PATTERNS = (
    re.compile(r"\bnever told\b", re.I),
    re.compile(r"\bwas not told\b", re.I),
    re.compile(r"\bno follow-?up\b", re.I),
    re.compile(r"\bnot found\b(?!\s+in the (supplied|provided|reviewed)\b)", re.I),
)

SCOPED_NONFINDING_HINT = (
    "No documentation of communication was located in the supplied "
    "{scope} for {date_range}."
)


@dataclass
class LanguageIssue:
    item_id: str
    phrase: str
    field_name: str
    suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "phrase": self.phrase,
            "field_name": self.field_name,
            "suggestion": self.suggestion,
        }


@dataclass
class LanguageLintReport:
    issues: List[LanguageIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "issues": [i.to_dict() for i in self.issues]}


def scoped_nonfinding(*, scope: str, date_range: str) -> str:
    return SCOPED_NONFINDING_HINT.format(scope=scope, date_range=date_range)


def lint_text(item_id: str, field_name: str, text: str) -> List[LanguageIssue]:
    issues: List[LanguageIssue] = []
    if not text:
        return issues
    lower = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lower:
            issues.append(
                LanguageIssue(
                    item_id=item_id,
                    phrase=phrase,
                    field_name=field_name,
                    suggestion=scoped_nonfinding(
                        scope="reviewed materials",
                        date_range="the supplied date range",
                    ),
                )
            )
    for pat in UNBOUNDED_ABSENCE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        hit = m.group(0).lower()
        if any(hit in iss.phrase or iss.phrase in hit for iss in issues):
            continue
        issues.append(
            LanguageIssue(
                item_id=item_id,
                phrase=m.group(0),
                field_name=field_name,
                suggestion=scoped_nonfinding(scope="supplied records", date_range="DATE-DATE"),
            )
        )
    return issues


def lint_lead(lead: Dict[str, Any]) -> List[LanguageIssue]:
    lid = str(lead.get("lead_id") or lead.get("id") or "unknown")
    issues: List[LanguageIssue] = []
    for field_name in (
        "title",
        "hypothesis",
        "cited_observation",
        "review_question",
        "clause",
        "text",
        "summary",
    ):
        if field_name in lead and lead[field_name]:
            issues.extend(lint_text(lid, field_name, str(lead[field_name])))
    return issues


def lint_packet_texts(items: Sequence[Dict[str, Any]]) -> LanguageLintReport:
    report = LanguageLintReport()
    for item in items:
        report.issues.extend(lint_lead(item))
    return report
