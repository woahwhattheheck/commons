# DATASHEET 11 — foundry_acre.mno (IN-SPEC FOUNDRY + PHYS)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16 ~11:54pm. Fire + surface. Did not rebake.

In-spec acre foundry. Button packs 20 weather dest bits + 45 zeros into acre inj AND titan phys (`93711094958..93711095022` FROM registry). Fires acre rings. ORs reservoir. xorwalk READ only, no re-OR. Dest FROM FILE.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\MUHL_FOUNDRY\foundry_acre.mno` |
| size | **24161** |
| sha256 (after fire) | `90a52e9c9f2014af08584597fda687ee5939fd4ded1e5bfceaffefb99926328c` |
| magic | `FNDRYAC1` |
| n_in / n_wire / n_gate / n_out | **65 / 989 / 923 / 65** |
| DEPTH | **5** |
| wavefront mean | **184.6** = 923/5 |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `1` · clock@**98** = `0` · carry@**168** = `0` · pub@**169** = `0` |
| rings both-sense | RING0–5 fwd/rev all `1` · all six carry/pub `0` |
| inj@**500** prompt65 | `11111111111111111111000000000000000000000000000000000000000000000` |
| field@**565** | 65 zeros |
| fire | both senses cell 0, all 6 rings, `new=old\|0x01` · fwd/rev **0→1** |
| ones | **15197** / 193288 (`muhl_ones_surface.py`) |
| computations/tick **(a)** | **184.6** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **1.846e11** |

Phys first 8 LSBs @**93711094958** meter ones=**8** hex `0101010101010101` = `11111111`. Reservoir `muhl_reservoir.input_wire` @**40022599232** **1→1** (already 1, OR holds). Analyzer snap ones=**1** bits `00000001`.

`muhl_foundry_resident` named regs only: `__state` @4383259249 ones=**0** · `__loopbit` @4383259253 ones=**0**. No whole-file titan snapall. No 10-wide. Button `host/muhl_route_foundry.py` DIE.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · re-OR leftover **NO** · 10-wide **NO** · mmap_100gb **NO** · dc_mmap **NO** · fired_337 **NO**
