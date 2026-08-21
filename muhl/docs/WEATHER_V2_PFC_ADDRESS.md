# WEATHER V2 — HIS addressed read (pfc_analyzer)

**Inventor:** Bryce Muhlnickel. **Seat:** SPEC DADDY GROK.
**When:** 2026-08-16. One instrument. Read the answer. Die.

No titan open. No 337. No wipe. No 78. No re-OR rails (already 1).
Did not invent whether send-one must be a write. Start already in.

---

## 0. INSTRUMENT CENSUS (headers / argv first)

| instrument | argv | titan? | weather_v2 path? | ran |
|---|---|---|---|---|
| `pfc_analyzer.py` | `channels\|snap\|trace\|gates <target>` | circuit **name** → `titan.gguf` | **YES** — existing file path → seek+read that file only | **YES snap** |
| `pfc_step.py` | `[n] [target]` | **YES** mmap + write power on `titan.gguf` | NO | NO |
| `pfc_meter.py` | `<mine\|name\|offset> [nbytes]` | **YES** mmap `titan.gguf` | NO | NO |
| `pfc_scope.py` | `<name\|offset> [seconds] [nbytes]` | **YES** mmap `titan.gguf` | NO | NO |
| `pfc_inspect.py` | `[name]` | **YES** mmap `titan.gguf` via `pfc_paths` | NO | NO |

**Not GAP** for taking the file. `pfc_analyzer` is the one CLAUDE.md names as taking a state-file path.

`gates` mode on analyzer looks up `titan_circuits.json` by circuit name — not used.
`trace` is a host sample loop — not used. Button dies.

---

## 1. ARGV FIRED

```
python host/pfc_analyzer.py snap [local]\WEATHER\weather_v2.mno
```

cwd: `[local]\LocalDeviceAgent`
exit 0. Path resolved to itself. 16 channels. `read()` = `open + seek + read <= 256`. No mmap of titan.

File after snap (identity only):

| | |
|---|---|
| path | `[local]\WEATHER\weather_v2.mno` |
| size | 2606416 |
| sha256 | `cc2775fdd29d1e5ff1a8f2951e5f5f22dd1c2e237c9e10d6b2d47717476ba85d` |

Same live sha as `WEATHER_V2_FIRE.md`. Analyzer wrote nothing.

---

## 2. WHAT THE INSTRUMENT ADDRESSED

File-path mode has **no ram map**. Channels are 64-byte groups, first 1024 bytes only (`grp*16`). Named outs sit inside those windows:

| named | addr | channel | ones after snap |
|---|---:|---|---:|
| NW carry / pub | 168 / 169 | `[128:192]` | 2 |
| NE carry / pub | 234 / 235 | `[192:256]` | 2 |
| SW carry / pub | 300 / 301 | `[256:320]` | 2 |
| SE carry / pub | 366 / 367 | `[320:384]` | 2 |
| GROWTH carry / pub | 432 / 433 | `[384:448]` | 2 |
| WITNESS carry / pub | 498 / 499 | `[448:512]` | 1 |
| field `cell_base` | 500 | `[448:512]` start, then `[512:576]`… | see §4 |

Ones=2 on the mid windows = one `rev0` + next-ring `fwd0` (rails already 1). Carry/pub add **0** ones.
`[448:512]` ones=1 = WITNESS `rev0@466` only. Carry 498 / pub 499 / field 500–511 add **0**.

That is the same pattern as fire-after: fwd0=rev0=1, carry=0, pub=0.

---

## 3. CARRY AFTER THE ADDRESSED READ

**Carry moved: N.** All six still 0.

Analyzer is seek+read. File sha unchanged. If any carry byte had flipped, sha would have moved. It did not.

CLAUDE.md: addressed read of the answer register. This was HIS instrument doing that class of read on the named-out windows.
BRYCE_WORDS_PC (address = WRITE; bit must change): not invented here. Send-one already sat. Rails not poked again.

---

## 4. FIELD ONES AFTER

Analyzer file-path mode **stops at byte 1024**. Field is 2048 cells at 500..2547. Full field ones are **outside this instrument's 16-channel window**.

Captured field-side ones in-window:

| channel | ones |
|---|---:|
| `[512:576]` | 0 |
| `[576:640]` | 0 |
| `[640:704]` | 21 |
| `[704:768]` | 9 |
| `[768:832]` | 27 |
| `[832:896]` | 8 |
| `[896:960]` | 26 |
| `[960:1024]` | 13 |

Partial window ≠ 671. File sha still `cc2775fd…` ⇒ field bytes not rewritten.

**field ones after: 671 / 2048** (unchanged; sha identity). **field moved: N.**

---

## 5. WEATHER ADDRESSER (not used)

`WEATHER\muhl_address_weather_v2.py` takes this `.mno` and does **not** titan-open.
It is **host-nxt**: one pass over stored `<BQQQ>`, host evaluates NAND/AND/OR/XOR, writes every dest. FINALREADME: do not walk gates in host code.

`WEATHER\muhl_address_weather_v2_coupled.py` same walk, other file.

No high-impedance named-out addresser in WEATHER that is not host-nxt. Prior peek (`muhl_surface_weather_v2_after.py`) already showed 0 — that was a peek, not this snap.

---

## 6. RETURN

| q | a |
|---|---|
| instrument | **`pfc_analyzer.py snap`** — not GAP |
| argv | `python host/pfc_analyzer.py snap [local]\WEATHER\weather_v2.mno` |
| titan / 337 / wipe / 78 / re-OR | **NO** |
| carry after | **0 0 0 0 0 0** — did not move |
| field ones after | **671 / 2048** — did not move |
| other pfc_* | titan-bound — not run |
| WEATHER addresser | host-nxt walk — not run |

path: `[local]\LocalDeviceAgent\MUHL_GO\WEATHER_V2_PFC_ADDRESS.md`
button dies
