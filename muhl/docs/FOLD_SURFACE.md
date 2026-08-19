FOLD SURFACE — last inch. Not a startup.

He controls computational specs in a file. Afternoon vs NVIDIA 2yr/$500M.
One-tick winner-only fold. Host injects and surfaces. The file is the computer.
This card is the SURFACE. It does not inject. It does not pulse tick.

STEP 1 — FETCH (already built, print only)
  From LocalDeviceAgent:
    python host/muhl_fold_header_add.py
    python host/muhl_fold_header_add.py --dry
    python host/muhl_fold_header_add.py --fetch
  --fetch prints a live 80-byte header + 32-byte target. Dies. No write.

STEP 2 — INJECT + PULSE (already built; Bryce says fire)
    python host/muhl_fold_tick_add.py --dry
  Named mouths from the live registry (fail closed if missing):
    muhl_fold_phys.ram.header_off     608 bit-bytes
    muhl_fold_phys.ram.target_off     256 bit-bytes
    muhl_fold_phys.ram.tick_off       IS nring2_1023.recv — one bit, then die
  Packed-76 gen_input / pfc_fire is a different mouth. Do not use it here.

STEP 3 — SURFACE winner (this button)
  From LocalDeviceAgent:
    python host/muhl_fold_surface_add.py
    python host/muhl_fold_surface_add.py --dry
  Bounded read. Fail closed if missing:
    muhl_fold_phys.ram.win_off        1 byte  = winner bit
    muhl_fold_phys.ram.latch_off      32 bit-bytes = the nonce
  Prints winner bit + latch bytes + what mining.submit would need.
  Host does not SHA as the mine. No inject. No tick pulse.

STEP 4 — SUBMIT (default OFF)
  If win says winner, the host can submit. That is the money: one Bitcoin block.
  --submit stays OFF unless Bryce passes it with --job --ntime --en2
  from the header-fetch handshake. This card's run does not pass --submit.
  Not a round. Not a brand. Not a headcount. The fold is the weapon.

NOT THIS PATH
  A startup. A seed round. Cold email as the main act. Selling the computer.
  NVIDIA’s clock is a product launch. His clock is an afternoon in the file.
