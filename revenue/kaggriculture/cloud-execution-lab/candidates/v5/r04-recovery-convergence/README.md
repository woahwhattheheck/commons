# TITAN V5 R04 recovery convergence gate

This directory is the **single rendezvous point** for current-V5 recovery of the score-facing behavior that shipped in submitted V3.1. It is an evidence/convergence gate, not another gameplay controller and not release authority.

Submitted authority is fixed to:

- source commit `a90d888f03987ef0b35cfd20ec3519c6144db08a`;
- archive SHA-256 `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`.

The gate does **not** import `r04_full_router.py`, the historical tape bank, V4 runtime, or a second producer. Leaf owners keep their current-ABI implementations. This package authenticates that those leaves are real Git objects, coexist byte-for-byte in **one assembled V5 commit**, and have raw paired-cell economics bound to the exact sources.

## One recovery set, two topologies

Historical source provenance and current runtime staging are intentionally separate.

Submitted returned-action topology:

`H8/L3 sale-window -> H4 strawberry -> row-order -> row-shed -> evening-flush -> B5/JIT`, with `fert_hand_boundary` around the inner action boundary and `B9 -> H3c` in the outer returned-action pipeline. The score-shipped **V231 late-COW** feature is independently required; this does not revive the submitted-OFF `cattle_early` window.

Current V5 cannot blindly replay historical wrapper order. Schema v2 therefore hard-binds a separate `current_runtime_stages` map, including:

- `h3c_goose_rescue = pre_capacity`;
- `row_shed = final_market_order`;
- `b9_terminal_fertilizer = post_market`.

A manifest with a different staging map is a hard error.

## Source custody: real carrier objects plus one composition tree

Every semantic component declares:

```json
{
  "slot": "...",
  "current_abi": true,
  "producer_ownership": "none",
  "source_paths": ["repository/relative/path.py"],
  "carrier": {"pr": 12345, "head_sha": "...40 hex..."},
  "economics": {"status": "PENDING"}
}
```

For authorizing evaluation the gate:

1. proves every carrier `head_sha` resolves to an actual Git commit;
2. reads each declared source path from that carrier with `git show <head>:<path>` rather than from the worktree;
3. records actual Git blob SHA-1 and SHA-256 identities;
4. computes an exact per-component source fingerprint;
5. proves manifest `composition_git_commit` resolves to a Git commit;
6. reads the **same path** from `composition_git_commit` and requires byte-for-byte equality with the authenticated carrier source.

This turns “single V5” into a machine-checked invariant: a READY receipt cannot be assembled from ten mutually incompatible branch islands. The declared leaf sources must already coexist unchanged in one concrete Git tree.

A nonexistent carrier head, missing path, missing composition commit, composition-tree source drift, historical whole-router/tape transplant, second producer, or forbidden submitted-OFF feature fails closed. The PR number is descriptive metadata; Git object bytes are source authority.

## Economics custody: raw paired cells, not positive summaries

`PASS_PAIRED_ECONOMICS` no longer accepts caller-supplied panel summaries. A PASS entry contains only:

```json
{
  "status": "PASS_PAIRED_ECONOMICS",
  "report_path": "relative/report.json",
  "report_sha256": "...64 lowercase hex..."
}
```

The report must be a regular file below the manifest directory. It is read **once**; those captured bytes are both SHA-authenticated and strictly parsed. Duplicate JSON keys and non-finite values are forbidden.

Each raw report contains exact control/candidate `v5c:` identities, engine/harness/opponent-pack identities, and paired cells. Each cell supplies opponent, seed, seat, and control/candidate own+rival terminal scores. The gate itself:

- rejects duplicate `(opponent, seed, seat)` cells;
- requires both seats for every opponent/seed pair;
- derives opponent set, seed depth, cell count and panel digest;
- recomputes control/candidate margins and aggregate/per-opponent deltas;
- requires >=2 opponents, >=4 seeds/opponent, >=16 cells, non-negative aggregate margin and non-negative margin on every played opponent.

Every **leaf** PASS report binds its exact authenticated `component_source_sha256`, so positive economics cannot be replayed after source changes.

The fully assembled candidate needs a separate raw `combined_composition` report. It binds both:

- the whole ordered `component_source_sha256`; and
- exact `composition_git_commit`.

So a carrier/source change or assembled-tree rejoin invalidates the combined economics until the exact new composition has evidence.

`{"status":"PENDING"}` is valid for source-ready work without completed matched economics; it blocks readiness without inventing evidence.

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

One broad carrier may satisfy adjacent semantics only by listing each slot separately with its exact source/evidence binding. Missing V231-late or collapsing row-order/row-shed remains explicit.

## What READY does not mean

Even `CURRENT_V5_COMPOSITION_READY_DEFAULT_OFF` grants **no** production default flip, release authority, archive-pointer publication, or Kaggle submission authority. The separate V3.1 champion-ratchet/release boundary still owns the final `V5 > submitted V3.1` acceptance theorem.

## Run

```bash
python -B -m unittest -v test_composition_gate.py
python -O -B -m unittest -v test_composition_gate.py
python -m py_compile composition_gate.py test_composition_gate.py
python -B composition_gate.py /path/to/manifest.json --repo /path/to/commons --output /path/to/receipt.json
```

A real manifest checkout must contain the declared carrier and composition commits; dedicated CI therefore checks out the exact PR head with full Git history. Exit status: `0` composition-ready, `3` valid-but-blocked, `2` malformed/custody failure. Receipt output is write-once.

Manifest schema: `titan-v5-r04-recovery-composition-gate/v2`. Raw economics report schema: `titan-v5-r04-paired-economics-report/v1`. The focused suite covers forged positive summaries, nonexistent carrier/composition heads, source-tree drift, raw-report tampering, duplicate cells, per-opponent regression, missing V231 and staged-runtime mismatch.
