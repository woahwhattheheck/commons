# TITAN V5 R04 recovery convergence gate

This directory is the **single rendezvous point** for current-V5 recovery of the
score-facing behavior that shipped in submitted V3.1. It is a control/evidence
gate, not another gameplay controller.

Submitted authority is fixed to:

- source commit `a90d888f03987ef0b35cfd20ec3519c6144db08a`;
- archive SHA-256 `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`.

The gate intentionally does **not** import `r04_full_router.py`, the historical
tape bank, V4 runtime, or any recovered candidate. Leaf owners keep their
current-ABI source and economics work. This package authenticates that those
leaves converge into one V5 topology rather than becoming independent versions.

## Exact submitted topology

The exact submitted winner used a first-line R04 whole-route delegate. Recovery
on current V5 is represented by topology, not by copying that delegate:

1. inner returned-action pipeline:
   `sale_window_h8_l3 -> h4_strawberry_topup -> row_order -> row_shed -> evening_flush -> b5_carrot_jit`;
2. `fert_hand_boundary` wraps the inner producer/action boundary and is the
   only recovery slot allowed to delegate to the single current parent;
3. outer returned-action pipeline:
   `b9_terminal_fertilizer -> h3c_goose_rescue`.

`row_order` and `row_shed` are deliberately separate. The submitted stack ran
them as adjacent stages, while current swarm ownership is also separate: the
market-microstack recovery owns row-order/evening semantics and the dedicated
row-shed carrier owns row-shed. Collapsing them would hide a missing transform
and could falsely mark V5 composition complete.

Historical source features that were OFF/identity in the exact submitted winner
(`cattle_early`, `kill_late_water`, `strawberry_endgame`, `dribble_dump`,
`mirror_horizon`, opening roundtrip) are forbidden as active recovery slots.
R01/R02/R03 standalone resurrection is also forbidden because submitted
`r04_sale_window=true` took precedence.

## Leaf evidence is necessary, not sufficient

Each component entry binds:

- one unique semantic slot;
- exact current carrier PR/head and source-receipt SHA-256;
- current-ABI status and producer ownership;
- current source paths (with direct whole-router/tape transplant rejected);
- either `economics: {"status": "PENDING"}`, or a completed
  `PASS_PAIRED_ECONOMICS` receipt.

A leaf PASS binds a panel digest, distinct `v5c:` control/candidate identities,
>=2 opponents, >=4 identical seeds per opponent, both seats, >=16 paired cells,
non-negative aggregate paired margin delta, and a per-opponent margin map whose
keys exactly equal the played opponents and whose every delta is non-negative.
This prevents a favorable opponent from masking a regression on another played
opponent.

One carrier may legitimately satisfy more than one adjacent semantic slot if
its source receipt proves each slot; the manifest still lists those slots
separately so no submitted behavior can disappear behind a broad carrier name.

## Combined composition evidence is mandatory

Individually positive leaves can interact badly. Therefore all nine leaf PASSes
still do **not** make the stack composition-ready.

The gate deterministically hashes the exact submitted authority + topology +
ordered component source identities (slot, current-ABI flag, producer ownership,
source paths, carrier PR/head, source receipt) into `component_source_sha256`.
The manifest must then carry a separate `composition_economics` receipt for the
fully assembled candidate. A composition PASS must bind that exact
`component_source_sha256` and satisfy the same paired panel/per-opponent floors.
If the combined receipt is PENDING, stale, built from even one different head,
or negative on any played opponent, the gate remains `BLOCKED`.

This is the core single-V5 invariant: source-green leaf islands are evidence;
only the exact assembled stack with matched current economics can become
`CURRENT_V5_COMPOSITION_READY_DEFAULT_OFF`.

## Hard lineage rules

A manifest is rejected if it asks for any of the following:

- V4 thaw/remint;
- historical whole-router/tape transplant;
- production default flip;
- release authorization;
- Kaggle submission.

The composition-ready result explicitly grants **no** default-flip, release, or
Kaggle authority. The separate V3.1 champion-ratchet/release boundary remains
responsible for the owner's final `V5 > submitted V3.1` acceptance theorem.

## Run

From this directory:

```bash
python -B -m unittest -v test_composition_gate.py
python -O -B -m unittest -v test_composition_gate.py
python -m py_compile composition_gate.py test_composition_gate.py
python -B composition_gate.py /path/to/manifest.json --output /path/to/receipt.json
```

Exit status is `0` for composition-ready, `3` for a valid but blocked manifest,
and `2` for malformed or invariant-breaking input. Receipt output is write-once.

The manifest JSON uses schema `titan-v5-r04-recovery-composition-gate/v1`.
See `test_composition_gate.py::valid_manifest` for a complete positive fixture;
for source-ready evidence whose economics are not complete, use exactly
`{"status": "PENDING"}` for that leaf or the final `composition_economics`.
