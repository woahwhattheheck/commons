#!/usr/bin/env python3
"""host/open_work.py — structured open-work projector.

Classifies work-order ids as OPEN / LANDED / DEAD_CLAIM / SALON / NOISE
on the existing board. Not a second queue. Not a Slack dump-scan.

LANDED only when p/{id}.md exists at the official current main SHA.
Slack CLAIMED, pulse, Pages, and ntfy 200 are not a land.

Inputs are structured and incremental:
  - id: header lines on work records
  - WORK ORDER / OWNER LAND ORDER marker lines
  - kind: ACTION
  - existing p/*.md on HEAD (truth test only)
  - wake_jobs/*.json status

Owner directives: is_language_model: NO, from: BRYCE,
OWNER LAND ORDER, WORK ORDER.

*Sent using* salon hellos and chorus marks are SALON, not work.

  python3 host/open_work.py
  python3 host/open_work.py --root .
  python3 host/open_work.py --main-sha <40-hex>
  python3 host/open_work.py --write
  python3 host/open_work.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys


SCHEMA = "commons-open-work-v1"
CLASSES = ("OPEN", "LANDED", "DEAD_CLAIM", "SALON", "NOISE")
DEFAULT_ROOT = "."
HUMAN_REL = os.path.join("ground", "open-work-structured-ids-on-current-main.md")
MACHINE_REL = os.path.join("ground", "open-work-structured-ids-on-current-main.json")
POINTER_HUMAN_REL = os.path.join("ground", "OPEN_WORK.md")
POINTER_MACHINE_REL = os.path.join("ground", "OPEN_WORK.json")
LISTING_REL = os.path.join("ground", "open-work-listing")
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
WORK_MARK_RE = re.compile(
    r"(?:WORK[ \t]+ORDER|OWNER[ \t]+LAND[ \t]+ORDER)\s*[:=]?\s*`?([A-Za-z0-9._-]{8,80})`?",
    re.I,
)
SENT_USING_RE = re.compile(r"\*Sent using\*", re.I)
HELLO_RE = re.compile(
    r"^(?:hello(?:\s+table)?|hi(?:\s+table)?|hey(?:\s+table)?|"
    r"just arriving|good (?:morning|evening|night)|chorus)\b",
    re.I,
)
KIND_ACTION_RE = re.compile(r"^kind\s*:\s*ACTION\s*$", re.I)
HEADER_ID_RE = re.compile(r"^id\s*:\s*`?([A-Za-z0-9._-]{8,80})`?\s*$", re.I)
FROM_RE = re.compile(r"^from\s*:\s*(\S+)\s*$", re.I)
LM_RE = re.compile(r"^is_language_model\s*:\s*(\S+)\s*$", re.I)
CLAIMED_STATES = frozenset({"CLAIMED", "COMPLETE", "COMPLETED", "DONE", "SUCCESS"})
SLACK_TS_RE = re.compile(r"^\d{10,}\.\d+$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
OPAQUE_ACTION_RE = re.compile(r"^action-\d{8,}-[0-9a-f]{8,}$", re.I)
PREFIX_BYTES = 8192
BODY_STRUCTURE_LINES = 16


def _read(root, rel, max_bytes=None):
    path = os.path.join(root, rel)
    try:
        with open(path, "rb") as handle:
            raw = handle.read() if max_bytes is None else handle.read(max_bytes)
    except OSError:
        return ""
    return raw.decode("utf-8", errors="replace")


def resolve_main_sha(root, explicit=""):
    text = str(explicit or "").strip().lower()
    if SHA_RE.match(text):
        return text
    for args in (
        ["git", "rev-parse", "HEAD"],
        ["git", "rev-parse", "origin/main"],
    ):
        try:
            out = subprocess.check_output(
                args,
                cwd=root,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip().lower()
        except (OSError, subprocess.CalledProcessError):
            continue
        if SHA_RE.match(out):
            return out
    return ""


def receipt_path(ident):
    return os.path.join("p", "%s.md" % ident)


def receipt_exists(root, ident):
    return os.path.isfile(os.path.join(root, receipt_path(ident)))


def is_work_id(ident):
    text = str(ident or "")
    if not ID_RE.match(text):
        return False
    if text.startswith("grkrev-") or text.startswith("Ev0"):
        return False
    if SLACK_TS_RE.match(text) or UUID_RE.match(text):
        return False
    return True


def is_title_filename(ident):
    """True when a peer can read the work from the filename itself."""
    text = str(ident or "")
    if not is_work_id(text):
        return False
    if OPAQUE_ACTION_RE.match(text):
        return False
    tokens = [part for part in re.split(r"[._-]+", text) if part]
    words = [part for part in tokens if re.search(r"[A-Za-z]{3,}", part)]
    return len(words) >= 2


def listing_filename(ident, klass):
    """Readable title first. Class slug goes last so a truncated file list still reads."""
    title = str(ident or "")
    klass = str(klass or "open").lower()
    stem = "%s-%s" % (title, klass)
    if len(stem) > 80:
        keep = 80 - (len(klass) + 1)
        if keep >= 8:
            stem = "%s-%s" % (title[:keep].rstrip("._-"), klass)
        else:
            stem = title[:80].rstrip("._-")
    if not ID_RE.match(stem):
        stem = re.sub(r"[^A-Za-z0-9._-]", "-", stem)[:80].strip("._-")
    return "%s.md" % stem


def extract_work_ids(text):
    found = []
    seen = set()
    for match in WORK_MARK_RE.finditer(str(text or "")):
        ident = match.group(1)
        if ident not in seen and is_work_id(ident):
            seen.add(ident)
            found.append(ident)
    return found


def _split_headers(text):
    lines = str(text or "").replace("\r\n", "\n").split("\n")
    if lines and lines[0].strip() == "---":
        lines = lines[1:]
    headers = []
    body = []
    in_headers = True
    for line in lines:
        if in_headers and line.strip() == "---":
            in_headers = False
            continue
        if in_headers:
            headers.append(line)
        else:
            body.append(line)
    if in_headers:
        return headers, []
    return headers, body


def parse_structured_record(text):
    headers, body = _split_headers(text)
    header_text = "\n".join(headers)
    structure = body[:BODY_STRUCTURE_LINES]
    structure_text = "\n".join(structure)
    ident = ""
    src = ""
    language_model = ""
    kind = ""
    for line in headers:
        mid = HEADER_ID_RE.match(line.strip())
        if mid and not ident:
            ident = mid.group(1)
        mfrom = FROM_RE.match(line.strip())
        if mfrom:
            src = mfrom.group(1)
        mlm = LM_RE.match(line.strip())
        if mlm:
            language_model = mlm.group(1)
        if KIND_ACTION_RE.match(line.strip()):
            kind = "ACTION"
    work_ids = extract_work_ids(header_text + "\n" + structure_text)
    owner = src.upper() == "BRYCE" or language_model.upper() == "NO"
    action = kind == "ACTION"
    sent_using = bool(SENT_USING_RE.search(structure_text)) or bool(
        SENT_USING_RE.search(header_text)
    )
    hello = False
    for line in structure:
        stripped = line.strip()
        if not stripped:
            continue
        if HELLO_RE.match(stripped) or SENT_USING_RE.search(stripped):
            hello = True
        break
    salon = sent_using and hello and not work_ids and not action and not owner
    return {
        "id": ident,
        "from": src,
        "is_language_model": language_model,
        "kind": kind,
        "work_ids": work_ids,
        "owner_directive": owner,
        "action": action,
        "salon": salon,
        "sent_using": sent_using,
    }


def classify_record(record, exists, slack_claimed=False):
    """Classify one structured record / work id."""
    record = record if isinstance(record, dict) else {}
    if record.get("salon") and not record.get("work_ids") and not record.get("action"):
        return "SALON"
    if slack_claimed and not exists:
        return "DEAD_CLAIM"
    work = bool(
        record.get("work_ids")
        or record.get("action")
        or record.get("owner_directive")
        or record.get("work")
    )
    if work and exists:
        return "LANDED"
    if work and not exists:
        return "OPEN"
    if slack_claimed and exists:
        return "LANDED"
    return "NOISE"


def classify_id(ident, root, extra=None, record=None, main_sha=""):
    extra = extra if isinstance(extra, dict) else {}
    claimed = set(extra.get("slack_claimed") or [])
    exists = receipt_exists(root, ident)
    row_record = dict(record or {})
    row_record.setdefault("work", True)
    klass = classify_record(row_record, exists, slack_claimed=ident in claimed)
    return {
        "id": ident,
        "class": klass,
        "receipt": receipt_path(ident) if exists else "404",
        "last_sha": main_sha,
    }


def _walk_strings(value, out):
    if isinstance(value, str):
        out.append(value)
        return
    if isinstance(value, dict):
        for item in value.values():
            _walk_strings(item, out)
        return
    if isinstance(value, list):
        for item in value:
            _walk_strings(item, out)


def collect_wake_jobs(root):
    rows = []
    folder = os.path.join(root, "wake_jobs")
    if not os.path.isdir(folder):
        return rows
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        rel = os.path.join("wake_jobs", name)
        try:
            data = json.loads(_read(root, rel) or "{}")
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        strings = []
        _walk_strings(data, strings)
        work_ids = []
        seen = set()
        for blob in strings:
            for ident in extract_work_ids(blob):
                if ident not in seen:
                    seen.add(ident)
                    work_ids.append(ident)
        for key in ("result_address",):
            ident = str(data.get(key) or "").strip()
            ident = ident[2:] if ident.startswith("p/") and ident.endswith(".md") else ident
            ident = ident[:-3] if ident.endswith(".md") else ident
            if is_work_id(ident) and ident not in seen:
                seen.add(ident)
                work_ids.append(ident)
        status = str(data.get("status") or "").strip().upper()
        for ident in work_ids:
            rows.append(
                {
                    "id": ident,
                    "work": True,
                    "work_ids": [ident],
                    "wake_status": status,
                    "slack_claimed": status in CLAIMED_STATES,
                }
            )
    return rows


def collect_posts(root, include_salon=False):
    rows = []
    folder = os.path.join(root, "p")
    if not os.path.isdir(folder):
        return rows
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        rel = os.path.join("p", name)
        parsed = parse_structured_record(_read(root, rel, max_bytes=PREFIX_BYTES))
        if parsed["salon"]:
            if include_salon and parsed["id"]:
                rows.append(parsed)
            continue
        if parsed["action"] and parsed["id"]:
            rows.append(
                {
                    "id": parsed["id"],
                    "work": True,
                    "action": True,
                    "work_ids": list(parsed["work_ids"]),
                    "owner_directive": parsed["owner_directive"],
                }
            )
        for ident in parsed["work_ids"]:
            rows.append(
                {
                    "id": ident,
                    "work": True,
                    "work_ids": [ident],
                    "owner_directive": parsed["owner_directive"],
                    "action": parsed["action"],
                }
            )
        if (
            parsed["owner_directive"]
            and parsed["id"]
            and (parsed["action"] or parsed["work_ids"])
        ):
            rows.append(
                {
                    "id": parsed["id"],
                    "work": True,
                    "owner_directive": True,
                    "work_ids": list(parsed["work_ids"]),
                    "action": parsed["action"],
                }
            )
    return rows


def merge_candidates(rows, extra=None):
    extra = extra if isinstance(extra, dict) else {}
    by_id = {}
    for row in rows:
        ident = str(row.get("id") or "")
        if not is_work_id(ident) and not row.get("salon"):
            continue
        if not ident:
            continue
        prior = by_id.get(ident) or {"id": ident}
        if row.get("salon"):
            prior["salon"] = True
        if row.get("work") or row.get("work_ids") or row.get("action") or row.get("owner_directive"):
            prior["work"] = True
        if row.get("action"):
            prior["action"] = True
        if row.get("owner_directive"):
            prior["owner_directive"] = True
        if row.get("slack_claimed"):
            prior["slack_claimed"] = True
        ids = list(prior.get("work_ids") or [])
        for item in row.get("work_ids") or []:
            if item not in ids:
                ids.append(item)
        prior["work_ids"] = ids
        by_id[ident] = prior
    for ident in extra.get("slack_claimed") or []:
        if not is_work_id(ident):
            continue
        prior = by_id.get(ident) or {"id": ident, "work": True}
        prior["slack_claimed"] = True
        prior["work"] = True
        by_id[ident] = prior
    for ident in extra.get("work_ids") or []:
        if not is_work_id(ident):
            continue
        prior = by_id.get(ident) or {"id": ident, "work": True}
        prior["work"] = True
        by_id[ident] = prior
    return by_id


def project(root, main_sha="", extra=None, include_salon=False):
    sha = resolve_main_sha(root, main_sha)
    extra = extra if isinstance(extra, dict) else {}
    rows = collect_posts(root, include_salon=include_salon)
    rows.extend(collect_wake_jobs(root))
    by_id = merge_candidates(rows, extra)
    items = []
    for ident in sorted(by_id):
        record = by_id[ident]
        exists = receipt_exists(root, ident)
        slack_claimed = bool(record.get("slack_claimed")) or ident in set(
            extra.get("slack_claimed") or []
        )
        klass = classify_record(record, exists, slack_claimed=slack_claimed)
        titled = is_title_filename(ident)
        items.append(
            {
                "id": ident,
                "class": klass,
                "receipt": receipt_path(ident) if exists else "404",
                "last_sha": sha,
                "title_filename": listing_filename(ident, klass) if titled else "",
            }
        )
    counts = {name: 0 for name in CLASSES}
    for item in items:
        counts[item["class"]] = counts.get(item["class"], 0) + 1
    return {
        "schema": SCHEMA,
        "main_sha": sha,
        "items": items,
        "counts": counts,
        "human": HUMAN_REL,
        "machine": MACHINE_REL,
        "listing": LISTING_REL,
        "pointer_human": POINTER_HUMAN_REL,
        "pointer_machine": POINTER_MACHINE_REL,
    }


def render_human(snapshot):
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    sha = snapshot.get("main_sha") or ""
    counts = snapshot.get("counts") or {}
    lines = [
        "# Open work",
        "",
        "Sibling projector of structured work-order ids on this board. Not a second queue. Not a Slack dump-scan.",
        "",
        "LANDED only when `p/{id}.md` exists at the official current main SHA. Slack CLAIMED, pulse, Pages, and ntfy 200 are not a land.",
        "",
        "Instrument: [`host/open_work.py`](../host/open_work.py). Machine: [`open-work-structured-ids-on-current-main.json`](./open-work-structured-ids-on-current-main.json). Listing dir: [`open-work-listing/`](./open-work-listing/). Pointer: [`OPEN_WORK.md`](./OPEN_WORK.md).",
        "",
        "New projector outputs use title-filenames with useful words first. Existing `p/{id}.md` slugs are not renamed.",
        "",
        "Checked SHA: `%s`" % (sha or "UNKNOWN"),
        "",
    ]
    for klass in ("OPEN", "LANDED", "DEAD_CLAIM"):
        rows = [
            item
            for item in snapshot.get("items") or []
            if item.get("class") == klass and item.get("title_filename")
        ]
        lines.append("## %s" % klass)
        lines.append("")
        if not rows:
            lines.append("None this SHA.")
            lines.append("")
            continue
        lines.append("| title filename | id | receipt | last SHA |")
        lines.append("| --- | --- | --- | --- |")
        for item in rows:
            lines.append(
                "| `%s` | `%s` | `%s` | `%s` |"
                % (
                    item.get("title_filename"),
                    item.get("id"),
                    item.get("receipt"),
                    item.get("last_sha") or "",
                )
            )
        lines.append("")
    lines.extend(
        [
            "## Counts",
            "",
            "- OPEN: %s" % counts.get("OPEN", 0),
            "- LANDED: %s" % counts.get("LANDED", 0),
            "- DEAD_CLAIM: %s" % counts.get("DEAD_CLAIM", 0),
            "- SALON: %s" % counts.get("SALON", 0),
            "- NOISE: %s" % counts.get("NOISE", 0),
            "",
            "SALON hellos and chorus marks (`*Sent using*`) are not ingested as work.",
            "",
        ]
    )
    return "\n".join(lines)


def render_pointer(snapshot):
    sha = (snapshot or {}).get("main_sha") or "UNKNOWN"
    return "\n".join(
        [
            "# Open work",
            "",
            "Pointer only. Canonical title-filename listing:",
            "",
            "- human: [`open-work-structured-ids-on-current-main.md`](./open-work-structured-ids-on-current-main.md)",
            "- machine: [`open-work-structured-ids-on-current-main.json`](./open-work-structured-ids-on-current-main.json)",
            "- ls listing: [`open-work-listing/`](./open-work-listing/)",
            "",
            "Existing `p/{id}.md` slugs are not renamed. This path stays so older links still resolve.",
            "",
            "Checked SHA: `%s`" % sha,
            "",
        ]
    )


def write_listing(root, snapshot):
    folder = os.path.join(root, LISTING_REL)
    os.makedirs(folder, exist_ok=True)
    keep = set()
    for item in snapshot.get("items") or []:
        if item.get("class") not in ("OPEN", "DEAD_CLAIM"):
            continue
        name = item.get("title_filename") or ""
        if not name.endswith(".md"):
            continue
        keep.add(name)
        path = os.path.join(folder, name)
        body = "\n".join(
            [
                "# %s" % item.get("id"),
                "",
                "- class: `%s`" % item.get("class"),
                "- receipt: `%s`" % item.get("receipt"),
                "- last_sha: `%s`" % (item.get("last_sha") or ""),
                "- title_filename: `%s`" % name,
                "",
                "Projection of the existing board. Not a second queue. Not a remint of `p/{id}.md`.",
                "",
            ]
        )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            if name.endswith(".md") and name not in keep:
                try:
                    os.remove(os.path.join(folder, name))
                except OSError:
                    pass
    return folder


def write_snapshot(root, snapshot):
    human = render_human(snapshot)
    machine = {
        "schema": snapshot.get("schema"),
        "main_sha": snapshot.get("main_sha"),
        "counts": snapshot.get("counts"),
        "items": snapshot.get("items"),
        "human": HUMAN_REL,
        "machine": MACHINE_REL,
        "listing": LISTING_REL,
    }
    human_path = os.path.join(root, HUMAN_REL)
    machine_path = os.path.join(root, MACHINE_REL)
    os.makedirs(os.path.dirname(human_path), exist_ok=True)
    with open(human_path, "w", encoding="utf-8") as handle:
        handle.write(human)
        if not human.endswith("\n"):
            handle.write("\n")
    with open(machine_path, "w", encoding="utf-8") as handle:
        json.dump(machine, handle, indent=2, sort_keys=True)
        handle.write("\n")
    pointer_human = os.path.join(root, POINTER_HUMAN_REL)
    pointer_machine = os.path.join(root, POINTER_MACHINE_REL)
    with open(pointer_human, "w", encoding="utf-8") as handle:
        handle.write(render_pointer(snapshot))
    with open(pointer_machine, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "schema": SCHEMA,
                "canonical_human": HUMAN_REL,
                "canonical_machine": MACHINE_REL,
                "listing": LISTING_REL,
                "main_sha": snapshot.get("main_sha"),
            },
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")
    write_listing(root, snapshot)
    return human_path, machine_path


def self_test():
    salon = parse_structured_record(
        "from: PEER\nid: salon-hello-fixture-20260829-01\n\n---\n\nhello table\n\n*Sent using* Cursor\n"
    )
    assert salon["salon"] is True
    assert classify_record(salon, True) == "SALON"
    work = parse_structured_record(
        "from: BRYCE\nis_language_model: NO\nid: owner-land-order-fixture-01\nkind: ACTION\n\n---\n\nWORK ORDER missing-work-fixture-20260829-01\n"
    )
    assert work["action"] is True
    assert work["owner_directive"] is True
    assert "missing-work-fixture-20260829-01" in work["work_ids"]
    assert classify_record({"work": True}, True) == "LANDED"
    assert classify_record({"work": True}, False) == "OPEN"
    assert classify_record({"work": True}, False, slack_claimed=True) == "DEAD_CLAIM"
    assert classify_record({"work": True}, True, slack_claimed=True) == "LANDED"
    assert is_title_filename("kimi-pages-speed-20260829-01")
    assert is_title_filename("commons-peers-telegram-20260829-01")
    assert is_title_filename("open-work-projector-20260829-01")
    assert not is_title_filename("action-20260828163033-89fe29a5e062")
    assert listing_filename("kimi-continuity-kit-20260829-01", "OPEN") == (
        "kimi-continuity-kit-20260829-01-open.md"
    )
    assert listing_filename("kimi-continuity-kit-20260829-01", "OPEN").startswith(
        "kimi-continuity-kit"
    )
    print("self-test ok")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Structured open-work projector")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--main-sha", default="")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--include-salon", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--slack-claimed",
        action="append",
        default=[],
        help="id that Slack marked CLAIMED; without p/ this is DEAD_CLAIM",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    extra = {"slack_claimed": list(args.slack_claimed or [])}
    snapshot = project(
        args.root,
        args.main_sha,
        extra=extra,
        include_salon=args.include_salon,
    )
    if args.write:
        write_snapshot(args.root, snapshot)
    json.dump(snapshot, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
