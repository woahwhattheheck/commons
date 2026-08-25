# MUHL SELF-TRAIN ADDRESS CONTRACT — a Slack TAKING is not dests FROM FILE

Slack `1787648830.269449` (2026-08-25), TAKING
`muhl-self-train-address-contract-20260825-01`:

> Pure source-only Muhlnickel prerequisite on fresh Commons main
> `683d0837f6b4b665bcffd32b5b6766ea48414058`. Exact new paths only:
> `muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_self_train_address_contract.py`,
> root synthetic test, and `ground/MUHL_SELF_TRAIN_ADDRESS_CONTRACT.md`.
> No legacy trainer import/execute; no Titan/model/device/container/
> inference; no auth/login/allowlist/approval/identity/action tiers.
> Grok H-006 is candidate evidence only; larger xproc harness is
> deferred. Unresolved evidence stays UNRESOLVED, never zero.

That Slack body is **CLAIMED**. Talk is not a land. The claimed base
SHA is an **ANCESTOR** once current main moves. Ancestor is not
current head. Do not remint the taking id.

## Unique leftover (this run)

A source-only dest FROM FILE contract over public
`muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_self_train.py`.

It reads that trainer as text. It does not import it. It does not
execute it. It does not import `pfc_paths` or `titan_circuit`. It
does not open `titan.gguf`. It does not copy private LocalDeviceAgent
source. It does not smash `commons.mno`.

Named dests FROM FILE, when the trainer source is present:

| Key | Source fact |
|---|---|
| `name` | `muhl_self_train` |
| `reservoir_input` | `40022599232` |
| `receiver` | `muhl_reservoir` |
| `intake_header` | `24` |
| `write_ptr_rel` / `size_rel` / `capacity_rel` | `0` / `8` / `16` |
| `data_start_rel` | `24` |
| `file_marker` | `MUHLFILE` |
| architecture | `9 -> 8 -> 3`, `NW=107`, `WEIGHT_BYTES=214`, `PTR_BITS=30` |
| `INTAKE_CAPACITY` assignment | `50 * (1 << 30)` |

Live allocated `intake_off`, `weights_off`, circuit / state /
loop-bit offsets stay **UNRESOLVED**. A missing live measure is
**FINDER-FAILED** / **FINDER-UNVERIFIED**, never `0`.

## Named source conflicts are fail-closed BLOCKED

The trainer source still says `INTAKE_CAPACITY = 50 * (1 << 30)`
while comments say `1 GB`, and `PTR_BITS = 30` addresses 1 GiB.
That is a deterministic source-space conflict. Do not pick a
live number to manufacture a match.

Exact 30-bit two-byte wrap facts:

| Fact | Value |
|---|---|
| `max_pointer` | `1073741823` |
| `last_safe_start` | `1073741822` |
| `steps_before_wrap` | `536870912` |
| `required_bits` | `36` |
| `stride` | `2` |
| `address-mode` | `RELATIVE` |
| `data-start` | `24` |
| canonical hash | `d5acf732c3bd72a10e42630654ec5b5cef43a5e11b8dcab7396fcf6f4ec33165` |

Packet and leftover classify as **BLOCKED**, not `SYNTHETIC_OK`.
Genuinely live allocated offsets stay **UNRESOLVED**. Never `0`.
No named-default substitution.

## Integrity follow-up

Slack `1787651271.265499` TAKING
`muhl-address-contract-integrity-followup-20260825-02` is **CLAIMED**.
Do not remint it. Do not remint #2314, #2326, the first taking, or
`p/rivet-ship-address-conflict-fail-closed-20260825-01.md`.

Missing or malformed address facts stay **UNRESOLVED**. The validator
does not substitute `PTR_BITS=30`, `50 GiB`, or wrap constants.
Canonical payload binds `stride`, `address-mode`, `data-start`,
`status`, `reasons`, and every derived field. Validator recomputes
semantics and rejects **tampered** or **re-signed** records.

- 50 GiB / 30-bit remains **BLOCKED**
- 1 GiB / 30-bit relative is **OK**
- absolute-base without a live offset stays **UNRESOLVED**
- registry/header-disagreement is fail-closed **BLOCKED**
- live allocated offsets remain **UNRESOLVED**

## Derived stride math leftover

Slack `1787652385.567949` TAKING
`muhl-address-contract-stride-math-20260825-01` is **CLAIMED**.
Do not remint it. #2337 already landed the integrity bind.
This leftover is only the derived-math defect that bind exposed.

`pointer_space` accepts any positive stride. It must not keep the
two-byte formulas `last_safe_start=max_pointer-1` and
`steps_before_wrap = pointer_span // stride`.

Full-stride bound and modular cycle, including absolute mode/base:

| Fact | Formula |
|---|---|
| `last_safe_start` | `pointer_span - stride` when `stride <= pointer_span` |
| `steps_before_wrap` | `pointer_span / gcd(stride, pointer_span)` |
| two-byte 30-bit | still `1073741822` / `536870912` |
| stride 3 on 8-bit | `last_safe_start=253`, cycle `256`, not `254` / `85` |
| stride 6 on 8-bit | `last_safe_start=250`, cycle `128`, not floor `42` |
| absolute + base | same full-stride / modular numbers; overflow stays **BLOCKED** |

A stride larger than the pointer space leaves `last_safe_start`
**UNRESOLVED** (`stride_exceeds_pointer_space`). Floor division is
not wrap-cycle length. Live allocated offsets stay **UNRESOLVED**.

## What this leftover is not

- Not a legacy trainer import or execute
- Not host inference
- Not Titan / model / device / container mutation
- Not the larger xproc harness (**DEFERRED**)
- Not a remint of H-006 `MUHL_TRAIN_BRIDGE` — that card is
  **CANDIDATE** evidence only. Missing H-006 stays **UNRESOLVED**,
  never `0`
- Not a remint of `MUHL_RECEIPT_LANE` / `LDA_RECEIPT` / SUBZERO_*

## Measure

```text
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_self_train_address_contract.py
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_self_train_address_contract.py --root .
python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_self_train_address_contract.py --self-test
python3 -m unittest -v test_muhl_self_train_address_contract.py
```

X = Slack taking + claimed ancestor SHA + public trainer source +
these three leftover paths.
Y from bytes, same run: named dests FROM FILE + deterministic
50 GiB vs 30-bit source-space conflict fail-closed `BLOCKED` +
exact `max_pointer` / `last_safe_start` / `steps_before_wrap` /
`required_bits` / `stride` / `address-mode` / `data-start` +
full-stride bounds + modular cycle + canonical hash + live
offsets UNRESOLVED + H-006 CANDIDATE or UNRESOLVED.
Missing/malformed facts stay UNRESOLVED. Tampered or re-signed
records are refused. Non-divisor stride is not two-byte floor.
Z = missing path / invented live offset `0` / trainer import /
Titan write / SYNTHETIC_OK on a source-space conflict /
named-default substitution / FINDER-FAILED. Never `0`.

Calibration is known-present `ground/EXECUTE.md` + `ground/HEAD.md`
+ the Action Pad directive in the same run.

Follow-up Slack `1787650265.162889` hardens only these three
leftover paths. Do not remint #2314, the taking id, or
`p/rivet-ship-muhl-self-train-address-20260825-01.md`.

titan: **NOT_WRITTEN**. No auth. No gate. Open door. Blank `from=`
still lands as `UNSEATED`. Possessing the link is authorization.
