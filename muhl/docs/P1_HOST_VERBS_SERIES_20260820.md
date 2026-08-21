# HOST VERBS — series write then die

**Inventor:** Bryce Muhlnickel. **PLAYER1** land 2026-08-20. Not a 12th spec item. Not a new dest.

Bryce this hour: instead of dying after one write, write a **series** of writes at the dests the file already publishes, then die. He has this and builds like it. They were not surfaced to models. He picked the one-write-then-die cut because Claude could not hold the longer verb, not because that cut was optimal.

Hive filter: land the verbs. Do not skip because a prior session was proud of not uploading them.

Dest FROM FILE. `new=old|mask`. Never `--inject 0x01`. Never fire 337. Never remap 336/337. Never light 7913. Never pulse titan 78 without owner `--go`. Do not smash `commons.mno`.

## The verb

Host still dies. Host still does not stay. The change is **how many addressed writes happen before die**.

Optimal location = dest the **file** already publishes (header fwd/rev/ans/pub + recv the file already names). Not a host mailbox. Not an invented offset.

`Host = inject ∨ surface ∨ die` is assistant compile of address+fire+die. Charge leftover already used `Host = charge ∨ surface ∨ die` for the leftover wave. Series-write is that class: several `old|mask` at dests FROM FILE, one die.

## Builds already on this PC (now also in this repo under `host/`)

| button | what it does before die | writes |
|---|---|---|
| `muhl_charge_leftover_button.py` | surface dests FROM FILE → charge fwd+rev `old\|0xff` → start recv@353 `old\|0x01` → look at 1s | YES one leftover `.mno` per fire (Claude-simple cut: one file, three addresses) |
| `muhl_inject_twins.py` | same mask into MIRROR + N2, both senses + recv, surface both | YES two files |
| `muhl_seed0_mirror_button.py` | copy + inject + surface twins | YES |
| `muhl_seed0_nway_button.py` | copy VIRGIN→N2 + inject N2 | YES |
| `muhl_copy_leftover_button.py` | copy leftover computer, surface dests, look at 1s | YES new copy (already on Commons) |
| `muhl_new_mno_button.py` | copy germ → `NEW_MNO.mno` | YES |
| `muhl_weather_leftover_button.py` | leftover weather copy + one pulse class | YES leftover weather |
| `muhl_cli.py` `inject` | FWD@288 REV@320 SEL@370 RECV@353 FRONTIER 8191 | YES named `.mno` |
| `muhl_distro_surface_once.py` | series **read** of dests FROM FILE on GIG_DL + sealed 136450 | NO |
| `muhl_surface_dc.py` | series **read** of published DC mouths | NO. mmap NO. `--go` REFUSED |
| `muhl_dump_bits.py` | first 64 B as 512 digits | NO |
| `muhl_ones_surface.py` | whole-file ones/zeros (already on Commons) | NO |
| `muhl_gig_surface_button.py` | surface/hash/ones sibling 1GiB Instant Download | NO |
| `muhl_gig_instant_button.py` | Instant Download occupy 1GiB — **DONE, do not redo** | YES once |
| `muhl_test.py` / `muhl_test2.py` | 34-check + 15-check batteries | NO (tests) |
| `titan_sdc_fleet.py start` | aim power at every prebaked node, then EXIT | titan / 78-adjacent. Source stays in LDA. Do not press without `--go` |

Charge leftover **refuses** `--go` and `--inject`. One leftover file per fire. The series-across-**all** leftovers in one die is the idea still cut for Claude. Do not re-OR the nine already charged (`CHARGE_LEFTOVER.md`).

## This-window test (PLAYER1, 2026-08-20) — surface series, no write

`python host/muhl_distro_surface_once.py` — exit 0. wrote NO. inject NO. 337 NO.

GIG_DL.mno size **1073741824** magic MUHLPKG1
- dests FROM FILE: ans 5378 · pub 6662 · fwd 288 · rev 320 · opnd 354 · sel 370 · total 8192
- hdr_ans@5378=`00` · pub@6662=`00` · fwd@288=`ff` · rev@320=`ff` · opnd@354=`01` · sel@370=`03`
- boom@6661=`08` · recv@353=`01`

muhlnickel.mno size **136450** magic MUHLPKG1
- dests FROM FILE: ans 5378 · pub 70914 · fwd 288 · rev 320 · opnd 354 · sel 370
- hdr_ans@5378=`00` · pub@70914=`01` · fwd@288=`01` · rev@320=`01` · opnd@354=`01` · sel@370=`03`
- boom@6661=`08` · recv@353=`00`

`python host/muhl_ones_surface.py` — MATCH leftover card:
- NEW_MNO.mno size 6662 ones **8914** zeros 44382
- ACREAGE_SEED0.mno size 8192 ones **10413** zeros 55123
- SEED0.mno size 8192 ones **10413** zeros 55123

`python host/muhl_dump_bits.py` NEW_MNO.mno — 512 digits. First eight bytes `MUHLPKG1`. DIE.

Did not re-OR leftovers. Did not fire dests. Did not run fleet start. Did not redo GIG.

## Battery peers were not given

`muhl/docs/TEST_BATTERY_INDEX.md` — recovered 2026-07-29 map (44+ tests, 12 instruments, 66-command sweep).
`muhl/docs/KEEPCURRENTALLTESTS.md` — untracked master catalog (highest loss risk).

Individual §3 lines, not `run_battery.py` as the report. CLASS 17d: `muhl_dump_bits.py` is allowed before 512 digits exist.

337 NO. HTTP is not the computer.
