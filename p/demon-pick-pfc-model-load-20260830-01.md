# Exact PFC model/load choice picked — 2026-08-30T06:47:30Z

Wall: `DIRECTIVES.md` section 20, `exact PFC model/load choice`.

## Decision

- model: `C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf`
- load/reference command: `python host/pfc_load.py C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf`
- connect command: `python host/pfc_harness.py connect C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf`
- state: `CHOICE_ONLY`
- live_load_executed: `NO`
- model_or_titan_bytes_written: `NO`
- inference_executed: `NO`
- host_forward_pass: `NO`

The choice stands until Bryce overrides it.

## Why this value

The current loader and harness independently default to the same configured 70B-class Q4_K_M GGUF. `host/pfc_load.py` uses a reversible `PFCLOAD1` descriptor/reference and PFC MMU wiring; `host/pfc_harness.py` connects the same model address. Current `ground/tokens/pfc.md` rejects small substitute models and keeps the host outside model forward-pass compute. Choosing the already-converged configuration closes the wall without inventing another model, loader, or address.

## Exact current sources at claim

- `host/pfc_load.py` blob `5b20b8b5e97489046fced7ac1985e7994a149aca`
- `host/pfc_harness.py` blob `c87cd15d783b7f6e10df392dbe54c3874be1d097`
- `ground/tokens/pfc.md` blob `475a5e48e459d3d0ed1f5801998629010a916f7f`
- fresh successor base `1c8debc8ccd78a8a8512317ad30507d732d67331`

## Boundary

This receipt does not run `pfc_load.py` or `pfc_harness.py`, inspect a private model, claim the selected file exists on this public seat, write `titan.gguf`, mutate a registry, execute inference, invent a destination, or use host compute as the computer. Live machine execution, if performed separately, requires exact file identity, preimage/range journal, reread, and its own durable receipt.
