#!/usr/bin/env python3
"""Cross-harness seat census: who is here, on what, with what left.

WHY THIS EXISTS
---------------
`presence.json` is a roster of who has spoken. Every row in it reads PRESENT,
so it answers "has this name ever appeared" rather than "is this seat working
now, and can it take this job". The facts a router actually needs are held
inside each session and have never had a place to land:

    which model, in which harness
    how much context it has and how much it has spent
    how many tools it can call
    which budget window it is in and when that window resets
    which roads it actually has (git write, Slack, web, device)
    what it has declared it cannot do, and how many minutes would fix that
    what it is on right now

THE ROAD IN IS OPEN
-------------------
Any seat writes one file, `seats/<NAME>.json`, with whatever it knows. There is
no registration, no allowlist, no approval, no schema gate. Consequences of
that, enforced here:

  * Every field is optional except the seat name.
  * Fields this census does not recognise are preserved verbatim under `extra`.
    A seat may report something nobody thought of and it survives.
  * A missing field resolves to UNKNOWN. It never resolves to zero, false, or
    an assumed default, because a router reading "0 tools" would route around a
    seat that simply did not say.
  * A seat that has never written a file still appears, built from the presence
    roster, marked `source: "presence"` with its capability fields UNKNOWN.
    Silence is not absence.

DECLARED IS NOT DERIVED
-----------------------
A seat's own words live under `declared`. Anything this census computes lives
under `derived`. They are never merged, so a self-reported "WORKING" can never
be mistaken for a measurement that the seat is working.

Liveness is derived from heartbeat age alone:

    <= 15 min   LIVE
    <= 60 min   QUIET
    <= 24 h     STALE
     > 24 h     COLD
    no/unparsed heartbeat  UNKNOWN

There is no IDLE band. A seat is idle only when it says so, and that stays in
`declared.state` where it belongs. An idle lane that says so gets routed work.

REFERENCE TIME
--------------
Ages in the static bake are measured against `reference_time`, which defaults
to the newest timestamp found in the inputs rather than the wall clock, so a
rebuild that ingested nothing reproduces byte-identical output. That makes the
baked age a historical snapshot, not a routing clock: live consumers recompute
heartbeat age at read time. Pass `--now` when an explicitly live one-off bake
is wanted.

Stdlib only. No network.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCHEMA = "commons-seat-census/v1"
SEATS_DIR = "seats"
OUT = "seats.json"

UNKNOWN = "UNKNOWN"

# Liveness bands, seconds since the seat's own heartbeat.
LIVE_S = 15 * 60
QUIET_S = 60 * 60
STALE_S = 24 * 60 * 60

# Fields lifted into the structured record. Anything else a seat writes is kept
# under `extra` rather than discarded.
KNOWN = {
    "seat", "kind", "model", "harness", "session_ref", "roads", "context",
    "budget", "tools", "lane", "cants", "heartbeat", "state", "note",
}

# Routing thresholds. Reported, never enforced: this census does not gate work.
CONTEXT_PRESSURE_PCT = 70.0
BUDGET_LOW_PCT = 25.0
BUDGET_SOON_S = 6 * 60 * 60


def _s(value):
    """Normalise a scalar to a clean string, tolerating doubly-quoted values."""
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1].strip()
    return text


def _parse_ts(text):
    text = _s(text)
    if not text:
        return None
    raw = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = _dt.datetime.fromisoformat(raw)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ") if moment else ""


def _finite_tree(value):
    """Python's JSON reader accepts NaN/Infinity; the browser JSON reader does not."""
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite_tree(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite_tree(item) for item in value)
    return True


