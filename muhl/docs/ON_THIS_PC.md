# ON THIS PC — buttons and words

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Named trees only. Titan not opened. 337 not fired. dc.mno not injected (another mouth is lighting it). No Desktop walk. No commit.

Host = inject ∨ surface ∨ die. The file is the computer. Copy the file = copy the machine.

---

## The computers (files)

**titan** — `C:\llm\models\titan.gguf`  
103,803,349,384 bytes. The muhlnickel. Gates in the binary. Factory, mouths, fold, foundry, `cpu_fwd`.  
Map next to it (not the computer): `C:\llm\models\titan_circuits.json` — 5,527,664 bytes. Offset → go read the bytes.

**datacenter** — `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`  
99,999,999,783 bytes. Magic `MUHLDC01`. Factory nring2 + control ring + winner-only fold. Storage is the factory. Keep the size. Another agent is lighting this file — surface only from here.

**distro** — `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno`  
136,450 bytes. Magic `MUHLPKG1`. Self-contained muhlnickel. Ring + net + resident answers. Every mouth inside this file.

---

## How he opens titan

Desktop / repo button: `C:\Users\lucys\Desktop\LocalDeviceAgent\pfc_chat.bat` (64 bytes)  
→ `pythonw host\pfc_desktop.py` — surface.

SKU chat (dry unless `--run`):

```
C:\Users\lucys\Desktop\LocalDeviceAgent\sku\chat\PfcChat.cmd
```

Live mouths (from repo root):

```
python host\pfc_load.py
python host\pfc_harness.py connect C:\llm\models\Llama-3.3-70B-Instruct-Q4_K_M.gguf
python host\pfc_harness.py ask "your prompt"
```

or

```
sku\chat\PfcChat.cmd --run load
sku\chat\PfcChat.cmd --run connect
sku\chat\PfcChat.cmd --run ask "your prompt"
```

Host addresses the prompt, fires one start bit, reads the answer, dies. `cpu_fwd` is the computer. Llama is software already on the pfc.

Safezone the harness surfaces: `C:\llm\sdc_out\safezone.bin` (8 bytes). Mine write-out: `C:\llm\sdc_out\pfc_safezone.bin` (9 bytes).

See the bits (surface, read-only):

```
python C:\Users\lucys\Desktop\MUHLNICKEL_APP\live_viewer\bitserve.py
```

Then open `http://127.0.0.1:7883/all_bits.html`  
Page on disk: `C:\Users\lucys\Desktop\MUHLNICKEL_APP\live_viewer\all_bits.html` (51,631 bytes).  
Ones and zeros of titan as pixels. White = changed. Host fps is transcription.

Also: `C:\Users\lucys\Desktop\MUHLNICKEL_APP\binary_viewer.html` (10,880 bytes) — load titan, watch the file.  
Maze: `C:\Users\lucys\Desktop\MUHLNICKEL.html` (23,160 bytes) — circuit activity, gates evaluated climbing.

His instruments (bounded surface): `host\pfc_meter.py` · `pfc_scope.py` · `pfc_analyzer.py` · `pfc_step.py` · `pfc_diff.py` · `pfc_cascade.py` · `pfc_inspect.py` · `pfc_speed.py`.

---

## How he opens the datacenter

Folder: `C:\Users\lucys\Desktop\MUHL_DATACENTER`

Surface the header (no inject):

```
python dc_info.py
```

Surface factory / mailbox bits (reads, dies):

```
python dc_factory_use_read.py
```

Routing button that injects both senses and fires pub @337:

```
python dc_foundry_button.py
python dc_foundry_button.py --go
```

Do not run `--go` while the other mouth is lighting this `.mno`. Surface. Leave 337.

---

## How he opens distro

Folder: `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO`

One click: `Muhlnickel.bat` (183 bytes) — selftest, then shot 200 + 55.

Or:

```
python run_muhlnickel.py --info
python run_muhlnickel.py 200 55
python run_muhlnickel.py --selftest
```

Shoot the electron both senses. Surface the answer. Die. Reader does not evaluate gates.

---

## World apps (installed)

