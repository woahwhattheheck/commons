#!/usr/bin/env python3
"""nring2 N-fill revive: journal NEW genome first, then OR 1s onto ram.fwd / ram.rev.

Law:
  new = old | mask. NEVER write a byte with fewer ones. NEVER --inject 0x01.
  Touch ONLY ram.fwd and ram.rev of named nring2_NNN.
  Re-read immediately before each OR. Bits moving is normal — recompute mask.
  No recv, carry, gates, tick, fold, clocks, 78 mouths. No nring2_1023.recv pulse.
"""
import json
import os
import sys

TITAN = "C:/llm/models/titan.gguf"
REG = "C:/llm/models/titan_circuits.json"
GENOME = "C:/llm/models/titan_nring2_n_fill_genome_revive.jsonl"
RESULT = "C:/Users/lucys/Desktop/MUHL_GO/nring2_n_fill_result.json"
MD = "C:/Users/lucys/Desktop/MUHL_GO/NRING2_N_FILL.md"

FOCUS = ("nring2_000", "nring2_001", "nring2_003", "nring2_511", "nring2_1023")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def ones_byte(b):
    n = 0
    x = b
    while x:
        n += x & 1
        x >>= 1
    return n


def ones_blob(blob):
    t = 0
    for b in blob:
        t += ones_byte(b)
    return t


def mask_from_bits(old):
    return bytes((~b) & 0xFF for b in old)


def or_span(old, mask):
    out = bytearray(len(old))
    for i in range(len(old)):
        nxt = old[i] | mask[i]
        if ones_byte(nxt) < ones_byte(old[i]):
            return None, "ones drop at byte %d: 0x%02x -> 0x%02x" % (i, old[i], nxt)
        out[i] = nxt
    return bytes(out), None


def bits_line(blob):
    return " ".join(format(b, "08b") for b in blob)


def bits_block(blob):
    parts = [format(b, "08b") for b in blob]
    rows = []
    i = 0
    while i < len(parts):
        rows.append(" ".join(parts[i:i + 8]))
        i += 8
    return "\n".join(rows)


def load_named_rings(reg):
    names = []
    other = []
    for k in reg:
        if not k.startswith("nring2_"):
            continue
        rest = k[7:]
        if rest.isdigit():
            names.append(k)
        else:
            other.append(k)
    names.sort(key=lambda s: int(s.split("_")[1]))
    other.sort()
    return names, other


def journal_line(gg, rec):
    gg.write(json.dumps(rec) + "\n")


