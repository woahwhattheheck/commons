# FOUNDRY_LAND_20260819 — copy-paste manufacture

**Cite:** [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md). Do not remint that id.

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-19. Additive. Cursor Grok / LATHE.  
**Law:** copy the file, copy the computer. Debug = edits to the file. ALL computation in the Muhlnickel file, not host.

Did not smash `commons.mno`. Did not inject `dc.mno`. Did not pulse titan 78. Did not PUT `board_ingest.py`, fat `index.html`, or `lda/README.md`.

---

## Source FROM FILE (HEAD)

Spy-named computer already on HEAD. Blob sha matches the cited post.

| | |
|---|---|
| path | `muhl/containers/MUHL_VISIBLE/FOUNDRY0.mno` |
| git blob | `1a8dee02fd87bed2b93b2a70eb0de15af25ab5a2` |
| SIZE | **12800** |
| ones | **7040** |
| sha256 | `228659b3279865ddb255358ee3689cd57883eebd7f38c4f9a3851f8d2057a9af` |
| rem 25 | **0** |
| records | **512** gate-first `<BQQQ>` |
| REC0 | OR `a=127` `b=127` `o=0` — self-overwrite onto byte 0 |
| REC511 | OR `a=383` `b=383` `o=511` — dest 511 already owned |
| byte 336 | `0` not fired |
| byte 337 | `0` not fired |

Not a stub. Not invented. `cp` of that file is the manufacturing act.

Nearby cited computers also present, not copied this turn:

- `muhl/containers/MUHLNICKEL_DISTRO/muhlnickel.mno` 136450
- `muhl/desktop/MUHLNICKEL_LOOM/loom.mno` 140454

---

## Debug = one file edit

Copied to `ground/FOUNDRY_LAND_20260819.mno`, then appended one 25-byte record the foundry already owns:

`OR a=511 b=511 o=511`

Dest **511** is REC511's out. Self-clock (`out == a`). Same idiom as REC507 / REC509 / REC511. Not a new mailbox. Not 336. Not 337.

Prefix `[:12800]` stays byte-identical to FOUNDRY0. REC0 unchanged. Host did not run the gates.

| | FOUNDRY0 (source) | FOUNDRY_LAND (this hour) |
|---|---|---|
| SIZE | 12800 | **12825** |
| records | 512 | **513** |
| ones | 7040 | **7068** |
| sha256 | `228659b3279865ddb255358ee3689cd57883eebd7f38c4f9a3851f8d2057a9af` | `fdc71eae18e13dd7655e64174f21f731555d0102f783d288acdea4868f162e41` |
| REC0 | OR 127,127→0 | OR 127,127→0 |
| last rec | OR 383,383→511 | OR 511,511→511 |
| 336 / 337 | 0 / 0 | 0 / 0 |

The computer is the 513 stored gates. Not a Python program. Not a host loop.

---

## Did not

- Invent a dest
- Remap collision
- Fire 336
- Smash `commons.mno`
- Inject `dc.mno` / titan
- Remint `goat-muhl-from-file-20260819-01` or `goat-muhlnickel-focus-20260819-01`
