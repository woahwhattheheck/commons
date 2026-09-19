#!/usr/bin/env python3
"""Deterministic offline provenance-preserving search for UIOWA-127."""
from __future__ import annotations

import argparse
import csv
import copy
import sys
import tempfile
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "uiowa.local-evidence-search.v1"
TOKEN_RE = re.compile(r"\w+", re.UNICODE)

if __package__:
    from .search_provenance import (SearchError, NOTICE, MAX_BYTES, native_rows, verified_sources,
                                    enrich, exact_excerpt, exact_snippet, index_digest, verify_index, read_json)
else:
    from search_provenance import (SearchError, NOTICE, MAX_BYTES, native_rows, verified_sources,
                                   enrich, exact_excerpt, exact_snippet, index_digest, verify_index, read_json)


def tokenize(value: str) -> list[str]:
    return [m.group(0).casefold() for m in TOKEN_RE.finditer(value or "")]


def github_url(path: str, ref: str = "main") -> str:
    return f"https://github.com/woahwhattheheck/commons/blob/{ref}/{path}"


def _base(record_id: str, record_type: str, title: str, text: str, source_path: str,
          upstream_blob_sha: str, locator: str, source_url: str | None = None,
          linked_ids: list[str] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not all([record_id, record_type, source_path, upstream_blob_sha, locator]):
        raise SearchError(f"{record_id or '<missing-id>'}: provenance fields must be non-empty")
    return {
        "record_id": record_id,
        "record_type": record_type,
        "title": title,
        "text": text,
        "source_path": source_path,
        "upstream_blob_sha": upstream_blob_sha,
        "locator": locator,
        "source_url": source_url or github_url(source_path),
        "linked_ids": sorted(linked_ids or []),
        "metadata": metadata or {},
        "provenance": {"local_bytes_verified": False, "underlying_status": "unverified_direct_adapter"},
    }


def adapt_authority(path: Path, source_path: str, blob_sha: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("sources"), list):
        raise SearchError("authority fixture missing sources array")
    out = []
    for row in payload["sources"]:
        sid = row.get("source_id")
        if not sid:
            raise SearchError("authority source missing source_id")
        meta = {k: row.get(k) for k in ("group", "dimension", "evidence_kind", "maturity", "observed_at", "confidence_bp")}
        searchable_meta = " ".join(str(v) for v in meta.values() if v is not None)
        out.append(_base(
            sid, "source_metadata", sid,
            f"{row.get('claim','')} {searchable_meta}", source_path, blob_sha,
            f"sources[source_id={sid}]", row.get("source_ref") or github_url(source_path), metadata=meta,
        ))
    return out


def adapt_evidence_csv(path: Path, source_path: str, blob_sha: str) -> list[dict[str, Any]]:
    out = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            rid = row.get("evidence_id", "")
            out.append(_base(
                rid, "observation", row.get("source_name", ""),
                " ".join([row.get("observation", ""), row.get("service", ""), row.get("source_type", ""), row.get("evidence_state", "")]),
                source_path, blob_sha, row.get("locator", ""), github_url(source_path),
                metadata={"service": row.get("service"), "source_type": row.get("source_type"), "evidence_state": row.get("evidence_state")},
            ))
    return out


def adapt_findings_csv(path: Path, source_path: str, blob_sha: str) -> list[dict[str, Any]]:
    out = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            rid = row.get("finding_id", "")
            linked = [x.strip() for x in row.get("evidence_ids", "").split(";") if x.strip()]
            text = " ".join([row.get("title", ""), row.get("statement", ""), row.get("limitation", ""), row.get("service", ""), row.get("type", ""), row.get("confidence", "")])
            out.append(_base(
                rid, "finding", row.get("title", ""), text, source_path, blob_sha,
                f"finding_id={rid}", github_url(source_path), linked_ids=linked,
                metadata={"service": row.get("service"), "finding_type": row.get("type"), "confidence": row.get("confidence")},
            ))
    return out


def adapt_extraction(path: Path, source_path: str, blob_sha: str) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    _, payload = native_rows(raw, "extraction")
    if payload.get("schema") != "uiowa.document-extraction.v1":
        raise SearchError("unexpected extraction schema")
    doc = payload.get("document", {})
    out = []
    segments = payload["segments"] or [{"segment_id": "document-diagnostic", "kind": "unreadable",
                                         "locator": "document metadata", "text": "", "heading_path": [],
                                         "warnings": [str(payload.get("error") or "No extractable text reported")]}]
    for seg in segments:
        readable = bool(seg["text"].strip())
        warnings = list(payload["warnings"]) + list(seg["warnings"])
        diagnostic = " ".join(warnings) or "No extractable text reported"
        rid = f"EXTRACT:{doc.get('name','document')}:{seg.get('segment_id','segment')}"
        heading = " > ".join(seg.get("heading_path") or [])
        out.append(_base(
            rid, "extracted_text" if readable else "extraction_diagnostic", heading or doc.get("name", ""),
            " ".join([heading, seg["text"]]) if readable else diagnostic, source_path, blob_sha,
            seg.get("locator", ""), github_url(source_path),
            metadata={"document": doc.get("name"), "document_sha256": doc.get("sha256"), "kind": seg.get("kind")},
        ))
        out[-1].update(original=seg, original_text=seg["text"], warnings=warnings)
    return out


def validate_records(records: list[dict[str, Any]]) -> None:
    if not isinstance(records, list) or len(records) > 10000:
        raise SearchError("records must be a list of at most 10000 objects")
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            raise SearchError("record must be an object")
        rid = row.get("record_id")
        if not isinstance(rid, str):
            raise SearchError("record_id must be a string")
        if not rid or rid in seen:
            raise SearchError(f"duplicate/missing record_id: {rid}")
        seen.add(rid)
        for key in ("record_type", "source_path", "upstream_blob_sha", "locator", "source_url"):
            if not isinstance(row.get(key), str) or not row[key]:
                raise SearchError(f"{rid}: missing {key}")
        if any(not isinstance(row.get(key, ""), str) for key in ("title", "text", "original_text")):
            raise SearchError(f"{rid}: text fields must be strings")
        if not isinstance(row.get("metadata", {}), dict) or not isinstance(row.get("linked_ids", []), list) or any(not isinstance(x, str) for x in row.get("linked_ids", [])):
            raise SearchError(f"{rid}: invalid metadata or linked IDs")
        if not (row["source_url"].startswith("https://") or row["source_url"].startswith("synthetic://")):
            raise SearchError(f"{rid}: unsupported source_url scheme")


def build_index(records: list[dict[str, Any]]) -> dict[str, Any]:
    validate_records(records)
    docs = sorted(copy.deepcopy(records), key=lambda x: x["record_id"])
    postings: dict[str, dict[str, int]] = defaultdict(dict)
    doc_lengths = {}
    for row in docs:
        bag = tokenize(" ".join([row["record_id"], row["record_type"], row.get("title", ""), row.get("text", ""), json.dumps(row.get("metadata", {}), sort_keys=True)]))
        counts = Counter(bag)
        # Preserve existing term frequencies; expose previously omitted native fields and warnings.
        extras = json.dumps(row.get("original", {}), ensure_ascii=False, sort_keys=True) + " " + json.dumps(row.get("warnings", []), ensure_ascii=False)
        for term in tokenize(extras):
            counts.setdefault(term, 1)
        doc_lengths[row["record_id"]] = sum(counts.values())
        for term, count in counts.items():
            postings[term][row["record_id"]] = count
    index = {
        "schema": SCHEMA,
        "ranking": "sum(idf(term) * (1 + ln(tf))) + exact-phrase bonus 1.0; deterministic tie-break by record_id",
        "documents": docs,
        "doc_lengths": dict(sorted(doc_lengths.items())),
        "postings": {term: dict(sorted(values.items())) for term, values in sorted(postings.items())},
        "notice": NOTICE,
    }
    index["content_digest"] = index_digest(index)
    return index


def snippet(text: str, terms: list[str], radius: int = 95) -> str:
    excerpt = exact_excerpt(text, terms, radius)
    visual = re.sub(r"\s+", " ", excerpt["text"]).strip()
    return ("…" if excerpt["truncated_before"] else "") + visual + ("…" if excerpt["truncated_after"] else "")



def search(index: dict[str, Any], query: str, limit: int = 5, record_types: set[str] | None = None) -> list[dict[str, Any]]:
    if not isinstance(index, dict) or index.get("schema") != SCHEMA:
        raise SearchError("unexpected index schema")
    if not isinstance(query, str) or len(query) > 2000:
        raise SearchError("query must be a string of at most 2000 characters")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise SearchError("limit must be an integer from 1 to 100")
    if record_types is not None and (not isinstance(record_types, set) or any(not isinstance(x, str) for x in record_types)):
        raise SearchError("record_types must be a set of strings")
    verify_index(index)
    validate_records(index["documents"])
    terms = tokenize(query)
    if not terms:
        return []
    docs = {x["record_id"]: x for x in index["documents"]}
    scores: dict[str, float] = defaultdict(float)
    n = len(docs)
    for term in terms:
        posting = index["postings"].get(term, {})
        if not posting:
            continue
        idf = math.log((n + 1) / (len(posting) + 0.5)) + 1.0
        for rid, tf in posting.items():
            if record_types and docs[rid]["record_type"] not in record_types:
                continue
            scores[rid] += idf * (1.0 + math.log(tf))
    phrase = " ".join(terms)
    for rid in list(scores):
        searchable = " ".join([docs[rid].get("title", ""), docs[rid].get("text", "")]).casefold()
        if phrase and phrase in searchable:
            scores[rid] += 1.0
    ranked = sorted(scores, key=lambda rid: (-scores[rid], rid))[:limit]
    return [{
        "record_id": rid,
        "record_type": docs[rid]["record_type"],
        "score": round(scores[rid], 6),
        "title": docs[rid].get("title", ""),
        "snippet": snippet(docs[rid].get("text", ""), terms),
        "source_url": docs[rid]["source_url"],
        "source_path": docs[rid]["source_path"],
        "upstream_blob_sha": docs[rid]["upstream_blob_sha"],
        "locator": docs[rid]["locator"],
        "linked_ids": docs[rid].get("linked_ids", []),
        "snippet_exact": exact_snippet(docs[rid], terms),
        "record_url": docs[rid].get("record_url"),
        "record_locator": docs[rid].get("record_locator"),
        "underlying_source_url": docs[rid].get("underlying_source_url"),
        "original": copy.deepcopy(docs[rid].get("original", {})),
        "synthetic": docs[rid].get("synthetic"),
        "warnings": list(docs[rid].get("warnings", [])),
        "provenance": dict(docs[rid].get("provenance", {"local_bytes_verified": False})),
        "index_integrity": "digest_verified" if "content_digest" in index else "legacy_unbound",
        "notice": NOTICE,
        "link_diagnostics": [{"code": "MISSING_LINKED_RECORD", "record_id": link}
                             for link in docs[rid].get("linked_ids", []) if link not in docs],
    } for rid in ranked]


def load_manifest(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    # Adapt immutable local snapshots, not a path that could change after its digest was checked.
    with tempfile.TemporaryDirectory(prefix="uiowa-search-") as work:
        local = Path(work) / "snapshot"
        for src, raw, proof in verified_sources(path):
            local.write_bytes(raw)
            args = (local, src["upstream_path"], src["upstream_blob_sha"])
            kind = src["adapter"]
            if kind == "authority": batch = adapt_authority(*args)
            elif kind == "evidence_csv": batch = adapt_evidence_csv(*args)
            elif kind == "findings_csv": batch = adapt_findings_csv(*args)
            elif kind == "extraction": batch = adapt_extraction(*args)
            else: raise SearchError(f"unknown adapter: {kind}")
            records.extend(enrich(batch, src, raw, proof))
            if len(records) > 10000:
                raise SearchError("index exceeds 10000 records")
    validate_records(records)
    return records



def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("manifest", type=Path)
    b.add_argument("output", type=Path)
    q = sub.add_parser("query")
    q.add_argument("index", type=Path)
    q.add_argument("query")
    q.add_argument("--limit", type=int, default=5)
    q.add_argument("--type", action="append", dest="types")
    args = ap.parse_args()
    if args.cmd == "build":
        index = build_index(load_manifest(args.manifest))
        args.output.write_text(json.dumps(index, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"indexed {len(index['documents'])} records / {len(index['postings'])} terms")
    else:
        if args.index.stat().st_size > MAX_BYTES:
            raise SearchError("index exceeds byte limit")
        index = read_json(args.index.read_bytes())
        result = search(index, args.query, args.limit, set(args.types) if args.types else None)
        print(json.dumps({"query": args.query, "results": result}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SearchError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
