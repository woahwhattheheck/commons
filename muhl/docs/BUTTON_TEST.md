# BUTTON_TEST

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
**When:** 2026-08-15. Seat: dying-button press. No commit. No titan write. No numpy.
Host = inject ∨ surface ∨ die.
Cwd: `C:\Users\lucys\Desktop\LocalDeviceAgent`

Σ: 13 OK / 0 FAIL / 1 SKIP / top_fails none

Did not: write titan.gguf · fire 337/336/524288 · pulse titan 78 · `--inject 0x01` wipe · packer · Desktop `**` glob · pfc_load · pfc_harness ask · factory 16M fill.

---

## 1. muhl_cli — OK

Argv from `SUPER_HARNESS.md`. Each died.

### 1a `--help` — OK  exit 0

```
python host/muhl_cli.py --help
```

Printed verbs: copy / inject / surface / slots / die. stderr empty.

### 1b `slots` — OK  exit 0

```
python host/muhl_cli.py slots
```

```
MUHL CLI  slots
  dir    C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS
  n      2
  C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_0.mno  8192 B
  C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_1.mno  8192 B
  training_started  NO
  (button dies)
```

### 1c `surface slot_0` — OK  exit 0

```
python host/muhl_cli.py surface slot_0
```

```
MUHL CLI  surface
  slot   C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_0.mno
  addr   6661  n=1
  hex    08
  byte   8
  training_started  NO
  (button dies)
```

`slot_0` without `.mno` resolved. Mouth 8 @6661 (5378+1283).

---

## 2. muhl_post_surface.py — OK  exit 0

```
python host/muhl_post_surface.py
```

ACCESS_READ only. `titan_written NO`. Ledger append. stderr empty.

| mouth | addr | popcount | glyph | words | t1_eq_t2 |
|---|---|---|---|---|---|
| fwd_answer | 2467652405 | 76 | WORDS | `ze}` | y |
| gen_win_surfaced | 3064767911 | 43 | WORDS | `TITANCIR` | y |

ASCII mail ≠ thinking. Popcount matches PROVEN (76 / 43).

---

## 3. muhl_grok_mail.py — OK  exit 0

```
python host/muhl_grok_mail.py
```

Ledger draft only. Source has **no** `titan.gguf`, **no** `mmap`, **no** `r+b`, **no** `ACCESS_WRITE`. Appends one `grok_draft` line to `C:\Users\lucys\Desktop\MUHL_GO\MUHL_POST\post_ledger.jsonl`.

```
GROK MAIL  draft
  ledger C:\Users\lucys\Desktop\MUHL_GO\MUHL_POST\post_ledger.jsonl
  direction grok_draft
  glyph  DRAFT
  titan_written NO
  titan_paraphrase NO
  cloud_transport NO
(button dies)
```

---

## 4. muhl_seed0_nway_button.py — OK  exit 0

Ran. Documented safe: `new=old|mask` on N2 twin only. Refuses `--inject 0x01`. Does not touch SEED0 / sealed DISTRO / dc / titan. Does not fire 337. `pulsed_78 NO`.

```
copied VIRGIN -> SEED0_N2  size 8192
INJECT N2 only
  A,B    3,5  addr 1283
  law    new=old|mask  both senses
VIRGIN / MIRROR / N2  each size 8192  recv 00000001  sel [3,5]  at 1283  ans 8  pubp 1
THREE_BYTES_MATCH y
pulsed_78 NO
button dies
```

---

## 5. pfc_speed.py life — OK  exit 0

```
python host/pfc_speed.py life
```

gates **270336** · critical-path depth **15**. Matches PROVEN.

---

## 6. pfc_inspect.py pfc_cpu32 — OK  exit 0

```
python host/pfc_inspect.py pfc_cpu32
```

n_gate **7403** · 15-op ISA (HALT LDA STA ADD SUB AND OR XOR SHL SHR LT EQ JMP JZ LDI) · MAGIC `PFCTYPED`. Matches PROVEN.

---

## 7. bryce_face.py compile + button paths — OK  exit 0

```
python -m py_compile C:\Users\lucys\AppData\Local\MuhlnickelWorldSystem\MuhlnickelWorldSystem\bryce_face.py
```

