"""Load grounding packs from Lane B JSON files."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Dict, List, Sequence

from charttrace.grounding.schema import GroundingPack, GroundingStatus, assert_pack_complete

_PACKS_DIR = Path(__file__).resolve().parent / "packs"


def _parse_iso(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date") from exc


def load_pack(pack_id: str) -> GroundingPack:
    path = _PACKS_DIR / f"{pack_id}.json"
    if not path.is_file():
        raise KeyError(f"unknown authority pack: {pack_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("pack_id") != pack_id:
        raise ValueError(f"pack_id {data.get('pack_id')!r} does not match file {pack_id}")
    assert_pack_complete(data)
    _parse_iso(data["publication_date"], "publication_date")
    _parse_iso(data["effective_from"], "effective_from")
    if data.get("effective_to"):
        _parse_iso(data["effective_to"], "effective_to")
    _parse_iso(data["retrieval_date"], "retrieval_date")
    amendments = tuple(data.get("historical_amendments") or ())
    return GroundingPack(
        pack_id=data["pack_id"],
        authority_type=data["authority_type"],
        issuer=data["issuer"],
        jurisdiction=data["jurisdiction"],
        publication_date=data["publication_date"],
        effective_from=data["effective_from"],
        effective_to=data.get("effective_to"),
        version_id=data["version_id"],
        care_date_match_rule=data["care_date_match_rule"],
        primary_url=data["primary_url"],
        pinpoint=data["pinpoint"],
        retrieval_date=data["retrieval_date"],
        supported_proposition=data["supported_proposition"],
        supersession=data["supersession"],
        status=GroundingStatus(data["status"]),
        historical_amendments=amendments,
        engineering_anchor_only=bool(data.get("engineering_anchor_only", False)),
        notes=str(data.get("notes", "")),
    )


def load_pack_library() -> Dict[str, GroundingPack]:
    packs: Dict[str, GroundingPack] = {}
    seen_ids: List[str] = []
    for path in sorted(_PACKS_DIR.glob("*.json")):
        pack = load_pack(path.stem)
        if pack.pack_id in packs or pack.pack_id in seen_ids:
            raise ValueError(f"duplicate authority pack id: {pack.pack_id}")
        seen_ids.append(pack.pack_id)
        packs[pack.pack_id] = pack
    return packs


def list_engineering_anchors() -> List[str]:
    return [
        p.pack_id
        for p in load_pack_library().values()
        if p.engineering_anchor_only
    ]


def pack_applies_to_care_dates(pack: GroundingPack, care_start: str, care_end: str) -> bool:
    start = _parse_iso(care_start, "care_date_start")
    end = _parse_iso(care_end, "care_date_end")
    if start > end:
        raise ValueError("care_date_start must be on or before care_date_end")
    effective_from = _parse_iso(pack.effective_from, "effective_from")
    if end < effective_from:
        return False
    if pack.effective_to:
        if start > _parse_iso(pack.effective_to, "effective_to"):
            return False
    return True


def resolve_requested_packs(
    pack_ids: Sequence[str],
    care_start: str,
    care_end: str,
) -> List[str]:
    if len(pack_ids) != len(set(pack_ids)):
        raise ValueError("duplicate authority pack ids in request")
    library = load_pack_library()
    resolved: List[str] = []
    for pack_id in pack_ids:
        if pack_id not in library:
            raise KeyError(f"unknown authority pack: {pack_id}")
        pack = library[pack_id]
        if not pack_applies_to_care_dates(pack, care_start, care_end):
            raise ValueError(
                f"authority pack {pack_id} inapplicable to care dates {care_start}–{care_end}"
            )
        resolved.append(pack_id)
    return resolved


def authority_library_bytes() -> bytes:
    chunks = []
    for path in sorted(_PACKS_DIR.glob("*.json")):
        chunks.append(path.name.encode("utf-8") + b"\n" + path.read_bytes())
    return b"\n".join(chunks)
