# H4 production-wiring prep

Status: **non-mutating wiring preview only**. This directory does not change shipped V3.1,
`overlay/**`, `apply_v3.py`, TITAN-CONFIG/defaults, package receipts, evaluator/opponent state,
or Kaggle/submission state.

## Why this exists

The reviewed H4 strawberry top-up is now converged on the current V3.1 spine (#12447), but it
still lives under `experiments/**` and therefore is not part of the packaged runtime. The next
score-facing step needs an auditable production wiring change without invalidating the exact-head
package/reachability gates currently running on the convergence root.

`preview.py` makes that future mutation deterministic without performing it:

1. pin the frozen R04 source blob (`21c4f1db...`) and reviewed H4 donor blob (`ecad11eb...`);
2. require exact, single `apply_v3.py` anchors for the R04 defaults/feature/install/diagnostic seam;
3. materialize a prospective `apply_v3.py` in a caller-supplied **out-of-repo** directory;
4. copy the reviewed H4 module byte-for-byte to prospective `overlay/r04_h4_strawberry.py`;
5. add one deterministic feature dial, `r04_strawberry_topup`, default **False**;
6. route packaged R04 through the reviewed H4 wrapper, passing that flag after the existing six
   R04 knobs; and
7. compile the prospective `apply_v3.py` and emit Git-blob receipts.

The reviewed wrapper preserves the live ordering
`POLICY_AGENT -> H4 -> ROW_ORDER -> EVENING_FLUSH -> OPEN_ROUNDTRIP`; with the H4 flag false,
the H4 transform itself is disabled.

## Important boundary

This is **not** the production patch and does not authorize one. A real wiring child must still:

- start from the current reviewed convergence head;
- copy the reviewed H4 donor byte-for-byte (or explain/review any delta);
- apply the exact feature wiring previewed here;
- regenerate/rebind deterministic package manifests/receipts because adding an overlay file
  changes packaged bytes even when the feature default is false;
- run package-integrity, materialized reachability, the H4 focused/source gates, and disabled-mode
  equivalence predecessors on that exact head;
- keep the feature default false until the integration owner explicitly promotes it after the
  required opponent-diverse economics/externality screen.

The preview refuses any output path inside the repository so running its tests cannot silently
turn wiring prep into a package mutation.
