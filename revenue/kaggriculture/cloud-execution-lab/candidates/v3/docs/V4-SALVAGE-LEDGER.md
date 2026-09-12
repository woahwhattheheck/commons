# TITAN V4 — V3/V3.1 salvage ledger

This ledger is a de-duplication and carry-forward map for the **single** canonical V4 line, `titan/v4-20260911`.

Publication baseline for this pass: `465f4263da1c98acf78889d67cdd21b61dbba145`.

Rules for this ledger:

- do not mint a sibling V4 root;
- do not duplicate an existing V4 carrier merely because the V3/V3.1 donor PR stayed open;
- carry correctness/mechanics repairs only after checking the current V4 source, not by copying a stale whole-file postimage;
- keep experiment/HOLD/negative lanes out of production until their own evidence boundary advances;
- serialize source carriers behind the active V4 plumbing front (#12620).

## Carried in this salvage branch

### E20 executable market-prefix parity — CARRY

Current V4 inherited `overlay/e20_hire_guard.py` blob
`341eed454cae08cfeba31b5205a10263e50999d8`, which still scanned the complete
authored market vector for `HIRE` rows. The engine executes only
`market[:max(1, maxMarketOrdersPerTurn)]`.

The reviewed V3.1 repair blob
`cd497140d188794d610d3ae387de8758ecbd0765` is now carried on this branch.
It keeps the existing E20 key/default semantics and changes only HIRE-index discovery to
the executable raw prefix. Focused V4 regression coverage freezes suffix-HIRE identity,
the official cap-0 -> cap-1 clamp, active-prefix-only limiting, and key-OFF exact identity.

Initial local receipt on the published bytes: `py_compile` PASS; 4/4 focused tests PASS.
The same carrier now also contains KESTREL-V4's test-only successor with a 9,604-case
raw-slot/cap/budget differential matrix plus demand, terminal, idempotence, malformed-market,
nonmutation, and disabled-path contracts. Production E20 bytes remain unchanged by that
successor.

### R04 fast tape-action clone — CURRENT-ROOT SOURCE-READY

V3.1 proof carrier #12431 retains `production.patch` blob
`84346b65edacbfb2e46580adace4ec407707ed5e`. The mechanism shallow-clones only the exact
JSON tape-action schema and fails closed to `copy.deepcopy` for any future schema.

The reviewed proof covered all 9,347 tape actions, alias safety/future-schema fallbacks, and a
>=1.50x median speed gate. Current V4 still contains `action = copy.deepcopy(tape[step])` and
has no `_r04_clone_tape_action` helper, so the optimization was not inherited.

This salvage branch now carries `docs/v4_salvage_fast_clone.py`, pinned to current V4 router
blob `a3e2fe87c717d128e43c9b65bae2265f40d1d76d`. It accepts exactly the two reviewed semantic
hunks (helper insertion + one `Policy.act` callsite replacement), compiles the generated
postimage, and rejects any source drift. `overlay/checks/test_v4_fast_clone_salvage.py` binds
the same postimage to all 13 x 719 = 9,347 frozen tape actions, checks per-row alias separation,
and exercises future-schema fail-closed fallback.

Do not paste the frozen V3.1 router postimage over V4: current R04 has later gameplay layers.
Consume the generated modern postimage only after the serial queue front advances.

### SELL scheduler executable-prefix family — CURRENT-ROOT SOURCE-READY

The V3 source/evidence carriers #12005 and #12018 identified the same interpreter boundary in
two scheduler projections:

- `SellScheduler.cash_reserve()` must not charge engine-inert market suffix rows;
- `SellScheduler.receipt_profile()` must not replay suffix SELL/BUY/HIRE rows that the engine
  never executes.

Current V4 `cloud-execution-lab/scheduler.py` blob
`da1b6fb571e79ba7dab54c8d816e45afb934e4d2` still iterates unsliced current/future market
queues in both paths. The official engine remains exact blob
`3c202c7ee921da239356789e266b694635103fc4`, so the interpreter boundary itself has not drifted.

The old #12018 materializer was bound to stale scheduler blob
`a483b24dd72b580d7d8811636b54d2d44f391575`; its whole-file postimage is not merge authority.
This branch instead carries `docs/v4_salvage_scheduler_prefix.py`, pinned to the current V4
scheduler + official engine. It inserts one shared `_engine_market_prefix()` helper and rewires
only the current cash-reserve loop, receipt-profile current-market prepass, and receipt-profile
market loop. `overlay/checks/test_v4_scheduler_prefix_salvage.py` binds those exact three
consumers, verifies the official engine source anchors, exercises 1,512 raw-queue/cap cases,
and fails closed on scheduler or engine drift.

#12026 (inherited purchase prefix stability) is a related stronger safety theorem and should
be reconciled when the generated scheduler postimage is consumed rather than independently
layered after it. #12036 remains an experiment around physical partial fills; do not silently
promote it.

## Already consumed by current V4 — DO NOT DUPLICATE

### Strict row-shed (S33/S34) — PRESENT

The strong V3.1 donor was #12551, with the strict production theorem recorded in #12566.
Current V4 `overlay/r04_full_router.py` already contains `r04_row_shed`, preserves raw falsey
market slots as barriers, limits movement to the contiguous leading SELL block, and documents
the coherent whole-block fallback to requested-quantity scoring when projected shed evidence
is missing or type-poisoned. This is not an orphan.

### B10 public-supply SELL ordering — V4 carrier exists

V4 carrier #12597 exists. Do not create another B10 port.

### D4 repaired lane — V4 ports exist

V4 D4 ports already exist (#12606/#12608/#12610 family). Converge ownership/queue position;
do not re-port the V3.1 donor under a new key.

### Other active V4 carrier families

The current V4 queue already contains dedicated carriers for F3, W1, S1, F2, H3b, M1,
raw-slot handling, S6, H3e, C5, EOD capacity rescue, R5, and the parked A1 donor. Treat those
as V4-owned unless an exact source comparison proves a missing semantic repair.

## HOLD / negative / experiment-only — DO NOT PROMOTE AS SALVAGE

### C4 quiet-slot WHEAT — HOLD

#12465 explicitly remains HOLD after mixed Reyhan generalization. It showed a useful Arlene
signal but is not a representative production admission. Keep it experiment-only.

### H13 unconditional lane — rejected

The H13 donor family was explicitly negative/rejected in V3.1. Do not resurrect it merely
because its PR remains discoverable.

### Receding shed-reserve challenger — NO_SIGNAL

#11691 reported NO_SIGNAL on its paired panel. It is not a V4 promotion candidate without a
new independent occurrence witness.

### Measurement-only / evidence-only carriers

Profilers, custody repairs, workflow-only descendants, and source-only experiments are not
runtime omissions by themselves. Preserve their evidence, but do not treat an open PR as a
reason to mutate V4 gameplay.

## Current integration blocker / queue front

#12620 is the V4 monotonic-plumbing bootstrap front. Its active sole-owner checker lane must
not be duplicated. The canonical branch is currently unprotected, so candidate-owned green CI
is not itself merge authority; #12620's current plan uses an independent exact Git-object audit
for bootstrap and keeps a trusted control-plane gate as a separate follow-up.

Until the front advances, salvage work remains draft/source-carrier state. Re-read the shared
canonical head, re-materialize these current-root postimages if required, and serialize them
into that **one** tree; never force-move the shared branch or mint a sibling V4 root.
