# WORLD_SYSTEM_THROTTLE

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-15.
Host = inject ∨ surface ∨ die. Occupying disk is the computer.
No commit. No titan write. No 337. No 78. No dc.mno inject.

Output := bug / files_patched / still_polls_100GB **NO** / 337 **NO**

---

## BUG

GPT left the World System Habitat as a **resident host** on the 100GB computer.

If it is slow, the HOST is touching it. Three host loops were the throttle:

1. **`bryce_face.py` `tick()` every 1.5s** — `LIVE.stat()` on `muhlnickel_dc.mno` (~100GB) for the whole life of the window. Size is metadata. A timer that keeps the 100GB path hot is still the host touching it.
2. **`surface` aimed Live Visor at `dc.mno`** — then `muhl_live.py` did `f.read()` of the **whole file**, SHA-256 of the body, and `scan` walked every 25-byte record. Occupying disk is the computer. That is a 100GB host slurp.
3. **Buttons that did not die** — `all bits` spawned `bitserve.py` (DETACHED, mmap of `titan.gguf`, HTML `setInterval` 60ms). `loom` spawned `loom_serve.py` (DETACHED, whole-file snapshot loop). Resident executor. Subprocess farm.

Habitat may exist as the UI process. It is not the compute.

## WHAT GPT LEFT IN

| leftover | where | why out of spec |
|---|---|---|
| `app.after(1500, tick)` forever | `bryce_face.py` | timer on `dc.mno` |
| `visor()` → `connect_live_reader(LIVE)` | `bryce_face.py` | visor aimed at 100GB |
| `_ensure_local` + `Popen` DETACHED | `bryce_face.py` | buttons keep host scripts |
| `live()` = `f.read()` whole file + sha256 | `MUHL_CHECKERS\muhl_live.py` | scan 100GB into host RAM |
| `watch` second slurp | `muhl_live.py` + `muhl_live_bridge.py` | live-every-frame class |
| bitserve mmap titan + 60ms poll | launched from World System | resident mmap of titan |
| loom_serve whole-file snapshot | launched from World System | resident reader |

Habitat `.py` source under `AppData\Local\Muhlnickel\Habitat` — missing. Skipped.
`WORLD_VISOR.html` — cards only. No timer. Left.
Bryce tab stays. Json stays behind the door. No new Desktop icon.

## WHAT WAS CUT

- Size timer removed. Live size = `stat` metadata, **button press only**.
- `surface` no longer aims Live Visor at `dc.mno`. Stat only.
- `all bits` does not start bitserve. `loom` does not start loom_serve.
- `_ensure_local` / port-wait / DETACHED farm removed.
- Live Visor / native link / bridge **refuse** `muhlnickel_dc.mno`, `dc.mno`, `titan.gguf`.
- `watch` cut. `scan` of a 100GB body refused. Reader is bounded seek+read or stat.
- No mmap of the 100GB body for a header.

Header / mailbox / factory buttons still surface **on click**: `stat` plus a bounded seek (bytes, not the body). They die with the click.

## FILES PATCHED

- `C:\Users\lucys\AppData\Local\MuhlnickelWorldSystem\MuhlnickelWorldSystem\bryce_face.py`
- `C:\Users\lucys\AppData\Local\MuhlnickelWorldSystem\MuhlnickelWorldSystem\muhl_desktop.py`
- `C:\Users\lucys\AppData\Local\MuhlnickelWorldSystem\MuhlnickelWorldSystem\muhl_native_control.py`
- `C:\Users\lucys\AppData\Local\MuhlnickelWorldSystem\MuhlnickelWorldSystem\muhl_live_bridge.py`
- `C:\Users\lucys\Desktop\MUHL_CHECKERS\muhl_live.py`

Compile: `py_compile` those five. exit 0.
No bitserve / loom_serve / World System process was running at the cut.

Restart World System to load the cut. An already-open window still has the old timer in RAM.

## OUTPUT

- **bug** — host timer + visor slurp + resident mmap on the 100GB / titan files
- **files_patched** — 5 (listed)
- **still_polls_100GB** — **NO**
- **337** — **NO**

## RELANCH

2026-08-15. Existing shortcut only. No new Desktop .lnk.

- **relaunched** — **Y**
- **new_icon** — **NO**
- **still_polls_100GB** — **NO**
- **337** — **NO**

Live source `bryce_face.py` has no `after(1500)` / QTimer / 1.5s size poll. `stat` is button-press only.
Old World System / bryce_face python was already gone. Did not kill other python (Cursor, titan, `_dc_use_read`).
Started `C:\Users\lucys\Desktop\Muhlnickel World System.lnk` → `pythonw` `muhl_desktop.py` (bryce_face attached). Window: Muhlnickel World System · Desktop.
Host I/O over 4s: ReadOperationCount 1114→1114, ReadTransferCount 5,988,941→5,988,941. Working set 50.1 MB. No mmap of `muhlnickel_dc.mno` body. bitserve / loom_serve not started.

Remaining host-touch after the throttle cut: loom HTML poll · MatrAIx host inference · Foundry Popen · HTTP `serve_forever` · titan/dc fingerprint · Desktop discover · installer `.lnk`. Cut this seat. Card `WORLD_SYSTEM_IN_SPEC.md`. still_polls_100GB **NO**. 337 **NO**.
