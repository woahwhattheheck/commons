from __future__ import annotations

import csv
import io
import os
import stat
from pathlib import Path
from typing import Any

from .core import PilotError, canonical_json, parse_json_strict

MAX_INPUT_BYTES = 8 * 1024 * 1024


def read_json_regular(path: str | os.PathLike[str]) -> Any:
    p = os.fspath(path)
    st = os.lstat(p)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode) or st.st_size > MAX_INPUT_BYTES:
        raise PilotError("input must be bounded regular non-symlink file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(p, flags)
    try:
        fst = os.fstat(fd)
        if not stat.S_ISREG(fst.st_mode) or fst.st_size > MAX_INPUT_BYTES:
            raise PilotError("input changed or oversized")
        data = b""
        while len(data) <= MAX_INPUT_BYTES:
            chunk = os.read(fd, min(65536, MAX_INPUT_BYTES + 1 - len(data)))
            if not chunk: break
            data += chunk
        if len(data) > MAX_INPUT_BYTES:
            raise PilotError("input oversized")
        try:
            return parse_json_strict(data.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise PilotError("input must be UTF-8") from exc
    finally:
        os.close(fd)


def write_exclusive(path: str | os.PathLike[str], data: str | bytes) -> None:
    p = os.fspath(path)
    try:
        os.lstat(p)
    except FileNotFoundError:
        pass
    else:
        raise PilotError("output exists; overwrite forbidden")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(p, flags, 0o600)
    try:
        payload = data.encode() if isinstance(data, str) else data
        view = memoryview(payload)
        while view:
            n = os.write(fd, view)
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def summary_markdown(report: dict[str, Any]) -> str:
    q = report["scope_result"]
    c = report["commercial_sheet"]
    lines = [
        "# Streaming Rendition QA Pilot", "",
        f"- Qualification: `{q['state']}`",
        f"- Diagnostic reference: `${c['diagnostic_reference']['price_cents']/100:,.2f}` for <= {c['diagnostic_reference']['max_assets']} sanitized metadata assets",
        f"- Integration reference: `${c['integration_reference']['price_cents']/100:,.2f}` — `{c['integration_reference']['stage']}`",
        f"- Receipt: `{report['receipt_sha256']}`", "",
        "## Scope holds", "",
    ]
    lines.extend([f"- `{x}`" for x in q["hold_reasons"]] or ["- none"])
    lines.extend(["", "## Included", ""] + [f"- {x}" for x in c["included"]])
    lines.extend(["", "## Excluded", ""] + [f"- {x}" for x in c["excluded"]])
    lines.extend(["", "## Truth boundary", "", "This is an owner-review diagnostic artifact only. It does not contact a prospect, access providers or media bytes, retrieve DRM secrets, determine rights, transcode, mutate a CDN, publish media, authorize deployment, prove buyer acceptance/payment, or recognize revenue.", ""])
    return "\n".join(lines)


def prospect_csv(report: dict[str, Any]) -> str:
    fields = ["organization", "dedupe_key", "state", "public_evidence_tags", "source_url", "source_sha256", "observed_at_utc", "contact_authority", "buyer_intent_inferred"]
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for row in report["prospects"]:
        out = {k: row[k] for k in fields}
        out["public_evidence_tags"] = ";".join(row["public_evidence_tags"])
        w.writerow(out)
    return buf.getvalue()


def write_artifacts(report: dict[str, Any], out_dir: str | os.PathLike[str]) -> None:
    out = Path(out_dir)
    if out.exists() or out.is_symlink():
        raise PilotError("output directory exists or is symlink")
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    write_exclusive(out / "report.json", canonical_json(report) + "\n")
    write_exclusive(out / "summary.md", summary_markdown(report))
    write_exclusive(out / "prospects.csv", prospect_csv(report))
