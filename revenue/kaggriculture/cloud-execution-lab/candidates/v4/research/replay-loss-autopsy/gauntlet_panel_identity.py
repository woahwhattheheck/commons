#!/usr/bin/env python3
"""Fail-closed opponent-family/source identity reducer for TITAN V4 gauntlets.

This module does not run games and does not infer semantic equivalence from score
similarity.  It only consumes explicit family/variant/source declarations and,
when outcomes are present, reports raw-label, source-balanced and family-balanced
views so repeated labels cannot silently multiply one strategy family's weight.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
import json
from pathlib import Path
import re
import sys
from typing import Any

SCHEMA = "titan.gauntlet.panel_identity.v1"
KINDS = {"recorded_trace", "archetype", "live_agent", "mirror"}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class IdentityError(ValueError):
    """Invalid or ambiguous identity input; callers must fail closed."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise IdentityError(message)


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise IdentityError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(raw: str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=strict_object)
    except IdentityError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise IdentityError(f"invalid JSON: {exc}") from exc


def obj(value: Any, name: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{name}: expected object")
    return value


def nonempty_rows(value: Any, name: str) -> list[Any]:
    require(isinstance(value, list) and bool(value), f"{name}: expected nonempty list")
    return value


def text(value: Any, name: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{name}: expected nonempty text")
    return value


def integer(value: Any, name: str, minimum: int | None = None) -> int:
    require(type(value) is int, f"{name}: expected integer, not bool/float")
    require(minimum is None or value >= minimum, f"{name}: below minimum {minimum}")
    return value


def digest(value: Any, name: str) -> str:
    require(isinstance(value, str) and SHA256.fullmatch(value) is not None,
            f"{name}: expected lowercase SHA-256")
    return value


def _decimal_mean(values: list[int | Decimal]) -> Decimal | None:
    if not values:
        return None
    width = max(len(str(v)) for v in values)
    with localcontext() as ctx:
        ctx.prec = max(50, width + len(str(len(values))) + 40)
        return sum((Decimal(v) for v in values), Decimal(0)) / Decimal(len(values))


def _ratio(numerator: int, denominator: int) -> Decimal:
    width = max(len(str(abs(numerator))), len(str(abs(denominator))))
    with localcontext() as ctx:
        ctx.prec = max(50, width + 40)
        return Decimal(numerator) / Decimal(denominator)


def _fmt(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _outcome(row: dict[str, Any], ident: str) -> dict[str, int] | None:
    keys = ("wins", "losses", "draws", "total_margin")
    present = [key in row for key in keys]
    require(all(present) or not any(present),
            f"{ident}: outcomes must provide wins/losses/draws/total_margin together")
    if not any(present):
        return None
    wins = integer(row["wins"], f"{ident}.wins", 0)
    losses = integer(row["losses"], f"{ident}.losses", 0)
    draws = integer(row["draws"], f"{ident}.draws", 0)
    total_margin = integer(row["total_margin"], f"{ident}.total_margin")
    games = wins + losses + draws
    require(games > 0, f"{ident}: outcome has zero games")
    return {"wins": wins, "losses": losses, "draws": draws,
            "total_margin": total_margin, "games": games}


def audit(document: dict[str, Any]) -> dict[str, Any]:
    document = obj(document, "root")
    require(document.get("schema") == SCHEMA, f"schema must equal {SCHEMA}")
    panel_id = text(document.get("panel_id"), "panel_id")
    entries: list[dict[str, Any]] = []
    ids: set[str] = set()
    family_variants: set[tuple[str, str]] = set()
    source_owner: dict[str, tuple[str, str]] = {}
    outcomes_present: bool | None = None

    for raw in nonempty_rows(document.get("opponents"), "opponents"):
        row = obj(raw, "opponent")
        ident = text(row.get("id"), "opponent.id")
        require(ident not in ids, f"duplicate opponent id: {ident}")
        ids.add(ident)
        kind = text(row.get("kind"), f"{ident}.kind")
        require(kind in KINDS, f"{ident}: invalid kind {kind}")
        family = text(row.get("family_id"), f"{ident}.family_id")
        variant = text(row.get("variant_id"), f"{ident}.variant_id")
        source = digest(row.get("source_sha256"), f"{ident}.source_sha256")
        fv = (family, variant)
        require(fv not in family_variants,
                f"duplicate variant_id {variant!r} inside family {family!r}")
        family_variants.add(fv)
        owner = source_owner.get(source)
        current_owner = (family, kind)
        require(owner is None or owner == current_owner,
                f"source {source} is assigned to conflicting family/kind: {owner} vs {current_owner}")
        source_owner[source] = current_owner
        outcome = _outcome(row, ident)
        has_outcome = outcome is not None
        if outcomes_present is None:
            outcomes_present = has_outcome
        require(outcomes_present == has_outcome,
                "panel mixes identity-only and outcome-bearing opponents")
        entry: dict[str, Any] = {"id": ident, "kind": kind, "family_id": family,
                                 "variant_id": variant, "source_sha256": source}
        if outcome:
            entry.update(outcome)
            entry["mean_margin"] = _ratio(outcome["total_margin"], outcome["games"])
            entry["win_rate"] = _ratio(outcome["wins"], outcome["games"])
            entry["loss_rate"] = _ratio(outcome["losses"], outcome["games"])
            entry["draw_rate"] = _ratio(outcome["draws"], outcome["games"])
        entries.append(entry)

    family_kinds: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        family_kinds[entry["family_id"]].add(entry["kind"])
    for family, kinds in family_kinds.items():
        require("mirror" not in kinds or kinds == {"mirror"},
                f"family {family!r} mixes mirror and non-mirror identities")

    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_family[entry["family_id"]].append(entry)
        by_source[entry["source_sha256"]].append(entry)

    alias_groups: list[dict[str, Any]] = []
    for source in sorted(by_source):
        members = sorted(entry["id"] for entry in by_source[source])
        if len(members) > 1:
            alias_groups.append({"source_sha256": source,
                                 "family_id": by_source[source][0]["family_id"],
                                 "kind": by_source[source][0]["kind"],
                                 "labels": members, "alias_excess": len(members) - 1})

    families: list[dict[str, Any]] = []
    for family in sorted(by_family):
        members = by_family[family]
        sources = sorted({entry["source_sha256"] for entry in members})
        family_row: dict[str, Any] = {
            "family_id": family,
            "kind": sorted({entry["kind"] for entry in members}),
            "label_count": len(members),
            "unique_source_count": len(sources),
            "alias_excess": len(members) - len(sources),
            "labels": sorted(entry["id"] for entry in members),
            "source_sha256": sources,
        }
        if outcomes_present:
            source_metrics: list[dict[str, Decimal]] = []
            for source in sources:
                rows_for_source = by_source[source]
                source_metrics.append({
                    metric: _decimal_mean([entry[metric] for entry in rows_for_source])
                    for metric in ("mean_margin", "win_rate", "loss_rate", "draw_rate")
                })
            for metric in ("mean_margin", "win_rate", "loss_rate", "draw_rate"):
                family_row[metric] = _fmt(_decimal_mean([values[metric] for values in source_metrics]))
        families.append(family_row)

    result: dict[str, Any] = {
        "schema": "titan.gauntlet.panel_identity.audit.v1",
        "panel_id": panel_id,
        "raw_label_count": len(entries),
        "family_count": len(by_family),
        "unique_source_count": len(by_source),
        "alias_excess": len(entries) - len(by_source),
        "multiplicity": {family: len(members) for family, members in sorted(by_family.items())
                         if len(members) > 1},
        "alias_groups": alias_groups,
        "families": families,
        "outcomes_present": bool(outcomes_present),
        "promotion_decision": "NOT_ASSESSED",
    }

    if outcomes_present:
        metrics = ("mean_margin", "win_rate", "loss_rate", "draw_rate")
        raw_label = {metric: _fmt(_decimal_mean([entry[metric] for entry in entries]))
                     for metric in metrics}
        source_values: dict[str, list[Decimal]] = {metric: [] for metric in metrics}
        for source in sorted(by_source):
            source_entries = by_source[source]
            for metric in metrics:
                value = _decimal_mean([entry[metric] for entry in source_entries])
                require(value is not None, "internal: empty source group")
                source_values[metric].append(value)
        source_balanced = {metric: _fmt(_decimal_mean(source_values[metric])) for metric in metrics}
        family_balanced: dict[str, str | None] = {}
        for metric in metrics:
            family_balanced[metric] = _fmt(_decimal_mean([Decimal(row[metric]) for row in families]))
        result["views"] = {
            "raw_game_weighted_counts": {
                "games": sum(entry["games"] for entry in entries),
                "wins": sum(entry["wins"] for entry in entries),
                "losses": sum(entry["losses"] for entry in entries),
                "draws": sum(entry["draws"] for entry in entries),
                "total_margin": sum(entry["total_margin"] for entry in entries),
            },
            "raw_label_mean": raw_label,
            "source_balanced_mean": source_balanced,
            "family_balanced_mean": family_balanced,
        }
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        document = loads_strict(args.input.read_text(encoding="utf-8"))
        report = audit(document)
        encoded = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.output:
            args.output.write_text(encoded, encoding="utf-8")
        else:
            sys.stdout.write(encoded)
        return 0
    except (IdentityError, OSError) as exc:
        sys.stderr.write(f"gauntlet-panel-identity: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