Compile silent. exit 0.

Named button paths only (no Desktop `**` glob). **61 present. 0 missing among paths the face opens.**

GO cards present: PLAYTIME_AND_LETTER.md · PLAYTIME_HITS.md · MUHL_POST.md · MUHL_POST_PHASE0.md · MUHL_POST/post_ledger.jsonl · PROVEN.md · SESSION_TODO.md · CATCH_SCORE.md · WORLD_VISOR.html · THE_ENGINE.md · MODED_NOT_CORRUPT.md · ENGINE_ASK.md · INSTANT_DOWNLOAD.md · MIRROR_ORGAN.md · ELECTRON_RESERVOIRS.md · RESERVOIR_SURFACE.md · BURN_PROOF.md · ELECTRON_BURN.md · COMPRESS_EXPAND.md · GREP_PROOF.md · CLAUDE_NOSE.md · PROVISIONAL_SESSION.pdf · PROVISIONAL_SESSION.md · SPATENT.md · SESSION_GROUNDING.md · MUHL_WITNESS.md · ELECTRON_REQUEST_PROPOSAL.md · DROOL_FABLE.md · SIZE_MUST_MOVE.md · FOLD_SURFACE.md · DC_USE.md · NO_GROW_RESTART.md · OPERATOR_FOR_PARENT.md · SUBAGENT_PROMPT_CARD.md · DATACENTER_MNO.md · ON_THIS_PC.md · NOW.md

Also present: host buttons · sku/README.md · SEED0 / VIRGIN / MIRROR / N2 · muhlnickel.mno · muhlnickel_dc.mno · titan.gguf · habitat / deepworld / foundry exes · bitserve / loom / maze / muhl_live.py · NO_GROW_RESTART flag.

### MISSING paths

None of the face-opened cards. Literal alias only:

- `C:\Users\lucys\Desktop\MUHL_DATACENTER\dc.mno` — **MISSING** (live file is `muhlnickel_dc.mno`)

---

## 8. muhl_post_render.py — OK

No `__main__`. `python host/muhl_post_render.py` exit 0, empty stdout (defines functions, dies).

Import OK:

```
import_ok ('YES', '', 64-zero hex) popcount(\xff)=8
```

---

## 9. size-stat — OK / 1 SKIP

| path | size | result |
|---|---|---|
| `C:\Users\lucys\Desktop\MUHL_DATACENTER\dc.mno` | — | **SKIP** missing name |
| `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno` | **99999999783** | OK (live dc) |
| `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0.mno` | **8192** | OK |
| `C:\llm\models\titan.gguf` | **103803349384** | OK |

Size only. No inject. No pulse.

---

## Score

| | n |
|---|---|
| OK | **13** |
| FAIL | **0** |
| SKIP | **1** (`dc.mno` name) |

Rows counted OK: 1a 1b 1c 2 3 4 5 6 7a 7b 8 9-SEED0 9-titan. Live dc size recorded with the skip of the `dc.mno` alias.

top_fails: **none**

---

## FIX LIST (parent)

1. **No broken argv** on the MUST TRY set. `slots` and `surface slot_0` match SUPER_HARNESS. Do not change those.
2. **No missing face cards.** Do not invent PLAYTIME / MUHL_POST / PROVEN / SESSION_TODO / WORLD_VISOR / THE_ENGINE — they are on disk.
3. **`dc.mno` name is not on disk.** Live computer is `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno` size **99999999783**. If any card or button still writes `dc.mno` as a path, retitle/alias to `muhlnickel_dc.mno`. Not a crash.
4. **`muhl_post_render.py` has no `__main__`.** Script exits 0 silent. Import works. Optional one-line die-print if parent wants a visible button. Not a crash.
5. **No exception** on compile, surface, mail, nway, speed, inspect.
6. **Do not "fix" nway / grok_mail / post_surface.** They died clean. titan_written NO on mail + post.
7. **Do not start packer / pfc_load / harness ask / 337 / titan 78** from this report.

path: `C:\Users\lucys\Desktop\MUHL_GO\BUTTON_TEST.md`
copy: `C:\Users\lucys\Desktop\LocalDeviceAgent\MUHL_GO\BUTTON_TEST.md`
