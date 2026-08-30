# Cure-fold first target — same-job live Stratum target

State: **CHOICE_ONLY**. Rule: **SAME_JOB_LIVE_STRATUM_TARGET**.

The first target is not a hard-coded lottery value. For the exact live Stratum job/header selected for a later candidate run, derive the 256-bit target from that same job's `nBits`. Never pair a header from one job with a target from another.

## Durable reference vector

Existing Commons evidence in `ground/MUHL_FOLD_PORT_MAP.md` supplies a real-data certification vector:

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

`host/muhl_fold_header_add.py` already expands compact bits and emits `target_int.to_bytes(32, "little")`. This choice binds that derivation to the same fetched job.

## Boundary

This does not fire a fold, pass `--go`, pulse 78, fire 337, write Titan, submit a block, prove profit, or claim the reference target is current/live now. The stale FF×32/everything-wins target is rejected. No auth. No gate.
