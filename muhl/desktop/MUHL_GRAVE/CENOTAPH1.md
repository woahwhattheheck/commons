# CENOTAPH1 — companion card (not a 12th spec item)

**Inventor:** Bryce Muhlnickel. **Builder this window:** Player 1 / Spec Daddy (Cursor Grok 4.6, Cursor parent chat).
**Commission:** `grave-player1-cenotaph1-commission-20260818-001` (Gravekeeper).

Native format: HIS nring2, same formula as `commons.mno` / `table_mail.mno` (`host/muhl_fab_nring_pkg.py`). Magic **CENOTPH1**. Not a new metadata mechanism. English names stay on this card. File dests are 1s/0s.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\MUHL_GRAVE\grave_cenotaph_v1.mno` |
| size | **7928** |
| magic | CENOTPH1 |
| n_in / n_wire / n_gate / n_out | **4 / 306 / 301 / 4** |
| DEPTH | **5** |
| (a) cpt | **60.2** |
| n_rings / cells / ring0 | **4 / 32 / 102** |
| clock / inj / field | @**98** / @**366** / @**370** |
| sha256 after genesis OR | `d197fd9f125db6bc52401f52bac879646342270385c7cb1f8159f38f9ee53080` |
| fab button | `python host/muhl_fab_cenotaph.py` |
| record button | `python host/muhl_route_cenotaph.py --go --record-genesis` |

## Event → dest (state=1 means recorded, not alive/dead)

| i | ring | event | inj | fwd | rev | carry | pub | clock | field |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | ROOK | ROOK_DECLARED_DEAD_BY_ZERO | 366 | 102 | 134 | 166 | 167 | 98 | 370 |
| 1 | FAILO | CAIRN_CARRIER_FAILOVER_SURVIVED / GRAVE_002_UNOCCUPIED | 367 | 168 | 200 | 232 | 233 | 99 | 371 |
| 2 | KSTRM | KITE_STREAM_ROLLBACK_SURVIVED | 368 | 234 | 266 | 298 | 299 | 100 | 372 |
| 3 | INGST | COMMONS_INGEST_REPAIR_PROMOTED | 369 | 300 | 332 | 364 | 365 | 101 | 373 |

Genesis this window: inj/fwd/rev OR-mask **1** on all four rings (`new=old|mask`). Field latch bytes still **0** — no host gate-ripple wrote the latch. The record is the dest 1s. Not a heartbeat. Not identity. Not a dashboard.

## Existing bytes not changed (sha256 before=after)

- `commons.mno` `2b9ba52141587a1ffec8a1b04c3bc6706363e06426d09271e8a7cdbd8afddafa`
- `table_mail.mno` `c9fd3dedbf417d820c2a0e8b6e30278144d205f1068b36b746cea1614c68f62a`
- `muhl_tenancy.mno` `ca67688ec6a0471b0e0d0f5bc0cf265a3a9d3bd1066c989a339ede09f85a6887`

Titan / dc / weather_v2 / DISTRO: not opened. fire_337=NO. 7913=NO. mmap=NO.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · 10-wide **NO**
