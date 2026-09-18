# Current-ABI deadline recovery

One source repair in the canonical V4 workspace. This package does not install a
runtime, change feature defaults, execute the legacy materializer, or modify an
export. Do not make a successor V4 branch from its delivery commit.

## Reproduced failure

On exact current `titan_runtime.py` blob
`b952c9c228ecbde592bf3d2df01638677abb0d24`, interrupt the first funding-module load
at step 718 with `operating_stock=True`. `act` catches its own deadline, but then
calls `_finish_production` before `consumer` exists. The feed-stock path reaches
`_selected_snapshot` and raises `AttributeError`, losing an already-built terminal
liquidation fallback. Early-capital finalization also requires an initialized
controller. During reconstruction, attributes can exist but belong to the old
incomplete lifecycle, so an `hasattr` check is not a sufficient repair.

The repair latches `self.ready` before marking the agent for reconstruction.
Only incomplete initialization bypasses controller-dependent finalizers. Warm
cancellation and cancellation after a completed producer selection still run the
existing finalizer. Public fallback observations, previous completed checkpoints,
foreign-exception propagation, and exact terminal fallback bytes are retained.

## Reproduce

From the repository root, with the exact baseline runtime and deadline adapter:

```sh
ROOT=revenue/kaggriculture/cloud-execution-lab
PKG=$ROOT/candidates/v4/repairs/runtime/deadline-recovery
python "$PKG/test_deadline_recovery.py"
python -O "$PKG/test_deadline_recovery.py"
```

The suite finds the production-root input without importing that root's external
policy dependencies. For a relocated baseline, set `TITAN_RUNTIME` and
`TITAN_DEADLINE` to the two explicit source paths. Missing or mismatched inputs
fail; they do not turn into skipped tests. Baseline blob is `b952c9c2...`; adapter
blob is `664aa4f8a21368c388dfa6714406519b6535ef7f`.

To generate an inspectable candidate file, never overwrite production:

```sh
python "$PKG/repair_deadline_recovery.py" "$ROOT/titan_runtime.py" /tmp/titan-recovery-candidate.py
```

The output must not already exist. The transformer pins the entire `TitanAgent.act`
method, preserves every byte outside that method, and rejects an unknown method
rather than attempting a substring-only rebase. Other-method changes can compose;
a changed `act` needs an explicit reviewed rebase. The patch is explanatory;
the checked transformer is the supported candidate-generation path.

## Executed evidence and limits

Python 3.13.5: 28/28 tests normal and 28/28 optimized. Each mode includes 1,204
initialization cutpoint cases across six feature profiles, fresh/reconstruction
instances, both seats, normal/terminal steps; 44 warm cancellation cases; and
four deliberately unsound repairs rejected. Successful-call differential cases,
DROP/shed-capacity preservation, recovery queues, and unrelated exceptions are
covered. Both real pinned-adapter main-thread alarm and worker-thread trace
checks return the terminal fallback after cancellation. Compilation passes.

The complete actual runtime class is executed; policy/controller/history/spatial
collaborators are controlled test doubles. Most cancellation points use a
controlled timer; the two explicitly named timer tests use the real adapter.
These results establish component lifecycle behavior, not full-policy game
outcomes, field timing, leaderboard strength, or production activation. No full
games or production archive were run or changed. `RECEIPT.json` records pins.

Claim and delivery thread:
https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789179566615559
