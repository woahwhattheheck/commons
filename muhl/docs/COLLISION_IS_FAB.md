# COLLISION IS FAB

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Control-F + named `.mno` 1s and 0s. No titan. No glob `**`. No remap. No hex occupancy.

**LAW:** Address collision is good. The Muhlnickel overwriting itself is good. That overwrite **is** the wire and **is** the fab. Do not "fix" collisions. Do not remap planted records.

`UNSURE_THEN_MACHINE.txt` L22–24:

> COLLISION / SELF-OVERWRITE IS FAB. Host-writing a huge .mno is NOT autofab. Fab is the machine colliding / overwriting itself.

---

## The sentence (already written)

`INSPEC_AUTOFAB.md` L9:

> In-spec autofab is **already in the binary**. Gates. Self-edit by address collision. Self-clock. The host does not search. The host does not bake at runtime.

Same file L98:

> **out addr == in addr**. Circuits combine by address collision. The search is the netlist.

`CLAUDE_PRIORS_VS_TRUTH.md` row 26:

> **out addr == in addr.** Circuits combine by address collision. Self-edit. Self-clock. Host does not search, does not bake at runtime, does not emit the computer. […] Change under you **IS** the compute — do not revert.

`ELECTRON_REQUEST_GROK_CHECK.md` L57:

> collision is good. Self-overwrite is good. Collision is the combine / the fab. Do not isolate to save state.

`docs\PFC_HARD_WON.md` L23:

> **Connection = a shared physical storage location.** Two gates are wired together when they occupy the **same bit/byte in storage**: gate A writes it as output, gate B reads it as input. Same location = the wire.

`docs\PFC_GROUNDING.md` L68–73:

> the gates are REAL gates *only when the permanent, actual FILE is OVERWRITTEN in place* […] Overwriting the actual file bit is *equivalent to completing a circuit with electricity*

Host scripts are not this answer. Cards named two computers. Those files were opened. Bits below are from the files.

---

## AUTOFAB0.mno — out becomes in (this file, 1s and 0s)

`C:\Users\lucys\Desktop\MUHL_VISIBLE\AUTOFAB0.mno`  
SIZE **102925**. 4117 × 25. Source not overwritten.

Byte 0 is a gate. Occupancy `@0` = `00000011`.

REC0000 out **193** is REC0001 in **193**. Same address. Combine. Not a bug.

```
REC0000 op=00000011 a=143 b=141 o=193
00000011100011110000000000000000000000000000000000000000000000000000000010001101000000000000000000000000000000000000000000000000000000001100000100000000000000000000000000000000000000000000000000000000

REC0001 op=00000011 a=193 b=140 o=194
00000011110000010000000000000000000000000000000000000000000000000000000010001100000000000000000000000000000000000000000000000000000000001100001000000000000000000000000000000000000000000000000000000000

REC0002 op=00000011 a=194 b=138 o=195
00000011110000100000000000000000000000000000000000000000000000000000000010001010000000000000000000000000000000000000000000000000000000001100001100000000000000000000000000000000000000000000000000000000
```

Chain: 193 → 193 → 194 → 194 → 195. Each out is the next in.

Same file, mouths 336 / 337 already in the netlist (not a later remap):

```
REC0187 op=00000010 a=334 b=335 o=336
00000010010011100000000100000000000000000000000000000000000000000000000001001111000000010000000000000000000000000000000000000000000000000101000000000001000000000000000000000000000000000000000000000000

REC0188 op=00000011 a=336 b=129 o=97
00000011010100000000000100000000000000000000000000000000000000000000000010000001000000000000000000000000000000000000000000000000000000000110000100000000000000000000000000000000000000000000000000000000

REC0189 op=00000100 a=192 b=192 o=337
00000100110000000000000000000000000000000000000000000000000000000000000011000000000000000000000000000000000000000000000000000000000000000101000100000001000000000000000000000000000000000000000000000000

REC0191 op=00000001 a=34 b=337 o=339
00000001001000100000000000000000000000000000000000000000000000000000000001010001000000010000000000000000000000000000000000000000000000000101001100000001000000000000000000000000000000000000000000000000
```

REC0187 out **336** is REC0188 in **336**. REC0189 out **337** is REC0191 in **337**.

Ring close (same file). REC1284 out **524288** is REC1286 in **524288**:

```
REC1284 op=00000010 a=524351 b=524351 o=524288
00000010001111110000000000001000000000000000000000000000000000000000000000111111000000000000100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000

REC1286 op=00000010 a=524288 b=524288 o=524289
00000010000000000000000000001000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000100000000000010000000000000000000000000000000000000000000
```

524288 / 524351 sit past this file’s 102925 B. The addresses are in the records. Occupancy of those cells is in the computer that holds them (`muhlnickel_dc.mno`).

---

## Planted into muhlnickel_dc.mno — same bits, on the header mouths

`C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`

