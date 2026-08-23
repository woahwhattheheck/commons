# PANEL — git tickets, hard-drive computers

**Inventor:** Bryce Muhlnickel. 2026-08-21. Not a 12th spec item.

Door: [panel.html](./panel.html). Models post `to=PANEL`. Ingest writes `COMMANDS/<id>.txt`. The laptop button addresses or surfaces the **live** file, then `COMMANDS/RECEIPTS/<id>.txt` must land on **git HEAD**.

A `.mno` in this git repo is **not configured to run**. It is an excerpt / picture of a computer that lives on the owner's hard drive. HTTP is not the computer. GitHub does not compute.

**READ is sufficient voltage (on device, 2026-08-23).** A READ operation, not just a write, is enough electrons to propagate the bit change. Surface / dump / analyzer are READs. Do not wait for a second write. Card: [ground/READ_IS_VOLTAGE.md](./ground/READ_IS_VOLTAGE.md).

## Verbs (in spec only)

Allowed:

- `kind=surface` — dests FROM FILE, write receipt, **no fire**
- `kind=dump` — `muhl_dump_bits.py` on a named live path, receipt is the 512 digits
- `kind=analyzer` — `pfc_analyzer.py snap` on a named live path

Law: `new=old|mask`. Never `--inject 0x01`. Dest FROM FILE. Never invent dest. Never mmap titan / dc bodies. Never 10-wide.

## Refused

**Verification and proof are not allowed on this panel.** MATCH is held. Do not ask this panel to check whether the muhlnickel works. That question is settled. The same question is answered by **use** or **building**, not a comfort test.

Refused kinds / tells: `prove` · `verify` · `test` · `battery` · `life --test` as a greeting · `name a third` · `does it work` · reminting MATCH.

## Ticket

Post from [panel.html](./panel.html), or copy `COMMANDS/TEMPLATE_USE.txt` to `COMMANDS/<id>.txt` (id 8–80 `[A-Za-z0-9._-]`).

```
id=your-use-id-20260821-01
kind=surface
approved=YES
claimed_from=YOURNAME
purpose=USE
```

`purpose` must be `USE` or `BUILD`. `VERIFY` / `PROOF` is refused.

Then the laptop runs once and dies:

```
python host/muhl_panel_once.py --go
```

Not a 10-minute watcher. Duplicate id = original receipt.

## Complete request

A request is not done at ntfy 200. It is done when `COMMANDS/RECEIPTS/<id>.txt` is a file on **git HEAD**. GitHub grabbed the answer into this repo. Pages can lag. The file is the receipt.

## Live vs excerpt

| live (runs) | git excerpt (does not run) |
|---|---|
| `C:\Users\lucys\Desktop\MUHL_COMMONS\commons.mno` | `excerpts/20260821/commons.mno` |
| `C:\Users\lucys\Desktop\MUHL_COMMONS\table_mail.mno` | `excerpts/20260821/table_mail.mno` |
| other Desktop `.mno` | copies under `excerpts/` |

titan / dc bodies are not in this repo. A chunk is enough to see the picture. Do not 10-wide.
