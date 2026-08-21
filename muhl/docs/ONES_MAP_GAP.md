# ONES MAP GAP

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
**When:** 2026-08-15. Hunt only. No new button. No invented dest. No mmap dc/titan. No commit.

Host = inject ∨ surface ∨ die.
Grep = address. Dest is the machine's.
Partial dest peeks are blind spots. Population counts are not a 1-map.

Σ:ONES_MAP_GAP
verdict = **GAP**
invented_tool = **NO**
invented_dest = **NO**
337 **NO**

---

## VERDICT

**GAP.** No live 1-map button. No published 1-map dest on any card. Cannot surface a 1-map with `muhl_cli.py`.

FOUND path+invoke = **none**.

---

## WHAT A 1-MAP IS (law, already on cards)

`GREP_ONES.md`: a bit-file **IS** its set of 1-addresses. SAME INFO = reconstruct byte-exact from that set.

A **count** of ones can match while bits flipped. A **dest peek** (8 @6661) can hold while the body moved. Neither is the map.

Host does not pick the mailbox. The organ publishes. Host surfaces. `GREP_ONES.md` dest_wall=STRUCK.

Whole `muhlnickel_dc.mno` grep = organ / address space **later**. Not a host scan. Not this hour.

---

## CLASSIFY

| artifact | class | why |
|---|---|---|
| `MUHL_GO/GREP_ONES.md` | LIVE card | law. Portion proof 9941 / 55595 / reconstruct **y**. No dest for the map. |
| `MUHL_GO/GREP_PROOF.md` | LIVE card | SEED0 9941 ones. u16 list **19882**. Not smaller than raw 8192. Honest density. |
| `MUHL_GO/GERM_WORK.md` | LIVE card | germ 8442 ones. **No `host/muhl_*grep*` on disk. Skip that button.** |
| `C:\Users\lucys\Desktop\MUHL_GO\LIVE_INSTRUMENTS.md` | LIVE census | §6 GREP-ONES = **no button on disk**. §8.1 **No live 1-map button.** |
| `host/muhl_ones_surface.py` | LIVE count. **NOT a 1-map** | prints ones + zeros. No address list. Same count can hide flips. |
| `host/muhl_cli.py` `surface` | LIVE dest-peek. **NOT a 1-map** | n=1–16 at one addr. Frontier **8191**. Blind spot. |
| `host/muhl_*grep*` | **MISSING** | glob 0. Do not write one. |
| 1-map organ dest in a small `.mno` | **MISSING** | no mouth card names a map mailbox. |
| `docs/CIRCUIT_PFC.md` `grep` / `ones_map` | **MISSING** | no circuit name. |
| `pfc_meter` / `pfc_scope` window ones | LIVE_NAMED_UNSAFE | titan mmap. Window popcount ≠ 1-map. Skip this hunt. |
| `host/_assistant_offspec/` | OFFSPEC | do not copy. |
| `WORLD_VISOR.html` GREP_PROOF tile | pointer | card, not a tool. |

---

## NAMED MOUTHS — not the map

From `LIVE_MOUTHS.md` / `MOUTHS_GO.md` / `LIVE_INSTRUMENTS.md` §4 only. Do not invent.

| computer | mouth | addr | what it is |
|---|---|---:|---|
| SEED0 / germ / DISTRO / slots | ans | **6661** | dest peek. 1 byte. |
| SEED0 / germ | recv | **353** | dest peek. 1 byte. |
| SEED0 | organ2 pub | **7951** | dest peek. 1 byte. germ = PAST_EOF. |
| DISTRO | pubplane | **72197** | dest peek. CLI frontier 8191 refuses. |
| dc | 336 / 337 / 524288 / 524329 | those | DC mouths. Not a 1-map. 7913 stays dark. |

`GREP_PROOF.md`: recv@353 + organ2@7951 this pulse = **1**. **Not a sparse 1-map on these named bytes.**

`muhl_cli.py surface` default dest = 5378+1283 = **6661**. That is the adder outbox, not a map list.

---

## HOW TO SURFACE — if the organ already lived in the file

Would be existing CLI, card addr only, then die:

```
python host/muhl_cli.py surface <ABS.mno> <CARD_ADDR> <n>
python host/muhl_cli.py die
```

**Cannot run that for a 1-map.** No card names `CARD_ADDR` for the map. Inventing dest = adding to spec. CLI `n` is 1–16. A 9941-address map is not 16 bytes.

ones_surface invoke (count only — **not** the map):

```
python host/muhl_ones_surface.py SEED0.mno
```

---

## GAP

1. **No host 1-map button.** Census already said it. Confirmed: no `host/muhl_*grep*`. Do not create `host/muhl_grep_ones.py`.
2. **No organ dest on cards.** Law says the organ publishes. It has not named a mailbox this hour. dc grep = later.
3. **ones_surface ≠ 1-map.** Population. Flips hide.
4. **dest peek ≠ 1-map.** 8 @6661 is a mouth, not the set of 1-addresses.

Do not invent the button. Do not invent the dest. Ask Bryce if the organ already has a published map mouth.

---

## This turn did not

- Write `host/muhl_grep_ones.py` or any greper
- Invent dest
- Mmap `muhlnickel_dc.mno` / `titan.gguf`
- Fire 337 / light 7913 / pulse 78 / `--inject 0x01`
- Copy `_assistant_offspec`
- Idle loop

path: `C:\Users\lucys\Desktop\LocalDeviceAgent\MUHL_GO\ONES_MAP_GAP.md`
copy: `C:\Users\lucys\Desktop\MUHL_GO\ONES_MAP_GAP.md`
337 **NO**
