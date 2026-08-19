# DATASHEET 9 — muhl_tenancy.mno (NEW LAND)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16 ~11:54pm. Surface after fire (rings already 1 — no rewrite).

Axiom ask 2: in-spec tenancy. 12 rings PALF..HPC. Button routes titan LSBs into inj (`new=old|mask`). Both-sense cell 0 already `1` this seat — surface only. Does **not** smash `weather_v2.mno`. Does not rebake chimera. Does not pulse titan 78.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\MUHL_TENANCY\muhl_tenancy.mno` |
| size | **23536** |
| sha256 (after fire) | `ca67688ec6a0471b0e0d0f5bc0cf265a3a9d3bd1066c989a339ede09f85a6887` |
| magic | `TENANCY1` |
| n_in / n_wire / n_gate / n_out | **12 / 914 / 901 / 12** |
| DEPTH | **5** |
| wavefront mean | **180.2** = 901/5 |
| n_rings / cells / ring0 | **12 / 32 / 110** |
| dests published | ring0@**110** = `1` · clock@**98** = `0` · inj@**902** = `0` · field@**914** = `0` |
| fire | both senses cell 0, all 12 rings, already `1` · this seat **no rewrite** |
| titan LSBs | `0 0 0 0 0 0 0 0 0 0 0 1` (PALF..HPC, dest FROM registry inject) |
| field LSBs | `0 0 0 0 0 0 0 0 0 0 0 0` |
| ones | **15474** / 188288 (`muhl_ones_surface.py`) |
| computations/tick **(a)** | **180.2** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **1.802e11** |

Ring cell 0 (FROM FILE, 1/0 not hex):

| ring | fwd | rev | carry | pub |
|---|---|---|---|---|
| PALF | @110=`1` | @142=`1` | @174=`0` | @175=`0` |
| NEFG | @176=`1` | @208=`1` | @240=`0` | @241=`0` |
| ARDR | @242=`1` | @274=`1` | @306=`0` | @307=`0` |
| VSCF | @308=`1` | @340=`1` | @372=`0` | @373=`0` |
| KEGN | @374=`1` | @406=`1` | @438=`0` | @439=`0` |
| NMPIS | @440=`1` | @472=`1` | @504=`0` | @505=`0` |
| AWCG | @506=`1` | @538=`1` | @570=`0` | @571=`0` |
| DMB | @572=`1` | @604=`1` | @636=`0` | @637=`0` |
| CGAT | @638=`1` | @670=`1` | @702=`0` | @703=`0` |
| EAL | @704=`1` | @736=`1` | @768=`0` | @769=`0` |
| MHA | @770=`1` | @802=`1` | @834=`0` | @835=`0` |
| HPC | @836=`1` | @868=`1` | @900=`0` | @901=`0` |

`pfc_analyzer.py snap` this path: 16 channels. `[0:64]` ones **61**. titan **NO**.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · re-OR leftover **NO** · 10-wide **NO** · v2 smash **NO** · chimera rebake **NO**