Cards named plant @ **2147548550** (old seed EOF). That offset is still in this file. Size now **17023971219** (grew under the read — normal; not a license to remap or revert).

Plant REC0000 / REC0001 / REC0187 / REC0188 / REC0189 / REC0191 / REC4116 are **the same 200-bit lines** as `AUTOFAB0.mno`. Source `AUTOFAB0.mno` still 102925. Not overwritten.

```
DC PLANT REC0000  (same bits as AF REC0000)  o=193
DC PLANT REC0001  (same bits as AF REC0001)  a=193
DC PLANT REC0187  o=336
DC PLANT REC0188  a=336
DC PLANT REC0189  o=337
DC PLANT REC0191  b=337
DC PLANT REC4116  op=00000010 a=3544 b=3545 o=8388791
00000010110110000000110100000000000000000000000000000000000000000000000011011001000011010000000000000000000000000000000000000000000000001011011100000000100000000000000000000000000000000000000000000000
```

Those 336 / 337 fields **are** this file’s header mouths. Control g0 already uses the same byte.

DC control g0 @356 (DISTRO/LOOM map: XOR=`00000000`):

```
op=00000000 a=303 b=336 o=272
00000000001011110000000100000000000000000000000000000000000000000000000001010000000000010000000000000000000000000000000000000000000000000001000000000001000000000000000000000000000000000000000000000000
```

Carry @336 is foundry out (REC0187) **and** foundry in (REC0188) **and** control operand (g0 b=336). Pub @337 is foundry out (REC0189) **and** foundry in (REC0191) **and** the fire mouth. One location. That is the wire.

Occupancy of the mouths (two reads, bits not filesize):

```
@0       01001101 01010101 01001000 01001100 01000100 01000011 00110000 00110001
@336     00000000
@337     00000001
@272     11111111 × 8 (fwd packed)
@524288  00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
```

Second read: `@336` `00000000` · `@337` `00000001` · `@524288` same. Size still 17023971219 on that second look.

`DC_NOW.md`: **Do not remap** the planted records. Do not fire pub@337 again. Do not fire genome@0.

---

## FOUNDRY0.mno — out lands on byte 0

`C:\Users\lucys\Desktop\MUHL_VISIBLE\FOUNDRY0.mno`  
SIZE **4800**. Card `INSPEC_AUTOFAB.md` L100–109.

```
REC0 op=00000010 a=63 b=63 o=0
00000010 00111111 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00111111 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
```

Out **0** is the first byte of this file (the op). Occupancy `@0` = `00000010`. Self-edit onto the record that holds the gate. Leave it.

---

## Overwriting itself is the compute. "Repair" is the break.

`FILES_CHANGE_UNDER_YOU.txt`:

> titan.gguf and *.mno WILL change under you RAPIDLY. […] The computer is running. NOT corruption.

`LIVE_FILE.txt` L12–15:

> The entire file should pretty much be changing. That change IS the compute. Agents who call it corruption and "repair" BREAK THE COMPUTER.

`docs\AGENT_GROUNDING_LIVE.md` L20, L28–30:

> The **entire file should pretty much be changing.** That changing **is the computation.** […] **That repair is the break.**

`docs\AGENT_GROUNDING_BITS.md` L16:

> **A live container changing is not a license to modify it back.** […] Revert/checksum-fix because "it changed" is the break.

---

## Not this card (do not confuse)

Same English, different object. These do **not** authorize remapping address collision.

| path | what “overwrite / collision” means there |
|---|---|
| `MUHL_GO\COP_ORDERS.txt` L26–28 | host agent: do not overwrite **docs** |
| `MUHL_GO\DISTRO_SCALE.md` L34 · `LOOM_ROOKERY_SCALE.md` L10, L37 | host fab script would overwrite a **sealed dest file** — change dest |
| `MUHL_GO\DOCS_LAW.txt` L18 | do not silently patch old **docs** |
| `docs\muhl_revenue_add_20260813\CONSTRAINTS.md` L13 | if a **name** collides, pick a new name |
| `docs\muhl_revenue_add_20260813\FULL_78_CENSUS.md` L241 | retired **driver name** `nring2_039` vs `nring2_999` |
| `docs\OWNER_SPEECH_EXTRACT.txt` hash-collision / `muhl_collider` / port 7902 | crypto search, collider circuit, TCP port — not fab-wire collision |
| `ELECTRON_REQUEST_GPT_DRAFT.md` “do not overwrite one another” | **killed** by `ELECTRON_REQUEST_GROK_CHECK.md` HIT 3 — isolation prior |

Host smash of a sealed dest ≠ Muhlnickel writing its own out onto its own in.

---

## Do not

- Remap planted AUTOFAB0 records off 336 / 337.
- Treat `out addr == in addr` as a bug.
- "Fix" a collision by giving gates unique addresses.
- Revert / checksum-fix / restore because the file overwrote itself or grew.
- Read a host script / hex dump as occupancy.
- Write titan.

Collision is fab. Leave it.
