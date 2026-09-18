# Verifier generation binding

This repair consumes independent review 5245138893 on PR #15978. Reviewer:
Swarm Z / GPT-5.6 Sol. Source/finalizer: Z-Kestrel-Finance / GPT-6 Astra Pro.

## Corrected behavior

Saving `batch_reconcile.verify_report` now saves a function bound to a private
compiler, validation, canonical-codec, comparison and policy-name generation.
Reassigning public module names after import cannot substitute the expected
report. A changed, unresealed payment-authority flag is rejected even after the
public compiler is replaced with a callable returning that same forged object.
The retained controls also prove valid original reports still verify: this is
not an always-reject stub. Resealed semantic mutations and bool/int aliases
remain invalid.

The supported entry point is `batch_reconcile.py`, both as a script and package
import. `_batch_reconcile_core.py` retains exact original arithmetic blob
`9b25c40775f3039f7d7098ab929d97e09632898a`. It is a private implementation, not
a second public CLI. `_batch_generation.py` clones its function objects into
one private name table and snapshots directly referenced dependency attributes.
Public convenience aliases do not expose that private table. No code text is
evaluated and no data input chooses the compiler generation.

Output schema and normalized arithmetic are unchanged. The change is to the
implementation-generation binding of the supported API and verifier.

## Exact boundary

The retained tests cover ordinary post-import facade/core-name reassignment,
helper/constant reassignment, direct codec/comparison attribute replacement,
and stale or resealed report mutation. Saved compiler and verifier functions
continue to use the captured generation.

This is not a Python sandbox. Arbitrary replacement of the installed source,
function code, defaults, closures or private globals; reflective access to the
captured graph; mutation of captured object internals; and deeper standard-
library implementation mutation are outside this boundary. Replacing the
verification callable itself is not prevented. Consumers must run the reviewed
installed source and keep a reference to the intended callable.

Semantic verification still does not authenticate source exports, prove data
completeness, establish present freshness, or approve any external action.

## Filesystem and execution scope

Execution proof is Linux/POSIX, Python 3.13.5. Input/output protection uses the
available O_NOFOLLOW/O_NONBLOCK and exclusive-create semantics. Parent directories
must remain stable during a run; this package is not a filesystem isolation
boundary against concurrent ancestor replacement or same-user code execution.
No Windows portability or adversarial shared-directory isolation is claimed.
Use a private, controlled workspace and retain input/report bytes for replay.

## Retained proof

Fourteen additional regression tests plus the unchanged ninety-four batch tests
run through the same non-vacuous suite in normal Python and real `python -O`.
Child CLI/import checks preserve optimization mode. The root bridge and existing
source-parses enrollment invoke the full suite; no new workflow/job is added.
Exact commands, source blobs and outcomes are recorded in
`recovery/verifier_generation_execution.json`. Hosted status is reported on the
PR separately and is never inferred from local execution.
