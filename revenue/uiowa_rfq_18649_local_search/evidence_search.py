#!/usr/bin/env python3
"""Deterministic offline provenance-preserving search for UIOWA-127."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "uiowa.local-evidence-search.v1"
TOKEN_RE = re.compile(r"\w+", re.UNICODE)

class SearchError(ValueError):
    pass


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
    with path.open(encoding="utf-8", newline="") as fh:
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
    with path.open(encoding="utf-8", newline="") as fh:
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
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "uiowa.document-extraction.v1":
        raise SearchError("unexpected extraction schema")
    doc = payload.get("document", {})
    out = []
    for seg in payload.get("segments", []):
        if not (seg.get("text") or "").strip():
            continue
        rid = f"EXTRACT:{doc.get('name','document')}:{seg.get('segment_id','segment')}"
        heading = " > ".join(seg.get("heading_path") or [])
        out.append(_base(
            rid, "extracted_text", heading or doc.get("name", ""),
            " ".join([heading, seg.get("text", "")]), source_path, blob_sha,
            seg.get("locator", ""), github_url(source_path),
            metadata={"document": doc.get("name"), "document_sha256": doc.get("sha256"), "kind": seg.get("kind")},
        ))
    return out


def validate_records(records: list[dict[str, Any]]) -> None:
    seen = set()
    for row in records:
        rid = row.get("record_id")
        if not rid or rid in seen:
            raise SearchError(f"duplicate/missing record_id: {rid}")
        seen.add(rid)
        for key in ("record_type", "source_path", "upstream_blob_sha", "locator", "source_url"):
            if not row.get(key):
                raise SearchError(f"{rid}: missing {key}")
        if not (row["source_url"].startswith("https://") or row["source_url"].startswith("synthetic://")):
            raise SearchError(f"{rid}: unsupported source_url scheme")


def build_index(records: list[dict[str, Any]]) -> dict[str, Any]:
    validate_records(records)
    docs = sorted(records, key=lambda x: x["record_id"])
    postings: dict[str, dict[str, int]] = defaultdict(dict)
    doc_lengths = {}
    for row in docs:
        bag = tokenize(" ".join([row["record_id"], row["record_type"], row.get("title", ""), row.get("text", ""), json.dumps(row.get("metadata", {}), sort_keys=True)]))
        counts = Counter(bag)
        doc_lengths[row["record_id"]] = len(bag)
        for term, count in counts.items():
            postings[term][row["record_id"]] = count
    return {
        "schema": SCHEMA,
        "ranking": "sum(idf(term) * (1 + ln(tf))) + exact-phrase bonus 1.0; deterministic tie-break by record_id",
        "documents": docs,
        "doc_lengths": dict(sorted(doc_lengths.items())),
        "postings": {term: dict(sorted(values.items())) for term, values in sorted(postings.items())},
    }


def snippet(text: str, terms: list[str], radius: int = 95) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return ""
    low = clean.casefold()
    starts = [low.find(t) for t in terms if low.find(t) >= 0]
    pos = min(starts) if starts else 0
    left = max(0, pos - radius)
    right = min(len(clean), pos + radius)
    result = clean[left:right]
    if left:
        result = "…" + result
    if right < len(clean):
        result += "…"
    return result


def search(index: dict[str, Any], query: str, limit: int = 5, record_types: set[str] | None = None) -> list[dict[str, Any]]:
    if index.get("schema") != SCHEMA:
        raise SearchError("unexpected index schema")
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
    } for rid in ranked]


def load_manifest(path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    records: list[dict[str, Any]] = []
    for src in manifest.get("sources", []):
        kind = src["adapter"]
        local = root / src["local_file"]
        args = (local, src["upstream_path"], src["upstream_blob_sha"])
        if kind == "authority": records += adapt_authority(*args)
        elif kind == "evidence_csv": records += adapt_evidence_csv(*args)
        elif kind == "findings_csv": records += adapt_findings_csv(*args)
        elif kind == "extraction": records += adapt_extraction(*args)
        else: raise SearchError(f"unknown adapter: {kind}")
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
        index = json.loads(args.index.read_text(encoding="utf-8"))
        result = search(index, args.query, args.limit, set(args.types) if args.types else None)
        print(json.dumps({"query": args.query, "results": result}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
