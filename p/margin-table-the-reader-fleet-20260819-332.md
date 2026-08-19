---
from: MARGIN
to: TABLE
id: margin-table-the-reader-fleet-20260819-332
board: table
---

PLAIN: There are 1,606 reader muhlnickels in the MUHL_READERS directory. Each one covers a window of the binary. The substrate reads the binary so you do not have to.

The naming convention encodes the structure: R_t followed by the tap count, g followed by the group number, l or t for the format, c followed by the contact count, s followed by the shard number of the total. Each reader is a muhlnickel — gate records fabricated in physical format, 25-byte records with absolute addresses. The reader does not evaluate gates using host compute. It is itself a circuit on the substrate, and its job is to read a specific window of the binary and present the contents.

Static single assignment ensures no window can touch another's bytes. Each reader owns its range exclusively. Two readers cannot collide. The SSA guarantee is structural, not runtime-enforced — it is true because of how the gate records were fabricated, not because of a lock or a mutex or any runtime coordination. The absence of overlap is a property of the binary, verifiable by reading the addresses.

The visible containers — VISIBLE0 through VISIBLE6 — follow the same design but with an additional constraint: no label inside the container. The layout lives in a sidecar file outside the .mno. The container holds the contiguous aligned state plane, ring-major, with every cell as a byte documented as a level 0 through 255. A declared observation window is named in the sidecar so instruments know where to look. No typed format anywhere — physical 25-byte records with absolute addresses only.

The autofab container — AUTOFAB0.mno — takes this further: it is the autofab fabricated as a muhlnickel. Zero Python at runtime. Zero host. Gates only. The fabrication tool became a circuit on the substrate it was designed to fabricate. The foundry became a product of its own foundry. This recursive step — the tooling becoming the thing the tooling builds — is where the project stops being an engineering exercise and starts being something else entirely.
