"""Extract acceptance criteria and deliverable items from the real ACCEPTANCE_EXHIBIT.md.

Why parse instead of transcribe: a hand-copied criteria list silently rots the moment
somebody edits the exhibit, and an acceptance index that describes a document which no
longer exists is worse than no index. This reads the live file and records its digest,
so drift is reported rather than hidden.

Python 3 standard library only.
"""
import hashlib
import os
import re

# The exhibit lives in another seat's lane. This package only ever READS it.
DEFAULT_EXHIBIT = os.path.join(
    "..", "uiowa_rfq_18649_workshare", "ACCEPTANCE_EXHIBIT.md")

_SECTION = re.compile(r"^###\s+(\d+)\.(\d+)\s+(.*)$")
_H2 = re.compile(r"^##\s+(\d+)\.\s+(.*)$")
_NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$")
_BULLET = re.compile(r"^[-*]\s+(.*)$")


def _clean(text):
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip().rstrip(";").strip()


def parse_exhibit(path):
    """Return {'digest', 'path', 'criteria': [...], 'deliverables': [...], 'commercial_status'}."""
    with open(path, "rb") as fh:
        raw = fh.read()
    digest = hashlib.sha256(raw).hexdigest()
    lines = raw.decode("utf-8").splitlines()

    criteria, deliverables = [], []
    sec_major = sec_minor = None
    sec_title = ""
    in_h2 = None

    for line in lines:
        h2 = _H2.match(line)
        if h2:
            in_h2 = int(h2.group(1))
            sec_major = sec_minor = None
            continue
        sec = _SECTION.match(line)
        if sec:
            sec_major, sec_minor = int(sec.group(1)), int(sec.group(2))
            sec_title = _clean(sec.group(3))
            continue
        if sec_major is None:
            continue

        num = _NUMBERED.match(line.strip())
        if num and sec_major == 5:
            criteria.append({
                "criterion_id": f"AC-{sec_major}.{sec_minor}.{num.group(1)}",
                "package": sec_title,
                "section": f"{sec_major}.{sec_minor}",
                "ordinal": int(num.group(1)),
                "text": _clean(num.group(2)),
            })
            continue
        bullet = _BULLET.match(line.strip())
        if bullet and sec_major == 4:
            deliverables.append({
                "deliverable_id": f"DL-{sec_major}.{sec_minor}.{len([d for d in deliverables if d['section'] == f'{sec_major}.{sec_minor}']) + 1}",
                "package": sec_title,
                "section": f"{sec_major}.{sec_minor}",
                "text": _clean(bullet.group(1)),
            })

    status = "UNKNOWN"
    for line in lines:
        if "Commercial status" in line:
            m = re.search(r"Commercial status:\**\s*\**([A-Z /]+)\**", line)
            if m:
                status = m.group(1).strip()
            break

    return {
        "path": path,
        "digest_sha256": digest,
        "commercial_status": status,
        "criteria": criteria,
        "deliverables": deliverables,
    }


if __name__ == "__main__":
    import json
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXHIBIT
    print(json.dumps(parse_exhibit(p), indent=2))