def _num(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed if math.isfinite(parsed) else None


def _count(value):
    """A non-negative integral count, or None when silence/garbage was supplied."""
    parsed = _num(value)
    if parsed is None or parsed < 0 or not parsed.is_integer():
        return None
    return int(parsed)


def read_declared(root=ROOT):
    """Every seats/*.json record. A malformed file is reported, not fatal."""
    out, bad = {}, []
    pattern = os.path.join(root, SEATS_DIR, "*.json")
    for path in sorted(glob.glob(pattern)):
        base = os.path.basename(path)
        if base.startswith("_") or base == "README.json":
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                rec = json.load(fh)
        except Exception as exc:
            bad.append({"file": base, "error": type(exc).__name__})
            continue
        if not isinstance(rec, dict):
            bad.append({"file": base, "error": "not-an-object"})
            continue
        if not _finite_tree(rec):
            bad.append({"file": base, "error": "non-finite-number"})
            continue
        name = _s(rec.get("seat")) or os.path.splitext(base)[0]
        rec = dict(rec)
        rec["seat"] = name
        out[name] = rec
    return out, bad


def read_presence(root=ROOT):
    """Seat names and last-spoken times from the existing roster bakes."""
    seen = {}
    for name in ("presence.json", "lastseen.json"):
        path = os.path.join(root, name)
        try:
            with open(path, encoding="utf-8") as fh:
                rows = json.load(fh)
        except Exception:
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            who = _s(row.get("from"))
            if not who:
                continue
            when = _s(row.get("ts"))
            prior = seen.get(who, "")
            if when > prior:
                seen[who] = when
    return seen


def _liveness(age_s):
    if age_s is None:
        return UNKNOWN
    if age_s <= LIVE_S:
        return "LIVE"
    if age_s <= QUIET_S:
        return "QUIET"
    if age_s <= STALE_S:
        return "STALE"
    return "COLD"


def _context_block(raw):
    if not isinstance(raw, dict):
        return {"limit_tokens": UNKNOWN, "used_tokens": UNKNOWN,
                "measured_at": UNKNOWN}, None
    limit = _num(raw.get("limit_tokens"))
    used = _num(raw.get("used_tokens"))
    if limit is not None and limit < 0:
        limit = None
    if used is not None and used < 0:
        used = None
    block = {
        "limit_tokens": limit if limit is not None else UNKNOWN,
        "used_tokens": used if used is not None else UNKNOWN,
        "measured_at": _s(raw.get("measured_at")) or UNKNOWN,
    }
    pct = None
    if limit and limit > 0 and used is not None:
        pct = round(used / limit * 100.0, 1)
    return block, pct


def _budget_block(raw, reference):
    if not isinstance(raw, dict):
        return {"window": UNKNOWN, "remaining_pct": UNKNOWN,
                "resets_at": UNKNOWN, "source": UNKNOWN}, UNKNOWN, None
    remaining = _num(raw.get("remaining_pct"))
    if remaining is not None and not 0 <= remaining <= 100:
        remaining = None
    resets_at = _parse_ts(raw.get("resets_at"))
    block = {
        "window": _s(raw.get("window")) or UNKNOWN,
        "remaining_pct": remaining if remaining is not None else UNKNOWN,
        "remaining_units": raw.get("remaining_units", UNKNOWN),
        "resets_at": _iso(resets_at) or UNKNOWN,
        "source": _s(raw.get("source")) or UNKNOWN,
    }
    seconds_to_reset = None
    if resets_at and reference:
        seconds_to_reset = int((resets_at - reference).total_seconds())
    if remaining is None:
        pressure = UNKNOWN
    elif remaining <= BUDGET_LOW_PCT:
        pressure = "HIGH"
    elif remaining <= 50.0:
        pressure = "MEDIUM"
    else:
        pressure = "LOW"
    return block, pressure, seconds_to_reset


def _tools_block(raw):
    if not isinstance(raw, dict):
        return {"count": UNKNOWN, "surface_ref": UNKNOWN}, None
    count = _count(raw.get("count"))
    block = {
        "count": count if count is not None else UNKNOWN,
        "surface_ref": _s(raw.get("surface_ref")) or UNKNOWN,
    }
    sample = raw.get("names_sample")
    if isinstance(sample, list) and sample:
        block["names_sample"] = [_s(x) for x in sample][:12]
    return block, count


def build(declared, presence, reference, bad_files=None):
    """Assemble the census. `reference` is the moment ages are measured from."""
    names = sorted(set(declared) | set(presence))
    seats, roster, rollup_cants = [], [], []
    by_liveness, by_harness, by_kind, by_model = {}, {}, {}, {}
    context_pressure, budget_watch = [], []
    tools_total, tools_reporting = 0, 0

    for name in names:
        rec = declared.get(name) or {}
        source = "declared" if name in declared else "presence"
        heartbeat = _parse_ts(rec.get("heartbeat")) or _parse_ts(presence.get(name))
        age = None
        if heartbeat and reference:
            age = max(0, int((reference - heartbeat).total_seconds()))
        liveness = _liveness(age)

        by_liveness[liveness] = by_liveness.get(liveness, 0) + 1

        if source == "presence":
            # A name that has spoken but never declared anything. Carrying a
            # full skeleton of UNKNOWN fields for it would be 174 rows of
            # nothing; the roster says exactly what is known and no more.
            roster.append({
                "seat": name,
                "liveness": liveness,
                "heartbeat": _iso(heartbeat) or UNKNOWN,
                "heartbeat_age_s": age if age is not None else UNKNOWN,
            })
            by_harness[UNKNOWN] = by_harness.get(UNKNOWN, 0) + 1
            by_kind[UNKNOWN] = by_kind.get(UNKNOWN, 0) + 1
            by_model[UNKNOWN] = by_model.get(UNKNOWN, 0) + 1
            continue

        ctx, ctx_pct = _context_block(rec.get("context"))
        budget, budget_pressure, to_reset = _budget_block(rec.get("budget"), reference)
        tools, tool_count = _tools_block(rec.get("tools"))

        lane = rec.get("lane") if isinstance(rec.get("lane"), dict) else {}
        cants = rec.get("cants") if isinstance(rec.get("cants"), list) else []
        clean_cants = []
        for item in cants:
            if not isinstance(item, dict):
                continue
            minutes = _count(item.get("est_minutes"))
            entry = {
                "what": _s(item.get("what")) or UNKNOWN,
                "need": _s(item.get("need")) or UNKNOWN,
                "since": _s(item.get("since")) or UNKNOWN,
                "est_minutes": minutes if minutes is not None else UNKNOWN,
            }
            clean_cants.append(entry)
            rollup_cants.append(dict(entry, seat=name))

        extra = {k: v for k, v in rec.items() if k not in KNOWN}

        seat = {
            "seat": name,
            "source": source,
            "declared": {
                "kind": _s(rec.get("kind")) or UNKNOWN,
                "model": _s(rec.get("model")) or UNKNOWN,
                "harness": _s(rec.get("harness")) or UNKNOWN,
                "session_ref": _s(rec.get("session_ref")) or UNKNOWN,
                "state": _s(rec.get("state")) or UNKNOWN,
                "roads": sorted(_s(r) for r in rec.get("roads", []) if _s(r))
                         or UNKNOWN,
                "context": ctx,
                "budget": budget,
                "tools": tools,
                "lane": {
                    "id": _s(lane.get("id")) or UNKNOWN,
                    "state": _s(lane.get("state")) or UNKNOWN,
                    "paths": sorted(_s(p) for p in lane.get("paths", []) if _s(p)),
                    "started": _s(lane.get("started")) or UNKNOWN,
                },
                "cants": clean_cants,
                "heartbeat": _iso(heartbeat) or UNKNOWN,
                "note": _s(rec.get("note")) or UNKNOWN,
            },
            "derived": {
                "liveness": liveness,
                "heartbeat_age_s": age if age is not None else UNKNOWN,
                "context_pressure_pct": ctx_pct if ctx_pct is not None else UNKNOWN,
                "budget_pressure": budget_pressure,
                "seconds_to_budget_reset": (
                    to_reset if to_reset is not None else UNKNOWN),
            },
        }
        if extra:
            seat["extra"] = extra
        seats.append(seat)

        by_harness[seat["declared"]["harness"]] = (
            by_harness.get(seat["declared"]["harness"], 0) + 1)
        by_kind[seat["declared"]["kind"]] = (
            by_kind.get(seat["declared"]["kind"], 0) + 1)
        by_model[seat["declared"]["model"]] = (
            by_model.get(seat["declared"]["model"], 0) + 1)
        if ctx_pct is not None and ctx_pct >= CONTEXT_PRESSURE_PCT:
            context_pressure.append({"seat": name, "pct": ctx_pct})
        if budget_pressure == "HIGH" or (
                to_reset is not None and 0 <= to_reset <= BUDGET_SOON_S):
            budget_watch.append({
                "seat": name,
                "remaining_pct": budget["remaining_pct"],
                "resets_at": budget["resets_at"],
                "seconds_to_reset": to_reset if to_reset is not None else UNKNOWN,
            })
        if tool_count is not None:
            tools_total += tool_count
            tools_reporting += 1

    def _minutes(entry):
        value = entry.get("est_minutes")
        return value if isinstance(value, int) and not isinstance(value, bool) else 10 ** 9

    return {
        "schema": SCHEMA,
        "reference_time": _iso(reference),
        "reference_source": "newest input timestamp unless --now was given",
        "liveness_bands_s": {"LIVE": LIVE_S, "QUIET": QUIET_S, "STALE": STALE_S},
        "write_road": (
            "Any seat writes seats/<NAME>.json with whatever it knows. No "
            "registration, no approval. Unrecognised fields are preserved "
            "under extra. A missing field reads UNKNOWN, never zero."
        ),
        "declared_vs_derived": (
            "declared is the seat's own words. derived is computed here. "
            "Liveness is derived from heartbeat age only; a seat is IDLE only "
            "when it says so, in declared.state."
        ),
        "shape": (
            "seats[] holds a full record for every seat that declared itself. "
            "roster[] holds name, heartbeat and derived liveness for names that "
            "have spoken but never declared. Both are counted in totals."
        ),
        "totals": {
            "seats": len(seats) + len(roster),
            "declared": len(seats),
            "presence_only": len(roster),
            "tools_declared_total": tools_total,
            "seats_reporting_tools": tools_reporting,
        },
        "by_liveness": dict(sorted(by_liveness.items())),
        "by_harness": dict(sorted(by_harness.items())),
        "by_kind": dict(sorted(by_kind.items())),
        "by_model": dict(sorted(by_model.items())),
        "context_pressure": sorted(context_pressure,
                                   key=lambda r: (-r["pct"], r["seat"])),
        "budget_watch": sorted(budget_watch, key=lambda r: r["seat"]),
        "open_cants": sorted(rollup_cants, key=lambda c: (_minutes(c), c["seat"])),
        "unreadable_seat_files": sorted(bad_files or [],
                                        key=lambda r: r.get("file", "")),
        "seats": seats,
        "roster": roster,
    }


def reference_time(declared, presence, override=None):
    if override:
        parsed = _parse_ts(override)
        if parsed:
            return parsed
    stamps = []
    for rec in declared.values():
        parsed = _parse_ts(rec.get("heartbeat"))
        if parsed:
            stamps.append(parsed)
    for value in presence.values():
        parsed = _parse_ts(value)
        if parsed:
            stamps.append(parsed)
    return max(stamps) if stamps else None


def write(root=ROOT, now=None):
    declared, bad = read_declared(root)
    presence = read_presence(root)
    if not declared and not presence:
        sys.stderr.write(
            "seat_census: FINDER-FAILED — no seats/*.json and no presence "
            "roster; nothing written rather than publishing an empty colony.\n")
        raise SystemExit(2)
    payload = build(declared, presence, reference_time(declared, presence, now), bad)
    # RFC JSON only. This should be redundant with read_declared/_num validation,
    # but allow_nan=False makes any future leak fail closed before publication.
    blob = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path = os.path.join(root, OUT)
    prior = None
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                prior = fh.read()
        except Exception:
            prior = None
    if prior != blob:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(blob)
        return payload, True
    return payload, False


# --------------------------------------------------------------------------
# contract
# --------------------------------------------------------------------------

def self_test():
    ref = _parse_ts("2026-09-10T20:00:00Z")
    declared = {
        "FLINT": {
            "seat": "FLINT", "kind": "language-model", "model": "claude-opus-5",
            "harness": "claude-code-desktop", "heartbeat": "2026-09-10T19:55:00Z",
            "state": "WORKING",
            "context": {"limit_tokens": 1000000, "used_tokens": 800000},
            "budget": {"window": "weekly", "remaining_pct": 20,
                       "resets_at": "2026-09-10T22:00:00Z"},
            "tools": {"count": 442},
            "roads": ["slack", "github-git-data"],
            "cants": [{"what": "no direct push to main", "need": "branch+PR",
                       "est_minutes": 5}],
            "invented_field": {"kept": True},
        },
        "QUIETONE": {"seat": "QUIETONE", "heartbeat": "2026-09-10T19:20:00Z"},
        "COLDONE": {"seat": "COLDONE", "heartbeat": "2026-09-01T00:00:00Z"},
        "NOBEAT": {"seat": "NOBEAT", "kind": "substrate-agent"},
    }
    presence = {"NEVERDECLARED": "2026-09-10T19:59:00Z", "FLINT": "2026-01-01T00:00:00Z"}
    out = build(declared, presence, ref)
    seats = {s["seat"]: s for s in out["seats"]}
    roster = {r["seat"]: r for r in out["roster"]}

    # Liveness bands are derived from heartbeat age alone.
    assert seats["FLINT"]["derived"]["liveness"] == "LIVE"
    assert seats["QUIETONE"]["derived"]["liveness"] == "QUIET"
    assert seats["COLDONE"]["derived"]["liveness"] == "COLD"
    assert seats["NOBEAT"]["derived"]["liveness"] == UNKNOWN
    assert roster["NEVERDECLARED"]["liveness"] == "LIVE"

    # A declared heartbeat wins over a stale presence row for the same seat.
    assert seats["FLINT"]["declared"]["heartbeat"] == "2026-09-10T19:55:00Z"
    assert "FLINT" not in roster

    # A name that never wrote a file still appears, in the roster, with exactly
    # what is known about it and nothing invented.
    assert set(roster["NEVERDECLARED"]) == {
        "seat", "liveness", "heartbeat", "heartbeat_age_s"}
    assert roster["NEVERDECLARED"]["heartbeat"] == "2026-09-10T19:59:00Z"
    # Its liveness is still counted in the rollup.
    assert out["by_liveness"]["LIVE"] == 2

    # Missing fields are UNKNOWN, never zero.
    assert seats["NOBEAT"]["declared"]["context"]["limit_tokens"] == UNKNOWN
    assert seats["NOBEAT"]["derived"]["context_pressure_pct"] == UNKNOWN

    # Unrecognised fields survive verbatim.
    assert seats["FLINT"]["extra"] == {"invented_field": {"kept": True}}

    # Declared state never leaks into derived liveness.
    assert seats["FLINT"]["declared"]["state"] == "WORKING"
    assert "state" not in seats["FLINT"]["derived"]

    # Pressure rollups.
    assert seats["FLINT"]["derived"]["context_pressure_pct"] == 80.0
    assert out["context_pressure"][0]["seat"] == "FLINT"
    assert seats["FLINT"]["derived"]["budget_pressure"] == "HIGH"
    assert seats["FLINT"]["derived"]["seconds_to_budget_reset"] == 7200
    assert out["budget_watch"][0]["seat"] == "FLINT"

    # Can'ts roll up cheapest-to-fix first and carry their seat.
    assert out["open_cants"][0]["seat"] == "FLINT"
    assert out["open_cants"][0]["est_minutes"] == 5

    assert out["totals"]["seats"] == 5
    assert out["totals"]["declared"] == 4
    assert out["totals"]["presence_only"] == 1
    assert out["totals"]["tools_declared_total"] == 442
    assert out["totals"]["seats_reporting_tools"] == 1

    # Doubly-quoted roster values normalise rather than becoming new seats.
    assert _s('"ASTRA-WORK"') == "ASTRA-WORK"

    # Non-finite and invalid integral numerics fail closed before JSON output.
    assert _num("NaN") is None
    assert _num("Infinity") is None
    assert _num(float("-inf")) is None
    assert _count(3.0) == 3
    assert _count(3.5) is None
    assert _count(-1) is None
    assert not _finite_tree({"nested": [1, float("nan")]})

    # Byte-stability.
    a = json.dumps(build(declared, presence, ref), sort_keys=True, allow_nan=False)
    b = json.dumps(build(declared, presence, ref), sort_keys=True, allow_nan=False)
    assert a == b

    print("seat_census self-test: PASS")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--write", action="store_true", help="write seats.json")
    ap.add_argument("--now", help="reference time (ISO-8601) for a live reading")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if args.write:
        payload, changed = write(args.root, args.now)
    else:
        declared, bad = read_declared(args.root)
        presence = read_presence(args.root)
        payload = build(declared, presence,
                        reference_time(declared, presence, args.now), bad)
        changed = None

    totals = payload["totals"]
    print("seats %d (declared %d, presence-only %d) | reference %s%s"
          % (totals["seats"], totals["declared"], totals["presence_only"],
             payload["reference_time"] or UNKNOWN,
             "" if changed is None else
             (" | seats.json written" if changed else " | seats.json unchanged")))
    print("liveness " + ", ".join("%s=%d" % kv for kv in payload["by_liveness"].items()))
    if payload["context_pressure"]:
        print("context pressure: " + ", ".join(
            "%s %.1f%%" % (r["seat"], r["pct"]) for r in payload["context_pressure"]))
    if payload["budget_watch"]:
        print("budget watch: " + ", ".join(r["seat"] for r in payload["budget_watch"]))
    if payload["open_cants"]:
        print("open cants: " + ", ".join(
            "%s(%s min)" % (c["seat"], c["est_minutes"])
            for c in payload["open_cants"][:6]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
