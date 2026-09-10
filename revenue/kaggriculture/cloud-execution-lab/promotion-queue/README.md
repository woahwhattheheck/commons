# Promotion queue service

Turns the manual Titan V3 promotion ritual—submit a candidate, pin every
identity-bearing input, run the paired gate against frozen control and LAND,
and seal the result—into a CLI-driven service.

The queue is **orchestration and receipt only**. The gate itself remains the
existing `../titan-v3-paired-game-gate/` implementation (`gate.py` and
`dual_predecessor_gate.py`). This service never reimplements gate logic.

## Pipeline

```text
submit  -> SHA-256 pin candidate + panel + policy + config + engine + runner
run     -> verify the submitted closure, then paired gate vs every predecessor
receipt -> sealed JSON carrying the complete queue pin and gate outcomes
```

## Submission identity

A queue submission is identified by the bytes of all six inputs below:

1. candidate artifact;
2. candidate games panel;
3. gate policy;
4. predecessor config;
5. engine identity manifest;
6. runner identity manifest.

The deterministic `input_digest` and queue dedupe key cover all six SHA-256
digests. Consequently, the same candidate bytes under a different engine,
runner, declared commit, or predecessor config form a different submission.

`run` must receive the exact predecessor-config bytes supplied to `submit`.
Before either gate is invoked, the queue:

- verifies the stored pin manifest and every content-addressed blob;
- compares the supplied config SHA-256 with the submitted config SHA-256;
- compares parsed config semantics with the pinned config;
- re-hashes the live engine and runner identity paths to detect replacement;
- replaces those paths with the already pinned content-addressed blobs.

Legacy three-input queue pins fail closed and must be resubmitted. A receipt
therefore cannot certify a candidate under executable bytes that were absent
from its submission ID.

## CLI

```bash
# Pin the complete submission closure and enqueue it.
python3 promote.py --state-dir <dir> submit \
  --name v3-p07-joint-actors \
  --artifact joint_actors.py \
  --games matched_p07.GAMES.jsonl \
  --policy policy.json \
  --predecessors predecessors.json

# Run one pending submission or the full FIFO. The config must byte-match the
# config used above.
python3 promote.py --state-dir <dir> run \
  --all \
  --predecessors predecessors.json

# Optional HMAC-SHA256 attribution for the sealed receipt.
python3 promote.py --state-dir <dir> run \
  --id <submission-id> \
  --predecessors predecessors.json \
  --signing-key <keyfile>

# Queue and receipt inspection.
python3 promote.py --state-dir <dir> list [--status pending|running|passed|failed]
python3 promote.py --state-dir <dir> status <submission-id>
python3 promote.py --state-dir <dir> rerun <submission-id>
python3 promote.py --state-dir <dir> receipt <submission-id> [--verify]
python3 promote.py pin <file>
```

## Predecessor config

`predecessors.json` declares comparison slots and the engine/runner identities.
See `predecessors.example.json`. Each slot needs a games panel and artifact
file. Engine and runner entries need a declared commit plus an identity file.

`engine_sha256` and `runner_sha256` are the digests of the pinned identity
manifests. Their `commit` fields carry the declared upstream identities. For a
content-addressed runner manifest, the manifest's own SHA-1 may be used as the
commit value; that convention is recorded verbatim and does not imply an
external repository assertion.

Predecessor slot artifacts and games are pinned by each attempt and bound into
the gate contract and receipt. The candidate-facing submission identity is
closed earlier, at enqueue time, by the six-input contract above.

## Gate strategy

- `paired`: one `gate.py` run per slot against the same pinned candidate. Every
  slot must promote.
- `dual`: one atomic `dual_predecessor_gate.py` comparison for two genuinely
  distinct predecessor artifacts. The queue emits the strict custody receipts
  required by that gate.
- `auto` (default): selects `dual` for two distinct predecessor artifacts and
  otherwise uses `paired`. Byte-identical predecessor roles are not fabricated
  into a distinction.

## Receipts

See [RECEIPT-CONTRACT.md](RECEIPT-CONTRACT.md). Every receipt carries the
complete queue pin, including `predecessor_config`, `engine_identity`, and
`runner_identity`; per-slot gate evidence; the exact config SHA-256; timings;
and a canonical integrity digest. Repeated attempts form a hash chain.

With `--signing-key`, the queue also applies HMAC-SHA256. Keys are supplied by
the operator and never enter receipts, logs, or queue state.

A `PROMOTE` verdict means only that the pinned candidate satisfied the pinned
policy against the pinned predecessor evidence under the bound gates. It is
not a Kaggle submission, leaderboard claim, or release authorization.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python3 -B -m unittest discover -s tests -v
```

- `test_pinning`: deterministic content-addressed pins and tamper detection.
- `test_store`: FIFO, dedupe, status transitions, and rerun history.
- `test_receipts`: canonical sealing, verification, and receipt chaining.
- `test_signing`: HMAC verification, config pinning, and grid enforcement.
- `test_executable_pins`: engine/runner/config substitution predecessor killers.
- `test_e2e_mocked`: full six-input CLI flow against contract-shaped mock gates.
- `test_dual_wiring`: queue dual strategy through the real dual gate.

## State layout

```text
<state-dir>/queue/queue.json      queue entries and attempt history
<state-dir>/pin-store/blobs/      content-addressed bytes
<state-dir>/pin-store/pins/       immutable submission manifests
<state-dir>/receipts/             sealed promotion receipts
<state-dir>/attempts/<submission> retained per-attempt gate bundles and reports
```

State is runtime data, not source; keep it out of git.
