# TITAN V5 R04 recovery convergence gate

This directory is the **single rendezvous point** for current-V5 recovery of the score-facing behavior that shipped in submitted V3.1. It is an evidence/convergence gate, not another gameplay controller and not release authority.

Submitted authority is fixed to:

- source commit `a90d888f03987ef0b35cfd20ec3519c6144db08a`;
- archive SHA-256 `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`.

The gate does **not** import `r04_full_router.py`, the historical tape bank, V4 runtime, or a second producer. Leaf owners keep their current-ABI implementations. This package authenticates that those leaves are real source objects and that their economics are backed by raw paired cells before they can converge into one default-OFF V5 candidate.

## One recovery set, two topologies

Historical source provenance and current runtime staging are intentionally separate.

The submitted returned-action topology is:

`H8/L3 sale-window -> H4 strawberry -> row-order -> row-shed -> evening-flush -> B5/JIT`, with `fert_hand_boundary` around the inner action boundary and `B9 -> H3c` in the outer returned-action pipeline. The score-shipped **V231 late-COW** stateful feature is also required; this does not revive the submitted-OFF `cattle_early` window.

Current V5 cannot blindly replay historical wrapper order. The v2 manifest therefore hard-binds a separate `current_runtime_stages` map, including:

- `h3c_goose_rescue = pre_capacity`;
- `row_shed = final_market_order`;
- `b9_terminal_fertilizer = post_market`.

A manifest with a different staging map is a hard error. This keeps one hot V5 integration seam rather than treating historical return order as current runtime authority.

## Source custody: real Git objects, not claims

Every component declares a carrier `{pr, head_sha}` and repository-relative `source_paths`.

For authorizing evaluation the gate:

1. proves `head_sha` resolves to a Git commit;
2. reads each declared path from that commit with `git show <head>:<path>` rather than from the worktree;
3. records the actual Git blob SHA-1 and SHA-256 of those bytes;
4. computes an exact per-component source fingerprint from slot, runtime stage, carrier head, paths and source bytes.

A nonexistent head, missing path, source drift, whole-router/tape transplant, second producer, or forbidden submitted-OFF feature fails closed. A PR number is descriptive metadata; the Git object bytes are source authority.

## Economics custody: raw paired cells, not positive summaries

`PASS_PAIRED_ECONOMICS` no longer accepts caller-supplied `panel_digest`, mean deltas, or per-opponent summaries.

A PASS entry contains only:

```json
{
  "status": "PASS_PAIRED_ECONOMICS",
  "report_path": "relative/report.json",
  "report_sha256": "...64 lowercase hex..."
}
```

The report must be a regular file below the manifest directory. It is read **once**; the same captured bytes drive SHA-256 authentication and strict JSON parsing. Duplicate JSON keys and non-finite values are forbidden.

Each raw report contains exact `control_id`, `candidate_id`, engine/harness/opponent-pack identities and paired cells. Each cell supplies opponent, seed, seat, and control/candidate own+rival terminal scores. The gate itself:

- rejects duplicate `(opponent, seed, seat)` cells;
- requires both seats for every opponent/seed pair;
- derives opponent set, seed depth, cell count and panel digest;
- recomputes control/candidate margins and every aggregate/per-opponent delta;
- requires >=2 opponents, >=4 seeds per opponent, >=16 cells, non-negative aggregate margin and non-negative margin for every played opponent.

Every **leaf** report must also carry the exact `component_source_sha256` computed from that carrier's authenticated source. A positive report cannot be replayed after the leaf source changes.

The fully assembled candidate needs its own raw `combined_composition` report. That report binds the whole ordered `component_source_sha256`, so any carrier/head/path/source change invalidates the composition evidence.

`{"status":"PENDING"}` remains valid for source-ready work that has not completed matched economics; it blocks readiness without inventing evidence.

## Required semantic slots

v2 requires ten distinct current-ABI slots:

1. `sale_window_h8_l3`
2. `h4_strawberry_topup`
3. `row_order`
4. `row_shed`
5. `evening_flush`
6. `b5_carrot_jit`
7. `fert_hand_boundary`
8. `b9_terminal_fertilizer`
9. `h3c_goose_rescue`
10. `v231_late_cow`

One broad carrier may satisfy adjacent slots only by listing each semantic slot separately with its exact source/evidence binding. Missing V231-late or collapsing row-order/row-shed remains visibly blocked.

## What READY does not mean

Even `CURRENT_V5_COMPOSITION_READY_DEFAULT_OFF` grants **no**:

- production default flip;
- release authority;
- archive pointer publication;
- Kaggle submission authority.

The separate V3.1 champion-ratchet/release boundary still owns the final theorem that a releasable V5 must beat submitted V3.1 under its authenticated release panel.

## Run

From this directory:

```bash
python -B -m unittest -v test_composition_gate.py
python -O -B -m unittest -v test_composition_gate.py
python -m py_compile composition_gate.py test_composition_gate.py
python -B composition_gate.py /path/to/manifest.json --repo /path/to/commons --output /path/to/receipt.json
```

The Git checkout used for a real manifest must contain the declared component commits; the dedicated CI therefore fetches full repository history. Exit status is `0` for composition-ready, `3` for valid-but-blocked, and `2` for malformed/custody-breaking input. Receipt output is write-once.

Manifest schema: `titan-v5-r04-recovery-composition-gate/v2`. Raw economics report schema: `titan-v5-r04-paired-economics-report/v1`. The focused tests construct a complete positive fixture plus forged-summary, nonexistent-head, report-tamper, source-drift, duplicate-cell, missing-V231 and staged-order adversaries.
