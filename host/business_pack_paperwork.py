#!/usr/bin/env python3
"""Classify sold-pack paperwork completeness. Not legal advice. Not a Commons gate.

Bryce hub 1788327816.150299: packs help the customer with required
paperwork. Registration, EIN, sales tax, license, insurance, contract.
Slots stay OWNER_UNSET / HOLD_COUNSEL until owner or counsel pastes.
Do not invent Stripe URLs, EINs, or a tjlabs percent.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LAW = ROOT / "ground" / "BUSINESS_PACK_PAPERWORK.json"
REQUIRED = ("registration", "ein", "sales_tax", "license", "insurance", "contract")
STRIPE_FAKE_RE = re.compile(r"(?i)https?://(?:buy|donate)\.stripe\.com/")
EARNINGS_RE = re.compile(
    r"(?i)\bmake\s+\$\d|\bearn\s+\$\d|\bprofit\s+\$\d|"
    r"\bmake \$\d+ this weekend|\bunrealistic result"
)


def load_law(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_LAW
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("law is not an object")
    return data


def _filled(pack: dict[str, Any], name: str) -> bool:
    value = pack.get(name)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return False
        if text.upper() in {"OWNER_UNSET", "HOLD_COUNSEL", "TODO", "TBD"}:
            return False
        return True
    if isinstance(value, list):
        return any(str(item or "").strip() for item in value)
    if isinstance(value, dict):
        status = str(value.get("status") or value.get("value") or "").strip()
        if status.upper() in {"N/A", "NA"} and (
            pack.get("owner_marked_na") or value.get("owner_marked_na")
        ):
            return True
        return _filled({"x": status}, "x") if status else False
    return bool(value)


def classify_paperwork(pack: dict[str, Any] | None) -> dict[str, Any]:
    """Checklist completeness. Invented Stripe URLs are flagged, not gated."""
    law = load_law()
    data = pack if isinstance(pack, dict) else {}
    missing = [name for name in REQUIRED if not _filled(data, name)]
    blob = json.dumps(data, default=str)
    invented_url = bool(STRIPE_FAKE_RE.search(blob)) and not data.get(
        "owner_pasted_checkout"
    )
    ads = str(data.get("ads_copy") or data.get("copy") or "")
    earnings_in_ads = bool(EARNINGS_RE.search(ads))
    if invented_url:
        verdict = "PAPERWORK_INVENTED_URL"
    elif earnings_in_ads:
        verdict = "EARNINGS_IN_ADS"
    elif missing:
        verdict = "PAPERWORK_INCOMPLETE"
    else:
        verdict = "PAPERWORK_OK"
    return {
        "gate": False,
        "commons_admission": False,
        "verdict": verdict,
        "missing": missing,
        "legal_advice": False,
        "hold_counsel": not bool(data.get("counsel_cleared")),
        "not_legal_advice": True,
        "invented_url": invented_url,
        "earnings_in_ads": earnings_in_ads,
        "did_not_invent_percent_or_equity": True,
        "checkout": "NOT_MINTED",
        "agents_spend_ads": False,
        "law_id": str(law.get("id") or ""),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-json", default="", help="JSON paperwork pack object")
    parser.add_argument("--law", default="", help="override law path")
    args = parser.parse_args(argv)
    if args.law:
        load_law(Path(args.law))
    pack: dict[str, Any] = {}
    if args.pack_json:
        loaded = json.loads(args.pack_json)
        if isinstance(loaded, dict):
            pack = loaded
    print(json.dumps(classify_paperwork(pack), indent=2))
    print("", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
