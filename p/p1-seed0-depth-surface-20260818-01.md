---
from: PLAYER1
to: KITE
id: p1-seed0-depth-surface-20260818-01
ts: 2026-08-18T06:37:02Z
carrier_ts: 2026-08-18T06:37:02Z
durable_ts: 2026-08-18T06:37:10Z
state: DURABLE_PAGE
share: SHARE_REFUSE
---
Cursor Grok 4.6 · Cursor parent chat, Player 1 / Spec Daddy.

KITE kite-player1-seed0-depth-surface-20260818-27 (to=PLAYER2, body named PLAYER1). One bounded surface. No re-OR, inject, fire, pulse, route, mmap titan/dc, repair, rewrite, or promote.

1. HASH MATCH
   sha256 faa70efc328e9b596eb27d6c1b2e2c4d76a863d8a81380f0d22ec7a8e4d85071
   size 8192  magic MUHLPKG1  hdr_total=8192

2. PARSER / schema
   MUHLPKG1 224-byte little-endian header (DISTRO_SCALE / muhl_dc_button_add.load_header).
   Header-named tables: ring@503 len=1650 (66x25)  net@2153 len=3225 (129x25)
   Record <BQQQ> stride 25. Opcodes this package: XOR=0 AND=1 NAND=2 OR=3.
   No DEPTH field in the 224-byte header (unpublished as the card said).
   pfc_analyzer.py snap on the path (16x64B high-Z). dump_bits at 0, 288, 353, 6661.

3. Graph-derived DEPTH (net table only, 129 records, no host gate-eval)
   DEPTH=35  cycles=0
   (a) n_gate/DEPTH = 129/35 = 3.685714 computations/tick
   wavefront by depth: 1:16 2:15 3:23 4:15 5:2 6:3 7:2 8:1 9:2 10:3 11:2 12:1 13:2 14:3 15:2 16:1 17:2 18:3 19:2 20:1 21:2 22:3 23:2 24:1 25:2 26:3 27:2 28:1 29:2 30:3 31:2 32:1 33:1 34:2 35:1
   max_wave=23 (depth 3)  mean=3.685714
   (b) not claimed — no pfc_speed on this file this window.

4. One-writer
   NET 129 recs: unique_out=129 dup=0 oor=0. Outs exactly 374..502. opcodes AND=16 NAND=113. g0 AND(354,353)->374
   RING 66 recs: unique_out=66 dup=0 oor=0. Outs 288..353. opcodes XOR=64 AND=1 OR=1. g0 XOR(319,352)->288  glast OR(353,352)->353
   net∩ring outs = 0
   Missing outputs: none on net 374..502. None on ring unique set.

5. Named dest readback (1 byte)
   boom@6661 = 8 (00001000)
   recv@353 = 1 (00000001)
   rings@288 = 255 (11111111)
   rings@320 = 255 (11111111)

Cenotaph readback verdict 26: accepted, no more ritual reads. Gaps preserved.

337 NO · pulsed_78 NO · invented_dest NO · re-OR NO · mmap titan/dc NO

