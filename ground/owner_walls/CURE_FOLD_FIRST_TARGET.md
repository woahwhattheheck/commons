# Cure-fold first target — same-job Bitcoin network target

State: **CHOICE_ONLY**. Rule: **SAME_JOB_LIVE_STRATUM_TARGET**.

The first target is not a hard-coded lottery value. For the exact live Stratum job/header selected for a later candidate run, derive the 256-bit Bitcoin network/block target from that same job's valid compact `nBits`. Never pair a header from one job with a target from another. This is not the pool share target communicated by `mining.set_difficulty`.

## Durable reference vector

Existing Commons evidence in `muhl/docs/MUHL_FOLD_PORT_MAP.md` supplies a real-data certification vector:

- job: `6a72bdc000001e1c`
- height: **961467**
- `nBits`: `0x17023ad4`
- target integer: `213572157266439505242940871974495870228360734370168832`
- canonical big-endian target: `000000000000000000023ad40000000000000000000000000000000000000000`
- current CLI little-endian `target32`: `0000000000000000000000000000000000000000d43a02000000000000000000`
- length: **32 bytes**
- bit length: **178**
- leading zero bits: **78**
- CLI target SHA-256: `be16de28c0358774add1605a2c5e8aa1fe2c6ea3ed98eaedc8ce377ab467e9e0`

`host/muhl_fold_header_add.py` now exact-binds the job's advertised `nBits` to the bytes in its derived header, rejects negative, zero, malformed, or overflowing compact targets, and emits `target_int.to_bytes(32, "little")` only after those checks.

## Boundary

Boundary fields are explicit: `live_target_claimed=false`, `live_run_executed=false`, `go=false`, `pulse_78=false`, `fire_337=false`, `titan_written=false`, `block_submitted=false`, and `profitability_claimed=false`. The stale FF×32/everything-wins target is rejected. The pool flow still uses its existing protocol-level `mining.authorize`; this change adds no Commons auth or admission gate. This choice only records and fail-closes the network-target derivation rule and its measured reference vector.
