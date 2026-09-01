"""Load grounding packs from Lane B JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from charttrace.grounding.schema import GroundingPack, GroundingStatus, assert_pack_complete

_PACKS_DIR = Path(__file__).resolve().parent / "packs"


def load_pack(pack_id: str) -> GroundingPack:
    path = _PACKS_DIR / f"{pack_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert_pack_complete(data)
    return GroundingPack(
        pack_id=data["pack_id"],
        authority_type=data["authority_type"],
        issuer=data["issuer"],
        jurisdiction=data["jurisdiction"],
        effective_from=data["effective_from"],
        effective_to=data.get("effective_to"),
        care_date_match_rule=data["care_date_match_rule"],
        primary_url=data["primary_url"],
        pinpoint=data["pinpoint"],
        retrieval_date=data["retrieval_date"],
        supported_proposition=data["supported_proposition"],
        supersession=data["supersession"],
        status=GroundingStatus(data["status"]),
        engineering_anchor_only=bool(data.get("engineering_anchor_only", False)),
        notes=str(data.get("notes", "")),
    )


def load_pack_library() -> Dict[str, GroundingPack]:
    packs: Dict[str, GroundingPack] = {}
    for path in sorted(_PACKS_DIR.glob("*.json")):
        pack = load_pack(path.stem)
        packs[pack.pack_id] = pack
    return packs


def list_engineering_anchors() -> List[str]:
    return [
        p.pack_id
        for p in load_pack_library().values()
        if p.engineering_anchor_only
    ]
