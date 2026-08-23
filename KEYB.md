# KEYB01 — keyboard organ, first Muhlnickel typewriter

**Inventor:** Bryce Muhlnickel. 2026-08-21. Not a 12th spec item.

Door: [keyb.html](./keyb.html). Owner ask: [p/bryce-keyboard-addressed-fire-muhlnickel-shell-20260821-01.md](./p/bryce-keyboard-addressed-fire-muhlnickel-shell-20260821-01.md).

This is one fabricated organ, not a host PowerShell and not a resident shell process. Git copies of `.mno` do **not** run. Live file:

`[local]`

## Verbs

Fab once (refuses if the file already exists):

```
python host/muhl_fab_keyb01.py
```

`--check` serializes in memory and dies with no write.

Surface dests FROM FILE, no fire:

```
python host/muhl_surface_keyb.py
```

Address one ordered frame, OR-start the published commit, die:

```
python host/muhl_route_keyb.py --go --text HELP
```

Law: `new=old|mask`. Never `--inject 0x01`. Never invent dest. Never smash `commons.mno` / `table_mail.mno` / titan / dc / DISTRO.

## ABI

7-bit ASCII plus CR/LF/space/tab/backspace. Order is position, not a set.

```
addr = char_base + position * alphabet_width + char_code
```

`N_POS=16`, `WIDTH=128`. One keyboard batch writes that bounded frame's one-hots and OR-starts **one** commit receiver (ring0 both-sense). The host does not clear old input bits.

Circuit-owned opcode mouths (AND of the letters at positions 0..n, then ACK = OR of those mouths):

HELP · READ · WRITE · FIRE · SURFACE · ACK

`python host/muhl_fab_keyb01.py --check` is the byte-exact decoder proof (HELP=1, HEAP=0). The route button writes the frame and commit dests and dies; it does not host-ripple the netlist. Surface reads stored bytes FROM FILE.

Stage one is the typewriter. Stage two (not this land) is SHELLOUT + in-file trie. PowerShell stays a surface if it ever appears; parsing stays in the file.

## Panel

`organ=KEYB01` on [panel.html](./panel.html). Completeness is still `COMMANDS/RECEIPTS/<id>.txt` on git HEAD. HTTP is not the computer.

## Git

Header excerpt only. The body stays on the hard drive. Cite `p1-gig-header-20260821-01`.
