from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .audit import CatalogCurrentnessError, canonical_json, compile_currentness, render_csv, render_markdown, verify_receipt


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CatalogCurrentnessError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_nonfinite(token: str) -> Any:
    raise CatalogCurrentnessError(f"non-finite JSON number: {token}")


def _loads_strict(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_strict_object, parse_constant=_reject_nonfinite)
    except CatalogCurrentnessError:
        raise
    except json.JSONDecodeError as exc:
        raise CatalogCurrentnessError(f"invalid JSON: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit cross-family offering catalogs against fresh provider default-branch snapshots.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--as-of", required=True, help="Trusted UTC evaluation instant, e.g. 2026-09-13T10:15:00Z")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = _loads_strict(args.input.read_text(encoding="utf-8"))
        receipt = compile_currentness(raw, as_of=args.as_of)
    except (OSError, CatalogCurrentnessError) as exc:
        print(f"HOLD: {exc}")
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "catalog-currentness.json").write_text(canonical_json(receipt) + "\n", encoding="utf-8")
    (args.out / "catalog-currentness.csv").write_text(render_csv(receipt), encoding="utf-8")
    (args.out / "catalog-currentness.md").write_text(render_markdown(receipt), encoding="utf-8")
    if not verify_receipt(raw, as_of=args.as_of, receipt=receipt):
        print("HOLD: independent receipt recomputation failed")
        return 3
    print(f"{receipt['state']} receipt={receipt['receiptSha256']} findings={receipt['counts']['findings']}")
    return 0 if receipt["state"] == "READY_FOR_HUMAN_CATALOG_CURRENTNESS_REVIEW" else 4


if __name__ == "__main__":
    raise SystemExit(main())