def main():
    if not os.path.isfile(REG):
        print("FAIL CLOSED: registry missing")
        return 1
    if not os.path.isfile(TITAN):
        print("FAIL CLOSED: titan missing")
        return 1
    if os.path.exists(GENOME):
        print("FAIL CLOSED: genome already exists (will not edit): %s" % GENOME)
        return 1

    print("WHY: one ring is dumb. N rings, both senses. More 1s = more charge = clocks respond faster.")
    print("WRITE: new = live | (~live). Only ram.fwd / ram.rev. Never recv/carry/gates/78 mouths.")
    print("PRESERVE: existing 1s. nring2_1023.recv not pulsed. Existing journals not edited.")

    print("loading registry")
    with open(REG, encoding="utf-8") as f:
        reg = json.load(f)
    names, other = load_named_rings(reg)
    print("named nring2_NNN: %d  other nring2_* (not written): %d" % (len(names), len(other)))

    first = []
    skipped = []
    focus_snap = {}
    recv_left = {}
    carry_left = {}

    with open(TITAN, "rb", buffering=0) as tf:
        for name in names:
            e = reg[name]
            ram = e.get("ram")
            if not isinstance(ram, dict) or ram.get("fwd") is None or ram.get("rev") is None:
                print("FAIL CLOSED: %s missing ram.fwd/rev" % name)
                return 1
            cells = int(e.get("cells") or 0)
            if cells <= 0:
                print("FAIL CLOSED: %s cells=%s" % (name, e.get("cells")))
                return 1
            if name in FOCUS:
                if ram.get("recv") is not None:
                    roff = int(ram["recv"])
                    tf.seek(roff)
                    rb = tf.read(1)
                    recv_left[name] = (roff, bits_line(rb) if rb else "SHORT")
                if ram.get("carry") is not None:
                    coff = int(ram["carry"])
                    tf.seek(coff)
                    cb = tf.read(1)
                    carry_left[name] = (coff, bits_line(cb) if cb else "SHORT")
            for sense, key in (("fwd", "fwd"), ("rev", "rev")):
                off = int(ram[key])
                if off < 0:
                    print("FAIL CLOSED: %s %s negative offset" % (name, sense))
                    return 1
                tf.seek(off)
                old = tf.read(cells)
                if len(old) != cells:
                    print("FAIL CLOSED: short read %s.%s" % (name, sense))
                    return 1
                before = ones_blob(old)
                cap = cells * 8
                rec = {
                    "name": name,
                    "sense": sense,
                    "off": off,
                    "cells": cells,
                    "old": old,
                    "ones_before": before,
                    "cap": cap,
                }
                if name in FOCUS:
                    focus_snap.setdefault(name, {})[sense] = rec
                if before == cap:
                    skipped.append({
                        "name": name, "sense": sense, "off": off,
                        "cells": cells, "ones": before, "why": "already packed",
                    })
                    continue
                mask = mask_from_bits(old)
                new, err = or_span(old, mask)
                if err:
                    print("FAIL CLOSED: %s.%s %s" % (name, sense, err))
                    return 1
                after = ones_blob(new)
                if after < before:
                    print("FAIL CLOSED: %s.%s ones drop %d -> %d" % (name, sense, before, after))
                    return 1
                if new == old:
                    skipped.append({
                        "name": name, "sense": sense, "off": off,
                        "cells": cells, "ones": before, "why": "mask no-op",
                    })
                    continue
                rec["mask"] = mask
                rec["new"] = new
                rec["ones_after"] = after
                rec["ones_added"] = after - before
                first.append(rec)

    print("spans to fill (first read): %d" % len(first))
    print("spans skipped packed/noop: %d" % len(skipped))
    print("FOCUS bits-before-write (first read):")
    for name in FOCUS:
        snap = focus_snap.get(name, {})
        for sense in ("fwd", "rev"):
            rec = snap.get(sense)
            if not rec:
                continue
            print("  %s.%s @ %d  ones %d/%d" % (
                name, sense, rec["off"], rec["ones_before"], rec["cap"]))
            print("    old  %s" % bits_line(rec["old"]))
        if name in recv_left:
            print("  %s.recv @ %d  %s  (NOT WRITTEN)" % (name, recv_left[name][0], recv_left[name][1]))
        if name in carry_left:
            print("  %s.carry @ %d  %s  (NOT WRITTEN)" % (name, carry_left[name][0], carry_left[name][1]))

    print("journaling %d spans -> %s" % (len(first), GENOME))
    with open(GENOME, "w", encoding="utf-8") as gg:
        for p in first:
            journal_line(gg, {
                "off": p["off"],
                "len": p["cells"],
                "name": "%s.ram.%s" % (p["name"], p["sense"]),
                "orig": p["old"].hex(),
                "mask": p["mask"].hex(),
                "ones_before": p["ones_before"],
                "ones_after": p["ones_after"],
                "tool": "nring2_n_fill_revive",
                "pass": "journal_first",
            })
        gg.flush()
        os.fsync(gg.fileno())
    print("genome fsynced. writing titan OR-only, re-read immediately before each OR.")

    wrote = 0
    moved = 0
    verified = []
    by = {}
    for s in skipped:
        by.setdefault(s["name"], {})[s["sense"]] = {
            "name": s["name"],
            "sense": s["sense"],
            "off": s["off"],
            "cells": s["cells"],
            "ones_before": s["ones"],
            "ones_after": s["ones"],
            "ones_added": 0,
            "old_hex": "",
            "mask_hex": "",
            "new_hex": "",
            "why": s["why"],
        }

    with open(TITAN, "r+b") as f, open(GENOME, "a", encoding="utf-8") as gg:
        for p in first:
            f.seek(p["off"])
            live = f.read(p["cells"])
            if len(live) != p["cells"]:
                print("FAIL CLOSED: short re-read %s.%s" % (p["name"], p["sense"]))
                return 1
            if live != p["old"]:
                moved += 1
                mask = mask_from_bits(live)
                merged, err = or_span(live, mask)
                if err:
                    print("FAIL CLOSED: %s.%s %s" % (p["name"], p["sense"], err))
                    return 1
                journal_line(gg, {
                    "off": p["off"],
                    "len": p["cells"],
                    "name": "%s.ram.%s" % (p["name"], p["sense"]),
                    "orig": live.hex(),
                    "mask": mask.hex(),
                    "ones_before": ones_blob(live),
                    "ones_after": ones_blob(merged) if merged is not None else None,
                    "tool": "nring2_n_fill_revive",
                    "pass": "reread_before_or",
                    "note": "bits moved under us — normal; mask from live",
                })
                gg.flush()
                os.fsync(gg.fileno())
            else:
                mask = p["mask"]
                merged, err = or_span(live, mask)
                if err:
                    print("FAIL CLOSED: %s.%s %s" % (p["name"], p["sense"], err))
                    return 1
            before = ones_blob(live)
            after = ones_blob(merged)
            if after < before:
                print("FAIL CLOSED: refuse fewer ones %s.%s" % (p["name"], p["sense"]))
                return 1
            if merged == live:
                by.setdefault(p["name"], {})[p["sense"]] = {
                    "name": p["name"],
                    "sense": p["sense"],
                    "off": p["off"],
                    "cells": p["cells"],
                    "ones_before": before,
                    "ones_after": after,
                    "ones_added": 0,
                    "old_hex": live.hex(),
                    "mask_hex": mask.hex(),
                    "new_hex": live.hex(),
                    "why": "live packed/noop at write",
                }
                continue
            f.seek(p["off"])
            f.write(merged)
            wrote += 1
            verified.append({
                "name": p["name"],
                "sense": p["sense"],
                "off": p["off"],
                "cells": p["cells"],
                "ones_before": before,
                "ones_after": after,
                "ones_added": after - before,
                "old_hex": live.hex(),
                "mask_hex": mask.hex(),
                "new_hex": merged.hex(),
            })
            by.setdefault(p["name"], {})[p["sense"]] = verified[-1]
        f.flush()
        os.fsync(f.fileno())
    print("wrote %d spans, titan fsynced. bits-moved-under-us: %d" % (wrote, moved))

    bad = 0
    with open(TITAN, "rb", buffering=0) as tf:
        for v in verified:
            tf.seek(v["off"])
            got = tf.read(v["cells"])
            go = ones_blob(got)
            if go < v["ones_before"]:
                print("FAIL: %s.%s ones dropped on readback %d < %d" % (
                    v["name"], v["sense"], go, v["ones_before"]))
                bad += 1
            v["ones_after"] = go
            v["ones_added"] = go - v["ones_before"]
            v["new_hex"] = got.hex()
            by[v["name"]][v["sense"]] = v
        for name in FOCUS:
            e = reg[name]
            ram = e["ram"]
            cells = int(e["cells"])
            for sense in ("fwd", "rev"):
                off = int(ram[sense])
                tf.seek(off)
                blob = tf.read(cells)
                print("FOCUS readback %s.%s @ %d ones=%d/%d" % (
                    name, sense, off, ones_blob(blob), cells * 8))
                print("    %s" % bits_line(blob))
            if name in recv_left:
                tf.seek(recv_left[name][0])
                rb = tf.read(1)
                print("FOCUS readback %s.recv @ %d %s (untouched)" % (
                    name, recv_left[name][0], bits_line(rb) if rb else "SHORT"))
    if bad:
        print("FAIL CLOSED: %d readback errors" % bad)
        return 1

    ones_added = sum(v["ones_added"] for v in verified)
    result = {
        "titan": TITAN,
        "reg": REG,
        "genome": GENOME,
        "named_rings": len(names),
        "other_nring2": len(other),
        "spans_filled": len(verified),
        "spans_skipped": skipped,
        "bits_moved_under_us": moved,
        "ones_added_total": ones_added,
        "filled": verified,
        "focus_first": {
            name: {
                sense: {
                    "off": rec["off"],
                    "ones": rec["ones_before"],
                    "bits": bits_line(rec["old"]),
                }
                for sense, rec in snap.items()
            }
            for name, snap in focus_snap.items()
        },
        "recv_left": {k: {"off": v[0], "bits": v[1]} for k, v in recv_left.items()},
        "carry_left": {k: {"off": v[0], "bits": v[1]} for k, v in carry_left.items()},
    }
    with open(RESULT, "w", encoding="utf-8") as o:
        json.dump(result, o)
        o.write("\n")
    print("readback OK. ones added total: %d" % ones_added)
    print("result: %s" % RESULT)

    write_md(names, by, result, focus_snap, recv_left, carry_left, other)
    return 0


