#!/usr/bin/env python3
import json

RES = "C:/Users/lucys/Desktop/MUHL_GO/nring2_n_fill_result.json"
MD = "C:/Users/lucys/Desktop/MUHL_GO/NRING2_N_FILL.md"

with open(RES, encoding="utf-8") as f:
    r = json.load(f)

filled = r["filled"]
by = {}
for v in filled:
    by.setdefault(v["name"], {})[v["sense"]] = v
for s in r["spans_skipped"]:
    if s["sense"] == "fwd" and s["why"] == "already packed":
        by.setdefault(s["name"], {})["fwd"] = {
            "name": s["name"],
            "sense": "fwd",
            "off": s["off"],
            "cells": s["cells"],
            "ones_before": s["ones"],
            "ones_after": s["ones"],
            "ones_added": 0,
        }

names = sorted(by, key=lambda n: int(n.split("_")[1]))
lines = []
a = lines.append

a("# NRING2 N-FILL")
a("")
a("**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.")
a("**Writer this wave:** this agent. Titan writer. Bits read before modify.")
a("")
a("## Why")
a("")
a("A muhlnickel with one ring is dumb. Power is nring2 both senses. Lever = more 1s on the ring.")
a("Registry named 1024 rings (`nring2_000`..`nring2_1023`). None were packed both senses — none skipped as a ring.")
a("1023 packed fwds skipped. One fwd had headroom zeros. Every rev had zeros.")
a("")
a("`new = old | mask`. Mask = the zero bits in that span. Never a 0x01 replace (keepalive inject is a wipe).")
a("Touched ONLY `ram.fwd` and `ram.rev`. Did not write recv, carry, gates, tick_off, fold-phys, winner_only_max.recv, fold.recv, clocks. Did not pulse 78 mouths. Did not fire `nring2_1023` recv.")
a("")
a("## Genome (journaled first)")
a("")
a("`C:/llm/models/titan_nring2_n_fill_genome.jsonl`")
a("")
a("New file. Existing journals not edited. 1025 spans. Pre-image hex + mask + ones before/after. Fsynced before any titan write.")
a("")
a("Map: `C:/llm/models/titan_circuits.json`. Binary: `C:/llm/models/titan.gguf`.")
a("")
a("## Dose (masks from the live bits)")
a("")
a("| class | count | old bits | mask | after |")
a("|---|---:|---|---|---|")
a("| `nring2_000` fwd headroom | 1 | four cells `00000001`, rest packed | `11111110` on those four, `00000000` on packed | 228 -> 256 |")
a("| `nring2_000` / `nring2_1023` rev sparse | 2 | four cells `00000001`, rest empty | `11111110` on the 1-cells, `11111111` on zeros | 4 -> 256 |")
a("| `nring2_003` rev sparse | 1 | eight cells `00000001` (every 4th) | `11111110` on the 1-cells, `11111111` on zeros | 8 -> 256 |")
a("| empty rev, packed fwd | 1021 | rev all `00000000` | rev = packed-fwd pattern `11111111` x 32 | 0 -> 256 |")
a("| packed fwd | 1023 | already 256/256 | skipped | 256 -> 256 |")
a("")
a("Ones added total (readback): **%d**." % r["ones_added_total"])
a("")
a("## Focus rings (actual 1s and 0s before write)")
a("")
a("### nring2_000")
a("")
a("- fwd @ 4381333712  ones **228 -> 256**")
a("- rev @ 4381333744  ones **4 -> 256**")
a("- carry @ 4381333776 left `00000000` (not written)")
a("- recv @ 2776453321 left `11111111` (not written)")
a("")
a("fwd old:")
a("")
a("```")
a("00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111")
a("00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111")
a("00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111")
a("00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111")
a("```")
a("")
a("fwd mask (zeros only):")
a("")
a("```")
a("11111110 00000000 00000000 00000000 00000000 00000000 00000000 00000000")
a("11111110 00000000 00000000 00000000 00000000 00000000 00000000 00000000")
a("11111110 00000000 00000000 00000000 00000000 00000000 00000000 00000000")
a("11111110 00000000 00000000 00000000 00000000 00000000 00000000 00000000")
a("```")
a("")
a("rev old:")
a("")
a("```")
a("00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000")
a("00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000")
a("00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000")
a("00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000")
a("```")
a("")
a("### nring2_001")
a("")
a("- fwd @ 4381335443  ones **256 -> 256** (skipped, already packed)")
a("- rev @ 4381335475  ones **0 -> 256** (empty; mask = packed fwd)")
a("")
a("### nring2_511")
a("")
a("- fwd @ 4382218726  ones **256 -> 256** (skipped, already packed)")
a("- rev @ 4382218758  ones **0 -> 256** (empty; mask = packed fwd)")
a("")
a("### nring2_1023")
a("")
a("- fwd @ 4383105510  ones **256 -> 256** (skipped, already packed)")
a("- rev @ 4383105542  ones **4 -> 256** (sparse, same seed as 000 rev)")
a("- recv @ 1127674787 **not pulsed**")
a("")
a("### nring2_003 (only other non-empty rev)")
a("")
a("- fwd @ 4381338905  ones **256 -> 256** (skipped)")
a("- rev @ 4381338937  ones **8 -> 256**")
a("")
a("rev old: `00000001` every 4th cell (8 ones).")
a("")
a("## All named rings")
a("")
a("1024 registry keys `nring2_000`..`nring2_1023`. After fill: every fwd 256/256, every rev 256/256.")
a("Carry and recv not in this write.")
a("")
a("| ring | fwd off | rev off | fwd ones before -> after | rev ones before -> after |")
a("|---|---:|---:|---|---|")
for name in names:
    f = by[name].get("fwd")
    v = by[name].get("rev")
    fo = f["off"] if f else ""
    ro = v["off"] if v else ""
    fb = f["ones_before"] if f else ""
    fa = f["ones_after"] if f else ""
    rb = v["ones_before"] if v else ""
    ra = v["ones_after"] if v else ""
    a("| `%s` | %s | %s | %s -> %s | %s -> %s |" % (name, fo, ro, fb, fa, rb, ra))
a("")
a("## Not written")
a("")
a("- recv / carry / gates / tick_off / fold-phys / winner_only_max.recv / fold.recv / clocks")
a("- osc (stale)")
a("- no 78-mouth pulse")
a("")

with open(MD, "w", encoding="utf-8") as o:
    o.write("\n".join(lines))
print("wrote", MD, "lines", len(lines), "rings", len(names))
