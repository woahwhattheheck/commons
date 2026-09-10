# TITAN V3 official-transition oracle successor

## Disposition

This directory is an additive evidence carrier. It changes no policy source,
candidate, evaluator, game panel, seed bank, canonical runtime/configuration,
archive, package pointer, provider state, Kaggle state, or submission.

Coordination claim:
`TITAN-V3-OFFICIAL-TRANSITION-ORACLE-SUCCESSOR-20260910-01`  
Slack claim TS: `1789072732.418589`

The carrier answers a narrower but cross-cutting question:

> Given one exact two-player prestate and two authored actions, what transition
> does the pinned official interpreter actually commit, in what order, and with
> what poststate?

It is a successor—not a replacement—to closed/unmerged PR #11700. That earlier
compact shadow oracle retains provenance for its seven minimized sentries and
hosted artifact. This carrier executes the real interpreter and binds every
receipt to its exact source bytes.

## Exact boundary

- publication base: `ed65812449a2cd021b0635a60ff9171957f3e386`
- claim-observation base: `c51049d671b55d282e0fed5df37a0be7c513a838`
  (only generated board/manual ownership files advanced; the pinned interpreter
  blob remained unchanged)
- pinned interpreter path:
  `revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py`
- pinned interpreter Git blob:
  `3c202c7ee921da239356789e266b694635103fc4`
- prior compact oracle: PR #11700, head
  `253cf3ce62faed47461e517ca56c721a2da60e87`
- prior hosted run/artifact: `34403550090` / `10124440153`
- prior evidence SHA-256:
  `87b51c0aafa70cdac352d52eae5daba40c9a9eb2ed9cabfea0eb553cab1177ea`

The launcher authenticates the interpreter Git blob before process creation.
The worker independently authenticates the same bytes, authenticates its own
SHA-256, imports the interpreter under `python -I -B`, hashes both files again
after execution, and emits exactly one newline-terminated strict-JSON receipt.

## What is executed

The worker constructs two farms, two private states, one shared market, and one
shared town using the pinned interpreter's own constructors. A fixture may
sparsely patch those objects, then provide 1–64 contiguous two-player actions.
For each step the worker invokes the official `interpreter()` once and records:

- the canonical prestate and poststate hashes;
- the exact authored-action hash;
- each player's active raw market prefix;
- atomic same-crop PLANT validation and every unit action;
- market entry/exit;
- player-order HIRE and BUY_LAND attempts;
- every per-unit market commit, price, success bit, and local delta;
- town-consumption inventory deltas;
- plant-decay and end-of-day boundaries; and
- terminal canonical state plus a transition hash.

Instrumentation delegates to the original functions. It does not replace price,
fill, capacity, town, actor, decay, or end-of-day semantics.

## Sterile protocol

`official_transition_oracle.py` and `official_transition_worker.py` fail closed
on:

- engine source/path drift, worker drift, symlinks, hard links, or non-regular files;
- duplicate JSON keys or non-finite numbers;
- unknown fixture surfaces, noncontiguous steps, oversized input/output, or
  malformed two-player action rows;
- timeout, nonzero exit, stderr, extra stdout lines, invalid UTF-8, or a
  malformed/tampered receipt; and
- source mutation during the transition.

Outputs are canonical JSON with self-verifying SHA-256 envelopes. The retained
corpus artifacts are created under a fresh directory and accompanied by an
exact `SHA256SUMS` manifest.

## Predecessor-killing corpus

The 24 exact fixtures include four metamorphic pairs and these witnesses:

1. **Atomic PLANT** — farmer and hand request WHEAT with one seed; both requests
   become PASS and the seed/two tiles remain unchanged.
2. **Two-player precommit quote** — simultaneous one-unit WHEAT sales both
   receive `$25`; ending inventory is `10002`.
3. **Arbitrary inactive suffix** — multi-turn traces with identical active raw
   prefixes but different target SELL/HIRE/BUY/malformed suffixes produce
   identical poststates at every step.
4. **Minimum-one cap** — `maxMarketOrdersPerTurn=0` still executes exactly one
   raw row and ignores later rows.
5. **Unaffordable in-prefix HIRE** — `$99` against cost `$100` creates no actor,
   inventory slot, or cash mutation.
6. **Represented-horizon current/future suffixes** — inert BUY/SELL suffixes
   followed by PICKUP/DROP remain exact-state metamorphisms, killing false
   represented-state events.
7. **Town-consumption funding** — eight bakeries plus the town center move a
   future WHEAT quote to `$32`; `$31` alone fails, while a current MILK sale
   funds the exact future purchase.
8. **Hidden rival receipt** — a rival's ten WOOL units move the later own quotes
   to `$194` and `$193`; exact receipt is `$387`, so a future `$400` COW does not
   fill.
9. **Own-prefix pressure counterexample** — parent order produces own/rival cash
   `1828/2075`; moving MILK before the contested final WHEAT unit produces
   `1827/2076`. The reorder loses one own dollar and gifts one rival dollar.
10. **Hidden-affordability discontinuity** — in both candidate seats, FERT
    sale receipts are `$97,$96,$96`. `SELL FERT3; BUY COW1` ends at `$31` with
    the COW, while `SELL FERT2; BUY COW1` ends at `$335` without it. The third
    positive `$96` sale crosses the fixed `$400` debit and causes a net `-$304`
    terminal-cash discontinuity. Sale-only controls end at `$431` and `$335`.

The corpus establishes transition facts. It does not prove any candidate is
stronger, safe to merge, or ready to promote.

## Run

From the repository root:

```bash
case_dir=revenue/kaggriculture/cloud-execution-lab/analysis/v3-official-transition-oracle-20260910-sol-pro
engine=revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py

PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
python -m unittest discover -s "$case_dir" -p "test_official_transition_oracle.py" -v

PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
python "$case_dir/run_official_transition_corpus.py" \
  --engine "$engine" \
  --worker "$case_dir/official_transition_worker.py" \
  --output-dir /tmp/titan-official-transition-evidence
```

The workflow runs the complete corpus twice from the immutable PR head, compares
every retained byte, records source identities, proves the checkout stayed
clean, and uploads the evidence directory.

## Consumption contract

Certificate owners should bind their claim to one retained fixture/envelope or
add a new exact fixture. A valid composition proof starts from the same prestate
and rival action, preserves inactive suffix bytes/indexes, executes both literal
raw prefixes row-by-row, and derives funding, fills, receipts, actors, physical
state, town timing, scheduler settlement, and final policy comparison only from
the retained official poststate.

A local shadow may explain a transition. It may not replace this oracle as the
truth boundary for one-tree integration.
