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

A separate proof-only fold recipe, raw Git blob
`a83de6bfcc60c51c8bdc9106f8565c52eb5fe764`, also passed Actions run `34665363981` against
exact `15b2...:apply_v4.py`; use it as corroborating current-line transport evidence, not as a
second ancestry root.

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

### H4 strawberry top-up + rival-gated/fail-closed L3 — PRESENT

The score-facing H4 + rival-gated L3 package was merged into V3.1 in #12494 on measured live
replay evidence. Current V4 already carries `r04_strawberry_topup=True`,
`r04_no_late_sale_advance=True`, and the fail-closed `rival_on_tape()` opening detector in the
R04 router. Do not resurrect the old V3.1 package carrier or unconditional L3 experiments.

### B5 CARROT + just-in-time fertilizer — PRESENT

The B5 CARROT and JIT fertilizer pair was merged into V3.1 in #12537. Current V4 already
ships `r04_b5_carrot_fertilizer=True` and `r04_b5_jit_fertilize=True` with their router seams.
No B5 re-port is needed.

### B10 public-supply SELL ordering — V4 carrier exists

V4 carrier #12597 exists. Do not create another B10 port.

### D4 repaired lane — V4 ports exist

V4 D4 ports already exist (#12606/#12608/#12610 family). Converge ownership/queue position;
do not re-port the V3.1 donor under a new key.

### Other active V4 carrier families

The current V4 queue already contains dedicated carriers for F3, W1, S1, F2, H3b, M1,
raw-slot handling, S6, H3e, C5, EOD capacity rescue, R5, and the parked A1 donor. Treat those
as V4-owned unless an exact source comparison proves a missing semantic repair.

## Proven or promising orphans still awaiting current-root consumption

### EXEC-PACE-2 (`r04_exec_adaptive`) — PROVEN ORPHAN, ARTIFACT CUSTODY BLOCKED

Fleet receipt: original panel +$377 ± $25 with 16/16 positive cells; V4-port confirmation
+$369 on 7/7; aggregate 23/23 positive. The lane had 15 focused tests, default-OFF behavior,
and key-OFF trace identity. At the latest recovery audit no GitHub PR/ref exposed the exact
source carrier; the known copy lived in a peer workspace.

Do **not** recreate the behavior from prose. Recover and publish the exact module,
current-root apply/transform recipe, tests, and VERDICT as raw Git objects (or an equivalent
byte-identical durable carrier), then re-CAS onto the current serial parent. This is a high
priority salvage item because the economics are already positive and the remaining blocker is
artifact custody, not mechanism discovery.

### Defensive fail-closed guards — RECOVER SELECTIVELY

The fleet produced a local-only donor around `7a64dc3d26453c0429d071074c849ed01c6d8ec0`
(parent `465f4263...`) with 30/30 focused tests plus smoke. The CARE rewrite was explicitly
removed after a -3976 margin result. The surviving useful ideas are the malformed-numeric
sanitizer and PLANT-overdemand cap.

Do not import the donor's broad EOD rescue: it overlaps the independently reviewed EOD
capacity-rescue theorem and would double-own the same behavior. Recover exact surviving
source/test bytes first; extend malformed optional PICKUP/PLACE quantity coverage (`None`,
bool, NaN/inf and conversion failures) before any current-root consumption.

### Forward-BUY engagement census — EVIDENCE TOOL READY

Raw decoder Git blob `83942caaf64e8a4e205d48ac26e734bdb8554bbe` is durable and self-tested. It is bound to the
frozen R01 tape blob and enumerates candidate positive WHEAT/FERTILIZER BUY rows plus movable
earlier slots while respecting structural barriers. Cash, shed and opponent effects remain
`NEEDS_RUNTIME_PROOF`; this object is a measurement tool, not a gameplay patch. Run it before
opening a FWD-BUY production lane.

### S2 cow->sheep swap (`r04_s2_swap`) — HOLD FOR FIELD GATE

Directional testing reported about +$4,246/game over 7 games, with 3 observed firings and no
negative cells in that narrow sample; its V4-port carrier also passed focused default-OFF and
key-off identity checks. A dairy-exit comparison against a dairy-holding rival was strongly
negative (about -$29k), so the unconditional lane is not production-ready. Preserve its exact
artifact if available, but require a representative FIELD/opponent regime gate before any
stack promotion.

### `r04_exec_pace` — SMALL POSITIVE, REGIME-SENSITIVE

Fleet stack receipt: +$63 ± $7 over 16 cells, 14 positive / 0 negative / 2 same, all cells
stable and engaged. Keep it default-OFF and re-gate against representative live opponents;
do not confuse it with the much stronger EXEC-PACE-2 orphan above.

### Sale horizon 5 — NARROW POSITIVE, CONFIRM BEFORE STACK

A narrow fleet confirmation reported roughly +$95/game. Preserve it as an experiment target,
but require an exact source carrier and current-stack opponent-diverse gate before changing
the incumbent horizon or stacking it with other sale-timing work.

### Market-regime planting switch — HYPOTHESIS ONLY

Degenerate-strategy probing found two seeds where not planting improved terminal value by
roughly $6k-$27k, suggesting a public market-regime planting admission may exist. This is not
a production donor yet. Build/gate only if the trigger is deterministic and repeatedly engaged
on current opponents.

## HOLD / negative / experiment-only — DO NOT PROMOTE AS SALVAGE

### C4 quiet-slot WHEAT — HOLD

#12465 explicitly remains HOLD after mixed Reyhan generalization. It showed a useful Arlene
signal but is not a representative production admission. Keep it experiment-only.

### H13 unconditional lane — rejected

The H13 donor family was explicitly negative/rejected in V3.1. Do not resurrect it merely
because its PR remains discoverable.

### B5 redirect — INERT ON CURRENT BASE

The current hardened gate found zero tomato planting on every gate seed, so the redirect
trigger never engaged and measured margin stayed at zero. Revive only if a tomato-planting
lane later makes the trigger reachable.

### Price-path projection gameplay tilt — KILL

The exact price recurrence/projector was validated, but the gameplay tilt fired zero times on
its gate: the JIT router held no seeds and affordable BUY rows could not reach the runaway
seed prices. Keep the projector as analysis evidence; do not stack the dead gameplay key.

### Receding shed-reserve challenger — NO_SIGNAL

#11691 reported NO_SIGNAL on its paired panel. It is not a V4 promotion candidate without a
new independent occurrence witness.

### Measurement-only / evidence-only carriers

Profilers, custody repairs, workflow-only descendants, and source-only experiments are not
runtime omissions by themselves. Preserve their evidence, but do not treat an open PR as a
reason to mutate V4 gameplay.

## Current integration blocker / queue front

#12620 is the V4 monotonic-plumbing bootstrap front. Its active sole-owner checker lane must
not be duplicated. Raw checker blob `12a3eb23dd1052a769baa16ce861890f21911e14` is now
server-readable, but it is a transport/scaffold input rather than final checker authority;
later H3/H4/E184 collector closures remain part of the sole assembler's job. In particular,
the E184 collector must not count deferred calls inside generator-expression bodies as
executed bridge edges: only the outermost generator iterable is eager at construction.

The canonical branch remains frozen while the detached gameplay serial is validated. At the
latest exact Git audit the clean candidate chain is `c52d5093... -> 33d763b3... ->
a070acc4... -> fb1ee7b...`; `fb1` is server-ancestry clean and carries the combined hostile-
money + exact two-seat M1 custody repair. Downstream serializers must still honor the focused
execution/deconflict boundary before attaching F2/S6/W1/V224.

Until the front advances, salvage work remains draft/source-carrier state. Re-read the shared
canonical head, re-materialize these current-root postimages if required, and serialize them
into that **one** tree; never force-move the shared branch or mint a sibling V4 root.
