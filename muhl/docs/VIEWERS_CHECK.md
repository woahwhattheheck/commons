# VIEWERS CHECK

Checked 2026-08-15 against `LIVE_VIEWERS.md`. Test-Path + header read only. No viewer rewrite. No titan write.

Live titan: `C:\llm\models\titan.gguf` = **103,803,349,384** bytes.

---

## The set

| Viewer | Listed path | On disk? | Verdict |
|---|---|---|---|
| **Maze** | `C:\Users\lucys\Desktop\MUHLNICKEL.html` | yes | **LIVE** — title `MUHLNICKEL`, GATES EVALUATED HUD |
| **ALL BITS** (file) | `MUHLNICKEL_APP\live_viewer\all_bits.html` | yes | **LIVE** — `C:\Users\lucys\Desktop\MUHLNICKEL_APP\live_viewer\all_bits.html` |
| **ALL BITS** (URL) | `http://127.0.0.1:7884/all_bits.html` | n/a | **PATH WRONG** — bitserve default is **7883** (`bitserve.py` `DEFAULT_PORT = 7883`; page `BULK = http://127.0.0.1:7883`). 7884 timed out this check. File is live; listed port is not. |
| **Live binary viewer** | `C:\Users\lucys\Desktop\MUHLNICKEL_APP\binary_viewer.html` | yes | **LIVE** — title `MUHLNICKEL — Live Binary Viewer` |
| **Spectator** | `MUHLNICKEL_INVENTION_BURST\Distro\Archetypes\muhl_spectator.html` | yes | **LIVE** — `C:\Users\lucys\Desktop\MUHLNICKEL_INVENTION_BURST\Distro\Archetypes\muhl_spectator.html`. Surfaces `localhost:7880` (API down this check; that is the feed, not a missing file). |
| **Arcade** | `python host/pfc_arcade.py` | yes | **LIVE** — `C:\Users\lucys\Desktop\LocalDeviceAgent\host\pfc_arcade.py` |
| **Instruments** | `pfc_meter` · `pfc_scope` · `pfc_diff` · `pfc_cascade` | yes | **LIVE** — all four under `LocalDeviceAgent\host\` |

---

## Also on disk (same job, different render)

| Listed | On disk? | Verdict |
|---|---|---|
| `MUHL_STATE_ANALYSIS\muhl_live_view.py` | yes | **LIVE** — `C:\Users\lucys\Desktop\MUHL_STATE_ANALYSIS\muhl_live_view.py` |
| `MUHLNICKEL_APP\live_viewer\live_viewer.html` | yes | **LIVE** |
| `binary_rain*.html` | yes | **LIVE** — `live_viewer\binary_rain.html` and `binary_rain2.html` |
| `loom_surface.html` | not under `live_viewer\` | **PATH WRONG** if read as `MUHLNICKEL_APP\live_viewer\loom_surface.html` (False). **LIVE** at `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\loom_surface.html` |

`bitserve.py` itself is on disk next to ALL BITS (`MUHLNICKEL_APP\live_viewer\bitserve.py`).

---

## Stale FILESIZE on ALL BITS — do not fix

`all_bits.html` hardcodes the **2026-08-05** size:

```
const FILE_PATH   = "C:\\llm\\models\\titan.gguf";
const FILESIZE    = 93709785575;   // ~93.7 GB
```

Live titan is **103,803,349,384**. He keeps the partial builds. Do not "fix" the viewer. Do not restore titan because a viewer and the file disagree.

Same leftover constant on the rain pages (`FILESIZE_EXPECT = 93709785575`). Same rule: leave them.

---

## Wrong paths (only these)

1. **`http://127.0.0.1:7884/all_bits.html`** — wrong port. Use the file, or bitserve on **7883**.
2. **`loom_surface.html` under `live_viewer\`** — not there. Real file: `MUHLNICKEL_LOOM\loom_surface.html`.

Everything else in the table is live at the listed (or repo-relative `host\`) path.