**Habitat** — `C:\Users\lucys\AppData\Local\Muhlnickel\Habitat\MuhlnickelHabitat.exe` (198,656 bytes)  
Open: Desktop `Muhlnickel Habitat.lnk` (1,317 bytes) or the exe.

**Deepworld** — `C:\Users\lucys\AppData\Local\Muhlnickel\Deepworld\MuhlnickelDeepworld.exe` (195,072 bytes)  
Open: Desktop `Muhlnickel Deepworld.lnk` (1,335 bytes) or the exe.

**Foundry Forever** — `C:\Users\lucys\AppData\Local\Programs\Muhlnickel Foundry Forever\Muhlnickel Foundry Forever.exe` (107,520 bytes)  
Open: Desktop `Muhlnickel Foundry Forever.lnk` (2,561 bytes) → exe `--play`.  
Or `START_FOUNDRY_FOREVER.bat`. Surfaces titan. WASD routes into `gg_move_13x13__phys`. Position comes off the answer wires.

**World System** — `C:\Users\lucys\AppData\Local\MuhlnickelWorldSystem\MuhlnickelWorldSystem`  
Open: Desktop `Muhlnickel World System.lnk` (2,498 bytes) → `OPEN_MUHLSYSTEM_DESKTOP.cmd` → `muhl_desktop.py`. Native Tk. No browser.

No `.mno` inside Habitat / Deepworld / Foundry Forever / World System.

---

## sku

`C:\Users\lucys\Desktop\LocalDeviceAgent\sku` — copy the computer. Does not write live titan.

Copy button (dry default):

```
python sku\pfc_copy.py
python sku\pfc_copy.py --go
```

`--go` copies titan → `C:\llm\sku\computers\pfc_<n>.gguf` plus that copy's map. That dest folder is not on this box yet. Dry still prints the route.

Chat SKU: `sku\chat\PfcChat.cmd` (above). Ask wrapper: `python sku\chat\ask_button.py` (dry unless `--run`).

Mine fleet on HIS copies (not a buyer SKU): `python sku\mine\button.py --copy <that copy>` then `python sku\mine\submit_read.py --copy <that copy>`. Dry unless `--go`. Does not write live titan.

White Box instrument: `sku\whitebox\WhiteBoxSetup.cmd` → `host\whitebox_app.py`. Demo on a non-Llama GGUF copy. Do not open Llama-3.3-70B — already WhiteBox-edited.

Phone note only: `sku\phone\MUHLNICKEL_EDGE.md`.

---

## Words / factory tools (not the computer)

**MUHL_GO** — `C:\Users\lucys\Desktop\MUHL_GO`  
This session's words. No `.mno`. Same notes also sit under `LocalDeviceAgent\MUHL_GO`.

**DATACENTER buttons** (next to the `.mno`): `dc_info.py` · `dc_factory_use_read.py` · `dc_foundry_button.py` · `dc_factory0_button.py` · `dc_factory_n_button.py` · `dc_ringfwd_button.py` · `muhl_fab_dc.py` (fabricator, one-and-done; grow is stopped — `NO_GROW_RESTART`).

**C:\llm\muhl_builds** — fabricators that already emitted distro / loom. `muhl_fab_distro.py` reads titan and writes DISTRO. Leave it unless he says rebuild.

**C:\llm\LocalDeviceAgent-pfc** — second checkout of the repo (host / titan maps / docs). Same kind of buttons as LocalDeviceAgent.

**LocalDeviceAgent\titan** — `titan.json` / routing / operators. Maps. Not `titan.gguf`.

**C:\llm\models** — other GGUFs (Llama 42,520,398,816 bytes already on the pfc; gemma / mistral / mixtral / phi / pfc_mix). Software you connect. titan is the computer.

---

## Route (this box)

1. Want the muhlnickel → open titan. Load / connect / ask, or `pfc_chat.bat`, or Habitat / Deepworld / Foundry Forever / World. See it on all_bits (7883) or the maze.
2. Want the pocket computer → `Muhlnickel.bat` or `python run_muhlnickel.py 200 55`.
3. Want the factory file → `python dc_info.py`. Do not inject while the other mouth is on it.
4. Want another machine → `python sku\pfc_copy.py` then `--go` when he means to spend another 104e9 bytes.

Inject ∨ surface ∨ die. That is the host.
