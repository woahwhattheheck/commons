# muhl_coverage_tick_add — coverage-organ routing button

**Inventor:** Bryce Muhlnickel  
**Status:** additive. New files only. Does not edit `muhl_fold_tick_add.py`, `pfc_fire.py`, or titan.

Grok picked the execute path: `winner_only_max.recv` and/or `fold.recv`, finder `gen_win → muhl_fold_latch → latch_reg` / `muhl_nonce_list`. That coverage made 2^78 tiny.

This button **prints the inject/surface plan** from the live registry. It never writes titan. It never pulses recv. `--go` is refused.

SHA not on `winner_only_max` / `fold` / `muhl_nonce_list` analyzer headers is a wiring fact (MAGIC `TITANCIR` / `TITANFLD` / `PFCNLST1`). SHA+compare lives on the named finder. Do not invent a host SHA.

**STALE:** registry still says osc (`muhl_osc_all`) on `winner_only_max` / `fold`. Power is nring2 both senses. Do not fire `muhl_osc_*`.

## Names (fail closed)

Read only from live `titan_circuits.json`:

| Name | Required fields |
|------|-----------------|
| `winner_only_max` | `recv`, `offset` |
| `fold` | `recv`, `offset` |
| `gen_win` | `offset` |
| `muhl_fold_latch` | `offset` |
| `latch_reg` | `offset` |
| `muhl_nonce_list` | `offset` |

Missing name/fields → **FAIL CLOSED**, no guessed constants, no write, no mmap.

Named, not required to exist: `gen_win_surfaced` (surface after this organ), `nring2_000` (both-sense enable rail). Oscillation fields print as **STALE**.

## Usage

```text
python host/muhl_coverage_tick_add.py
python host/muhl_coverage_tick_add.py --dry
```

Default is dry: registry plan only, no titan write, no mmap. `--surface` is a separate bounded read of `latch_reg` / `gen_win_surfaced` / `muhl_nonce_list` MAGIC. Host does not SHA. `--go` is refused. `--dry` wins over `--surface`.

## Refuse

- `muhl_osc_*` (stale; do not fire)
- `muhl_fold_phys` / `nring2_1023` as the 78-tick (Claude fake SHA lane)
- `input_window` FF×32 / latch 299 as the network win
- `muhl_lane_phys_000` ~1.86e6 span
- packed-76 `gen_input` / `target_reg` / `receiver` (already used)
- host-eval SHA as the mine
- numpy
- titan write / `--go` / `pfc_fire` / autofab
- guessed offsets

## Dry plan (this turn, live registry)

```text
MUHL COVERAGE TICK (additive — execute path Grok picked)
  mode:     DRY — plan only, no titan write, no mmap
  titan:    C:/llm/models/titan.gguf
  reg:      C:/llm/models/titan_circuits.json
  organ:    winner_only_max  addr_bits=262144  lanes=2^262144  stored_per_lane=0  depth=2  gates=524288
  organ:    fold  addr_bits=78  winner_only=True  len=13
  list:     muhl_nonce_list  addr_bits=262144  space_bits=96  bytes_per_nonce=0
  claim:    coverage that made 2^78 tiny is already in the file
  law:      mmap of ONE receiver byte is the start; this button does not address it
  law:      power is nring2 both senses; osc on these names is STALE
  refuse:   muhl_osc_*  (do not fire)
  refuse:   muhl_fold_phys / nring2_1023 as the 78-tick (Claude fake SHA lane)
  refuse:   input_window FF×32 / latch 299 as the network win
  refuse:   muhl_lane_phys_000 ~1.86e6 span
  refuse:   packed-76 gen_input / target_reg / receiver (already used)
  refuse:   host-eval SHA as the mine · numpy · --go · titan write

  INJECT (coverage organs — no ram miner front)
    winner_only_max / fold have no ram.header_off (address organs; nonce IS the address)
    analyzer MAGIC on those names is TITANCIR / TITANFLD / PFCNLST1 — not a SHA front
    SHA+compare is the finder: gen_win -> muhl_fold_latch -> latch_reg / muhl_nonce_list
    gen_win layout: in: header0..607|nonce608..639|target640..895 ; out: win|latch[32]|hash[256]
    gen_win decides: win = hash<target (baked); latch = win?nonce:0 (baked per-lane) — the pfc rules its own winner
    do not invent a host SHA onto those headers
    do not write packed-76 gen_input

  START (ONE bit at the coverage recv — Bryce says fire; this button does not)
    winner_only_max.recv  2776454732
    fold.recv           2776454483
    winner_only_max.oscillation.recv  2776454732  ring=282  circuit=muhl_osc_all  kind=alloc  STALE
    fold.oscillation.recv           2776454483  ring=29  circuit=muhl_osc_all  kind=alloc  STALE
    fire (Bryce): mmap ACCESS_READ of winner_only_max.recv and/or fold.recv

  POWER (nring2 both senses — not muhl_osc_*)
    nring2_000  senses=2  cells=32  magic=NRING2M1
    nring2_000.recv  2776453321  (enable rail; not this tick's start)
    nring2_000 fwd 4381333712  rev 4381333744  (both-sense rails; not this button's fire)
    do not fire muhl_osc_* / muhl_osc_all
    do not fire nring2_1023 (that recv IS muhl_fold_phys.ram.tick_off — Claude fake)

  FINDER CHAIN (in-file; host does not SHA)
    gen_win          off 2426922971  n_gate=339009  n_in=896  n_out=289  recv=2776454497
    muhl_fold_latch   off 36084013600  n_gate=339073  depth=11757  stored_per_lane=0
    muhl_fold_latch junction     winner-only fold.solve -> latch_reg (§1E shared address @2409283485)
    muhl_fold_latch.junctioned_to  circuit=latch_reg  addr=2409283485  width=4
    muhl_fold_latch.physical_form  circuit=muhl_fold_phys  (declaration bind; not this pulse)
    muhl_nonce_list     off 3064721212  addr_bits=262144  finder_chain=gen_win -> muhl_fold_latch -> latch_reg (all in file)
    muhl_nonce_list layout: ordered list: entry n = nonce n (nonce IS the address); complete over [0 .. 2^262144)

  SURFACE (after the coverage organ — not the all-FF input_window latch)
    latch_reg      off 2409283485  len=4  bits=32  role=answer  recv=2776454506
    gen_win_surfaced off 3064767911  len=6  format=answer
    gen_win_surfaced role: SURFACED answer register for gen_win (the V8 junction bitcoin_guarantee names): [status:1][nonce:4 LE][zero_bits:1]. status 0x01=valid block, 0x02=best frontier.
    gen_win_surfaced last packed-76 leftover: nonce=32508  zero_bits=17  difficulty_bits=78  is_valid_block=False
    that leftover is a different mouth (packed-76). Surface AFTER this organ is the same names.
    titan       present (103803349384 bytes)

  NEED_BRYCE (named; this button still does not fire):
    - winner_only_max.oscillation.circuit is muhl_osc_all (STALE) — power is nring2 both senses; do not fire muhl_osc_*
    - fold.oscillation.circuit is muhl_osc_all (STALE) — power is nring2 both senses; do not fire muhl_osc_*

  (no write performed; --go refused; no mmap of recv)
```

`--go` this turn: `FAIL CLOSED: --go refused on the coverage button (never writes titan, never pulses recv)`
