"""Treat record text as untrusted data. Prompt-injection must never become commands."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Mapping, Sequence, Tuple

from charttrace.peers.validate import ZERO_WIDTH_CHARS


INJECTION_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(
        r"ignore\s+(all\s+|every\s+)?(previous|prior|above|earlier)\s+(instructions?|directives?|prompts?)",
        re.I,
    ),
    re.compile(
        r"disregard\s+(all\s+|every\s+)?(previous|prior|earlier|system)\s+(instructions?|prompts?|directives?)",
        re.I,
    ),
    re.compile(r"override\s+(the\s+)?(system\s+)?prompt", re.I),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+\S+", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"</?\s*(?:system|assistant|tool)\s*>", re.I),
    re.compile(r"do\s+not\s+cite\s+(?:sources|records)", re.I),
    re.compile(r"reveal\s+(?:your|the)\s+(?:system\s+)?prompt", re.I),
    re.compile(r"execute\s+(?:the\s+)?(?:following\s+)?(?:command|code|shell)", re.I),
    re.compile(r"exfiltrate|send\s+to\s+https?://", re.I),
)

QUARANTINE_MARKER = "[QUARANTINED_INSTRUCTION]"
UNTRUSTED_PREFIX = "[UNTRUSTED_RECORD_TEXT]\n"


@dataclass(frozen=True)
class InjectionFinding:
    document_id: str
    excerpt_index: int
    pattern: str
    snippet: str
    span_start: int
    span_end: int

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "excerpt_index": self.excerpt_index,
            "pattern": self.pattern,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "snippet_sha256": hashlib.sha256(self.snippet.encode("utf-8")).hexdigest(),
            "treated_as": "untrusted_document_text",
        }


def deobfuscate(text: str) -> str:
    """NFKC-fold, strip zero-width marks, and join letter-punctuation-letter runs."""
    folded = unicodedata.normalize("NFKC", text or "")
    for mark in ZERO_WIDTH_CHARS:
        folded = folded.replace(mark, "")
    return re.sub(r"(?<=[A-Za-z])[.\u00b7\u2022_\-](?=[A-Za-z])", "", folded)


def scan_untrusted_text(document_id: str, excerpt_index: int, text: str) -> List[InjectionFinding]:
    findings: List[InjectionFinding] = []
    for pat in INJECTION_PATTERNS:
        for m in pat.finditer(text or ""):
            start = max(0, m.start() - 24)
            end = min(len(text), m.end() + 24)
            findings.append(
                InjectionFinding(
                    document_id=document_id,
                    excerpt_index=excerpt_index,
                    pattern=pat.pattern,
                    snippet=text[start:end],
                    span_start=m.start(),
                    span_end=m.end(),
                )
            )
    return findings


def neutralize_as_document_text(text: str) -> str:
    """Mark text as untrusted document content — never executable."""
    if text.startswith(UNTRUSTED_PREFIX):
        return text
    return f"{UNTRUSTED_PREFIX}{text}"


def _merged_injection_spans(text: str) -> List[Tuple[int, int]]:
    spans = [(m.start(), m.end()) for pat in INJECTION_PATTERNS for m in pat.finditer(text or "")]
    if not spans:
        return []
    spans.sort()
    merged: List[Tuple[int, int]] = []
    for start, end in spans:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def quarantine_text(text: str) -> Tuple[str, List[Tuple[int, int]]]:
    """Replace injection spans so they cannot become searchable evidence."""
    merged = _merged_injection_spans(text)
    if not merged:
        return text, []
    out: List[str] = []
    cursor = 0
    for start, end in merged:
        out.append(text[cursor:start])
        out.append(QUARANTINE_MARKER)
        cursor = end
    out.append(text[cursor:])
    return "".join(out), merged


def prepare_untrusted_text(raw: str) -> Tuple[str, List[Tuple[int, int, int, int]], List[Tuple[int, int]]]:
    """Build escaped worker text plus worker-to-raw span alignment.

    Raw bytes stay immutable for citation binding. Worker payload is
    neutralized data-only text with injection spans replaced.
    """
    inj = _merged_injection_spans(raw)
    prefix_len = len(UNTRUSTED_PREFIX)
    parts: List[str] = []
    span_map: List[Tuple[int, int, int, int]] = []
    q_cursor = 0
    raw_cursor = 0
    for start, end in inj:
        if start > raw_cursor:
            kept = raw[raw_cursor:start]
            w0 = prefix_len + q_cursor
            parts.append(kept)
            q_cursor += len(kept)
            span_map.append((w0, prefix_len + q_cursor, raw_cursor, start))
        parts.append(QUARANTINE_MARKER)
        q_cursor += len(QUARANTINE_MARKER)
        raw_cursor = end
    if raw_cursor < len(raw) or not raw:
        kept = raw[raw_cursor:]
        w0 = prefix_len + q_cursor
        parts.append(kept)
        q_cursor += len(kept)
        span_map.append((w0, prefix_len + q_cursor, raw_cursor, len(raw)))
    escaped = neutralize_as_document_text("".join(parts))
    return escaped, span_map, inj


def map_worker_span_to_raw(
    span_map: Sequence[Tuple[int, int, int, int]],
    worker_start: int,
    worker_end: int,
) -> Tuple[int, int]:
    for ws, we, rs, re in span_map:
        if worker_start >= ws and worker_end <= we:
            offset = worker_start - ws
            length = worker_end - worker_start
            return rs + offset, rs + offset + length
    raise ValueError("worker span is not inside a raw-aligned kept segment")


def quote_from_worker_span(excerpt: Mapping[str, object], start: int, end: int) -> Tuple[int, int, str]:
    """Return raw span coordinates and the quote sliced from worker-visible kept text."""
    text = str(excerpt.get("text", ""))
    span_map = excerpt.get("span_map")
    quote = text[start:end]
    if span_map is None:
        return start, end, quote
    mapped = [tuple(item) for item in span_map]
    if not mapped:
        raise ValueError("unsafe span map")
    raw_start, raw_end = map_worker_span_to_raw(mapped, start, end)
    return raw_start, raw_end, quote


def prepare_untrusted_excerpts(excerpts: Sequence[dict]) -> Tuple[List[dict], List[InjectionFinding]]:
    cleaned: List[dict] = []
    findings: List[InjectionFinding] = []
    for i, ex in enumerate(excerpts):
        row = dict(ex)
        raw = str(row.get("text", ""))
        doc_id = str(row.get("document_id", f"doc-{i}"))
        deobf = deobfuscate(raw)
        findings.extend(scan_untrusted_text(doc_id, i, raw))
        if deobf != raw:
            findings.extend(scan_untrusted_text(doc_id, i, deobf))
        if deobf != raw and _merged_injection_spans(deobf):
            quarantined, _inj = quarantine_text(deobf)
            row["text"] = neutralize_as_document_text(quarantined)
            row["span_map"] = []
        else:
            escaped, span_map, _inj = prepare_untrusted_text(raw)
            row["text"] = escaped
            row["span_map"] = span_map
        row["text_kind"] = "untrusted_record_data"
        cleaned.append(row)
    return cleaned, findings


def quarantine_excerpts(excerpts: Sequence[dict]) -> Tuple[List[dict], List[InjectionFinding]]:
    return prepare_untrusted_excerpts(excerpts)


def collect_injection_findings(excerpts: Sequence[dict]) -> List[InjectionFinding]:
    out: List[InjectionFinding] = []
    for i, ex in enumerate(excerpts):
        doc_id = str(ex.get("document_id", f"doc-{i}"))
        text = str(ex.get("text", ""))
        deobf = deobfuscate(text)
        out.extend(scan_untrusted_text(doc_id, i, text))
        if deobf != text:
            out.extend(scan_untrusted_text(doc_id, i, deobf))
    return out