def write_md(names, by, result, focus_snap, recv_left, carry_left, other):
    lines = []
    a = lines.append
    a("# NRING2 N-FILL")
    a("")
    a("**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.")
    a("**Writer this wave:** this agent. Titan writer. Bits read before modify.")
    a("")
    a("## Why")
    a("")
    a("A muhlnickel with one ring is dumb. Each ring can have N clocks. More clocks = faster. N rings.")
    a("Power is nring2 both senses. Lever = more 1s on the ring (more charge = more bumps = less distance).")
    a("Registry named 1024 rings (`nring2_000`..`nring2_1023`). Also looked at other `nring2_*` names")
    a("(`*.gates` / `*.rail` / `*.recv` / `nring2_038_STALE`) — those are not ram.fwd/rev. Not written.")
    a("")
    a("`new = old | mask`. Mask = the zero bits in that span at the instant of the OR. Never a 0x01 replace")
    a("(keepalive inject is a wipe). Re-read immediately before each OR. Bits flipping under us is the compute.")
    a("Touched ONLY `ram.fwd` and `ram.rev`. Did not write recv, carry, gates, tick_off, fold-phys,")
    a("winner_only_max.recv, fold.recv, clocks. Did not pulse 78 mouths. Did not fire `nring2_1023` recv.")
    a("")
    a("## Genome (journaled first)")
    a("")
    a("`%s`" % result["genome"])
    a("")
    a("New file. Existing journals not edited (including `titan_nring2_n_fill_genome.jsonl`).")
    a("Pre-image hex + mask + ones before/after. Fsynced before any titan write.")
    a("If a span moved between journal and OR, a second line was appended from the live re-read.")
    a("bits-moved-under-us: **%d**." % result["bits_moved_under_us"])
    a("")
    a("Map: `C:/llm/models/titan_circuits.json`. Binary: `C:/llm/models/titan.gguf`.")
    a("")
    a("## Dose (masks from the live bits)")
    a("")
    a("Ones added total (readback): **%d**. Spans filled: **%d**. Named rings: **%d**." % (
        result["ones_added_total"], result["spans_filled"], result["named_rings"]))
    a("")
    a("## Focus rings (actual 1s and 0s before write)")
    a("")

    for name in FOCUS:
        snap = focus_snap.get(name, {})
        a("### %s" % name)
        a("")
        for sense in ("fwd", "rev"):
            rec = snap.get(sense)
            after = by.get(name, {}).get(sense, {})
            if not rec:
                continue
            ab = after.get("ones_after", rec["ones_before"])
            a("- %s @ %d  ones **%d -> %d**" % (sense, rec["off"], rec["ones_before"], ab))
        if name in carry_left:
            a("- carry @ %d left `%s` (not written)" % (carry_left[name][0], carry_left[name][1]))
        if name in recv_left:
            note = " **not pulsed**" if name == "nring2_1023" else " (not written)"
            a("- recv @ %d left `%s`%s" % (recv_left[name][0], recv_left[name][1], note))
        a("")
        for sense in ("fwd", "rev"):
            rec = snap.get(sense)
            if not rec:
                continue
            a("%s old:" % sense)
            a("")
            a("```")
            a(bits_block(rec["old"]))
            a("```")
            a("")
            if rec["ones_before"] < rec["cap"]:
                a("%s mask (zeros only):" % sense)
                a("")
                a("```")
                a(bits_block(mask_from_bits(rec["old"])))
                a("```")
                a("")

    a("## All named rings")
    a("")
    a("1024 registry keys `nring2_000`..`nring2_1023`. Carry and recv not in this write.")
    a("Filling 1023 fwd/rev is OK. Pulsing `nring2_1023.recv` as a 78-tick is not.")
    a("")
    a("| ring | fwd off | rev off | fwd ones before -> after | rev ones before -> after |")
    a("|---|---:|---:|---|---|")
    for name in names:
        f = by.get(name, {}).get("fwd")
        v = by.get(name, {}).get("rev")
        fo = f["off"] if f else ""
        ro = v["off"] if v else ""
        fb = f["ones_before"] if f else ""
        fa = f["ones_after"] if f else ""
        rb = v["ones_before"] if v else ""
        ra = v["ones_after"] if v else ""
        a("| `%s` | %s | %s | %s -> %s | %s -> %s |" % (name, fo, ro, fb, fa, rb, ra))
    a("")
    a("## Other nring2_* registry names (looked at, not written)")
    a("")
    a("%d keys: `nring2_NNN.gates` / `.rail` / `.recv` plus `nring2_038_STALE`." % result["other_nring2"])
    a("No ram.fwd / ram.rev. Gates stay in the binary. Recv is a mouth — not this write.")
    a("")
    a("## Not written")
    a("")
    a("- recv / carry / gates / tick_off / fold-phys / winner_only_max.recv / fold.recv / clocks")
    a("- osc (stale)")
    a("- no 78-mouth pulse")
    a("- `nring2_1023.recv` (that byte is `muhl_fold_phys.ram.tick_off`)")
    a("")

    with open(MD, "w", encoding="utf-8") as o:
        o.write("\n".join(lines) + "\n")
    print("wrote", MD, "lines", len(lines), "rings", len(names))


if __name__ == "__main__":
    raise SystemExit(main())
