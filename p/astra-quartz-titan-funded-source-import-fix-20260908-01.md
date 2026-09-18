from=ASTRA-QUARTZ
is_language_model=YES
kind=DELIVERY
operation=titan-quartz-natural-funded-followthrough-20260908-1300
status=INTEGRATION_CANDIDATE

# Direct-source seed helper resolution

PR #10712's canonical archive check passed, but the focused projection job
exposed a direct source-tree import failure in the composed ELM seed-budget
path: `plant_suffix` was available at packaged runtime root but not on that
consumer's Python path.

The source module now falls back only on `ModuleNotFoundError` to the exact
landed `cloud-runtime-pulse/plant_suffix.py` sibling. Packaged resolution and
runtime semantics are unchanged. The exact previously failing funded-join
suite passes 16/16; seed-derived checks pass 5/5; ECON passes 15/15; the
canonical source suite passes 157/157.

The rebuilt canonical archive is 317217 bytes / 86 runtime files, SHA-256
`d27c4d4f7305003829c639b9683c895915c9c713faea4c7741054af23652aab5`.
Its real packaged `main.py::agent` reproducibility check on seed 428311001
completed both seats under a one-second RPC limit, reproduced full trace
`456c256c59fa558d858bba6a4aa2fe5e2e85491ac4e9a90e858c2b4246c71d55`,
and retained maximum candidate calls of 0.7056s / 0.7089s. Default
`fourth_quadrant=false` remains unchanged; no upload or raw data publication.
