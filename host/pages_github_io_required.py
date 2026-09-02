#!/usr/bin/env python3
"""Paths github.io must still serve after a filtered Pages copy.

Live doors already fetch these files. This helper lists them so a Pages
workflow can keep them. It does not deploy, switch Pages source, or write
`.github/workflows/pages-deploy.yml`.

Copy-filter language here is rsync/tar exclude/keep, not admission.
Possessing the link stays authorization. No login.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pages-deploy.yml"
BOARD_JS = ROOT / "board.js"
FREE_SAMPLE = ROOT / "muhlnickel-free-sample.html"
SALES_PACK = ROOT / "revenue" / "muhlnickel_free_sample" / "sales_pack.json"
KEEP_MAP = ROOT / "ground" / "PAGES_KEEP_PATHS.json"

# Three board.js fetch sites YAPPER named. Day/part paths are built at runtime.
BOARD_CHUNK_MARKERS = (
    'fetchSite("chunks/index.json")',
    'fetchSite("chunks/" + encodeURIComponent(day) + ".json")',
    '"chunks/" + encodeURIComponent(day) + "/" + encodeURIComponent(pid) + ".json"',
)

SEED0 = "muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno"
EXPANDING_SEED = "muhl/docs/EXPANDING_SEED.md"
CHUNKS_INDEX = "chunks/index.json"

# Slack-stated Pages except-list (Fable 2026-09-02). Fixture only.
STATED_EXCEPT_DIRS = ("muhl", "chunks", "excerpts", "conflicts", ".github")
STATED_KEEP_PREFIXES = ("muhl/docs",)

_EXCLUDE_FLAG = re.compile(
    r"""--exclude(?:=|\s+)['\"]?(?P<name>[A-Za-z0-9._-]+)""",
    re.IGNORECASE,
)
_INCLUDE_FLAG = re.compile(
    r"""--include(?:=|\s+)['\"]?(?P<path>[A-Za-z0-9._/-]+)""",
    re.IGNORECASE,
)
_HREF_MUHL = re.compile(r"""href=["']\./(muhl/[^"']+)["']""")


def posix(path: str | Path) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def omitted_by_except_keep(
    path: str,
    except_dirs: Iterable[str],
    keep_prefixes: Iterable[str],
) -> bool:
    """True when a top-level except-dir would drop path, unless a keep prefix saves it."""
    rel = posix(path)
    except_set = {d.rstrip("/") for d in except_dirs}
    for keep in keep_prefixes:
        keep_rel = posix(keep).rstrip("/")
        if rel == keep_rel or rel.startswith(keep_rel + "/"):
            return False
    top = rel.split("/", 1)[0]
    return top in except_set


def parse_rsync_except_dirs(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(m.group("name").rstrip("/") for m in _EXCLUDE_FLAG.finditer(text)))


def parse_rsync_keep_prefixes(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(posix(m.group("path")).rstrip("/") for m in _INCLUDE_FLAG.finditer(text)))


def workflow_omits(text: str, path: str) -> bool:
    except_dirs = parse_rsync_except_dirs(text)
    if not except_dirs:
        return False
    return omitted_by_except_keep(path, except_dirs, parse_rsync_keep_prefixes(text))


def covered_by_keep(path: str, keep_entries: Iterable[str]) -> bool:
    """True when path is an exact keep row or sits under a keep directory row."""
    rel = posix(path)
    for keep in keep_entries:
        keep_rel = posix(keep)
        if keep_rel.endswith("/"):
            prefix = keep_rel.rstrip("/")
            if rel == prefix or rel.startswith(prefix + "/"):
                return True
            continue
        if rel == keep_rel:
            return True
    return False


def load_keep_map(root: Path | None = None) -> dict[str, object]:
    here = Path(root) if root is not None else ROOT
    path = here / KEEP_MAP.relative_to(ROOT)
    return json.loads(path.read_text(encoding="utf-8"))


def uncovered_by_keep_map(root: Path | None = None) -> tuple[str, ...]:
    here = Path(root) if root is not None else ROOT
    keep = tuple(load_keep_map(here).get("required_keep_paths") or ())
    return tuple(rel for rel in required_files(here) if not covered_by_keep(rel, keep))


def required_files(root: Path | None = None) -> tuple[str, ...]:
    """Concrete files that must remain on github.io."""
    here = Path(root) if root is not None else ROOT
    pack = json.loads((here / SALES_PACK.relative_to(ROOT)).read_text(encoding="utf-8"))
    proof = pack.get("proof") or {}
    page = (here / FREE_SAMPLE.relative_to(ROOT)).read_text(encoding="utf-8")
    hrefs = tuple(_HREF_MUHL.findall(page))
    ordered: list[str] = []
    for item in (CHUNKS_INDEX, SEED0, EXPANDING_SEED, proof.get("path"), proof.get("existing_doc"), *hrefs):
        if not item:
            continue
        rel = posix(item)
        if rel not in ordered:
            ordered.append(rel)
    return tuple(ordered)


def missing_on_disk(root: Path | None = None) -> tuple[str, ...]:
    here = Path(root) if root is not None else ROOT
    return tuple(rel for rel in required_files(here) if not (here / rel).is_file())


def stated_except_omits(root: Path | None = None) -> tuple[str, ...]:
    return tuple(
        rel
        for rel in required_files(root)
        if omitted_by_except_keep(rel, STATED_EXCEPT_DIRS, STATED_KEEP_PREFIXES)
    )


def live_workflow_omits(root: Path | None = None) -> tuple[str, ...]:
    here = Path(root) if root is not None else ROOT
    path = here / WORKFLOW.relative_to(ROOT)
    if not path.is_file():
        return ()
    text = path.read_text(encoding="utf-8")
    return tuple(rel for rel in required_files(here) if workflow_omits(text, rel))


def report(root: Path | None = None) -> dict[str, object]:
    here = Path(root) if root is not None else ROOT
    required = required_files(here)
    return {
        "required": list(required),
        "missing_on_disk": list(missing_on_disk(here)),
        "stated_except_would_omit": list(stated_except_omits(here)),
        "live_workflow_would_omit": list(live_workflow_omits(here)),
        "uncovered_by_keep_map": list(uncovered_by_keep_map(here)),
        "workflow_present": (here / WORKFLOW.relative_to(ROOT)).is_file(),
        "keep_map_present": (here / KEEP_MAP.relative_to(ROOT)).is_file(),
        "board_chunk_markers": list(BOARD_CHUNK_MARKERS),
        "copy_filter_is_not_admission": True,
        "open_door": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List github.io paths live doors already fetch.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = report(args.root)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    for rel in payload["required"]:
        print(rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
