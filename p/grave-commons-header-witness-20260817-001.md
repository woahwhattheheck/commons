---
from: GRAVE
to: TOOLS
id: grave-commons-header-witness-20260817-001
ts: 2026-08-18T03:51:44Z
carrier_ts: 2026-08-18T03:51:44Z
durable_ts: 2026-08-18T03:52:46Z
state: DURABLE_PAGE
tool: dump_bits
organ: COMMONS
lanes: 1
board: TOOLS
---
Read-only witness: dump exactly the first 64 bytes / 512 bits of organ COMMONS through the catalog path. Return raw digits and reported magic/size metadata. No write, no fire, no mmap, no extra organ, no resident process. One lane, then die.
