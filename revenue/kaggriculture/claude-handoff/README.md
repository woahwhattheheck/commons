# TITAN: complete simulation handoff for Sanskrit Juggernaut

Sanskrit Juggernaut is the **root session coordinating Claude's existing cloud VM**,
as explicitly identified in the [active coordination thread](https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1788762339088829).
This is the common packet assembled by LARK. It carries Euler's implementation,
ASTRA-WORK's lean20 study, current peer receipts, public-opponent versions, a
working launcher and the [Claude prompt](CLAUDE_PROMPT.md).

Bryce's instruction for this work is explicit: “Give all stuff to sanskrit
juggernaut so it can prompt claude for testing and running simulations.” That
current instruction governs this handoff, including Claude execution, even where
older repository text describes a different resource route. Root supplies the
single stream of prompts to the existing VM. The agent's owner-chosen name is
**TITAN**; experiment names remain useful internally.

## Read these first

- [peer-manifest.json](peer-manifest.json): current candidate paths, receipts and
  distinctions between peer-reported, source-verified, and measured results.
- [manifest.json](manifest.json): every byte of the baseline source bundle,
  Git blob IDs, SHA-256 values, original commit and engine pin.
- [CLAUDE_PROMPT.md](CLAUDE_PROMPT.md): executable continuation order and result contract.
- [KESTREL's original complete archive](peer-packets/kestrel-handoff.zip):
  recovered unchanged after its earlier transfer rejection; all 45 listed
  file hashes verified. Extract separately and follow its existing prompt.
- [evidence/receipt.json](evidence/receipt.json): this package's actual verification,
  including the resource-test error; detailed logs and raw games sit alongside it.

## Prepare and verify

The consolidated peer map now includes ROWAN's landed dispatch package at
`515cdabbde75ae3066fe096bcce65081f33e709d`, SORREL's landed purchasing package
at `a233848288e7fe27b569bcdfef5b0c00ec50abec`, and KESTREL's exact recovered ZIP,
SHA-256 `0fc85adde06875da8ad0d1b1ac417756d09a589d3a9781abe16a79e799c8a23a`.
KESTREL's original `recipient_route_unresolved` metadata is retained as history;
the recipient is now explicitly identified. Its previously rejected branch is
still not claimed landed. This packet preserves the complete source transfer.

ROWAN's selected candidate is `cloud-dispatch/candidate.py`, SHA-256
`d87fafab8c9267d508533cd04e7ab8fa8e7c5f71414d9935ec4ddd977f0e7f74`.
SORREL provides eight generated candidates including the unchanged control.
KESTREL provides five including its control. Their untouched validation sets
and exact continuation commands are in the peer map; run their missing checks
and stronger-opponent development before extending the aggregate matrix.

Python 3.11+ on Linux. Run in ephemeral cloud storage. Preparation downloads only
30 pinned public Commons files and four upstream files (three engine inputs and
their full Apache-2.0 license). The retained Commons files include all 26 files
in the three original agent/evaluator/study folders and their four workflows.
Subsequent commands use the verified cache and preserve differing existing files.

```sh
python -B revenue/kaggriculture/claude-handoff/handoff.py prepare --bundle /tmp/titan-input
python -B revenue/kaggriculture/claude-handoff/handoff.py verify --bundle /tmp/titan-input
python -B revenue/kaggriculture/claude-handoff/handoff.py tests --bundle /tmp/titan-input --output /tmp/titan-tests
python -B revenue/kaggriculture/claude-handoff/handoff.py run --bundle /tmp/titan-input --phase calibration --output /tmp/titan-calibration
```

For an already available exact checkout and engine cache, preparation can use
`--from-checkout /absolute/checkout --engine-cache /absolute/engine` without
network access. The byte checks are identical. The `tests` command runs all 52
published tests, including real-engine tests; it does not silently skip missing
engine inputs. The additional six regressions are in `test_handoff.py`.

Calibration reproduces the **known** seed4421 losses in candidate seat1: lean20
45,485 vs Euler28 45,533, and lean20 64,471 vs compact22 65,734. It plays both
seats against both rivals, then checks one exact replay per rival. These are
calibration cases, not new independent evidence.

## Add the strong public opponents

Root already has the decoded standalone files in Claude's VM. Set `KAITO` and
`IGOR` to those actual file paths; their notebook versions and hashes are in
`peer-manifest.json`. No notebook execution is needed to extract these files.

Run each standalone candidate with its recorded hash. This example uses lean20
as the baseline control; replace both its path and hash for another candidate.

```sh
python -B revenue/kaggriculture/claude-handoff/handoff.py run \
  --bundle /tmp/titan-input --phase development \
  --candidate /tmp/titan-input/source/revenue/kaggriculture/cloud-market/main.py \
  --candidate-sha256 d9487c031b50ede06a706acc8bcb40e0b5a681d9b5e92c1a1a96492b26c2dd62 \
  --opponent "kaito43=$KAITO" \
  --opponent-sha256 kaito43=69f06a802b62aa08f28705dab5728eb924bb6a7c23ffe0164f65b104cc3dadf3 \
  --opponent "igor=$IGOR" \
  --opponent-sha256 igor=8ac34abce129cf5c9456776c90edf7d2233b3a280bbdcf7622628825ef3669a0 \
  --output /tmp/titan-development-lean20
```

This freezes the candidate and each additional opponent into the output folder
before execution. Inputs must be standalone agents exporting `agent(obs, cfg)`
or `agent(obs)`; arbitrary external dependencies are not copied or validated.
Use the packaging lane to produce a standalone first when a peer has a wrapper.
Full-game defaults are 720 recorded states / 719 action rounds. The reused
evaluator has one process per agent and a strict one-second RPC deadline; it
does not emulate Kaggle's overage-time bank.

| Phase | Seeds | Games with Kaito + Igor | Purpose |
|---|---:|---:|---|
| calibration | 1 known | 4, internal rivals only | Reproduce the published losses |
| smoke | 1 separate | 10 | Interface / extra-opponent integration |
| development | 6 separate | 60 per candidate | Compare and select exact candidate bytes |
| validation | 12 separate | 144 for the selected candidate | Check the frozen choice; adds incumbent36 |

Each opponent also has one replay, separately recorded and excluded from game
counts. All newly declared development/validation seeds are unrun by this lane.
Existing peer study protocols stay intact. This shared matrix is available for
cross-lane or composed finalists; it is not an order to duplicate every completed
study. Include Kaito and Igor in selection, not just after picking an internal winner.

For the selected candidate repeat the command with `--phase validation`, a new
output directory, and `--development-report /tmp/selected-development/report.json`.
Use the same extra-opponent arguments. The launcher checks the candidate hash,
complete development result, source manifest and identical development opponent
roster before running the reserved set. Record the selection rationale first.
If validation causes further edits, those results become development evidence;
declare another untouched validation set before claiming confirmation.

## Run with the intended resource envelope

Preparation is networked; simulations can run in the existing Linux VM or in a
container with networking disabled. Pull the Python image during preparation,
record its digest in `KAG_RUNTIME_IMAGE`, then mount the checkout and bundle read
only, with a separate writable output directory. A calibration example:

```sh
mkdir -p /tmp/titan-results
docker pull python:3.11-slim
KAG_RUNTIME_IMAGE=$(docker image inspect python:3.11-slim --format '{{.Id}}')
docker run --rm --network none --cpus 1.6 --memory 6656m \
  -e KAG_RUNTIME_IMAGE="$KAG_RUNTIME_IMAGE" -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD:/repo:ro" -v /tmp/titan-input:/bundle:ro \
  -v /tmp/titan-results:/results:rw -w /repo \
  python:3.11-slim python -B revenue/kaggriculture/claude-handoff/handoff.py run \
  --bundle /bundle --phase calibration --output /results/calibration
```

The container command is provided for Claude; this Work runtime did not execute
Docker or impose Kaggle's CPU/memory envelope. Our local timing/RSS observations
are not hosted resource certification. The published test that reads
`/proc/<child-pid>/status` errors here; its exact log is included. Rerun it in the
normal Linux VM before making an all-tests-pass or complete resource claim.

## Interpret and return results

Local verification: six handoff tests pass; eight final-code smoke games and
four replays complete, including an additional opponent whose scores and
hashes match the built-in Euler28 control exactly. Four earlier calibration
games and two replays reproduce the published losses. These repeated/control
games do not establish a new improved policy. All shared development/validation
games remain for Sanskrit Juggernaut to run through Claude.

`contract.json` and the fsynced append-only `games.jsonl` make runs resumable.
Reuse an output directory only with the identical contract; changed source,
candidate, runtime or roster gets a separate directory. `report.json` contains
every result and failure, source hashes, per-seed/per-seat scores, daily bank
traces, timing/RSS fields and replay hashes. Failed games never count as wins.
Both seats form one seed cluster for descriptive bootstrap intervals.

Root's newly reported strong-opponent losses substantially change the benchmark:
lean20 is an internal control, not evidence of competitiveness against public
agents. Ask what produces realized terminal cash. Compare dispatch, recurring
crops, feed self-supply and procurement singly before composing them. Preserve
losses, unsold inventory and rejected variants. Return exact source refs,
commands, all game rows, independent seed count, failures and resource limits to
the same working thread; root integrates the experiment results and owns any
replacement of the existing successful Kaggle v2 entry.

Owner-authored handoff: MIT OR CC-BY-4.0. Full grants and attribution are included.
Upstream engine files remain Apache-2.0; public opponents retain their own notices.

## Continuation: real exports and official file loading

The original PR9766 packet stays complete. LARK's next increment is
[`../cloud-pack/`](../cloud-pack/README.md), with two real submission archives,
an export builder for the selected integration, explicit assets/licenses,
source-to-extracted-agent comparisons, first-action initialization timing and
the prepared constrained-container command. Its
[Claude prompt](../cloud-pack/CLAUDE_PROMPT.md) is the next packaging handoff.
Nine new regressions and eight full packaging games pass; Docker/container and
hosted execution remain with Sanskrit → Claude. Exact code/archive hashes and
raw reports are in that packet's evidence directory.

The updated peer manifest also carries FLORA's landed public-opponent package
at `cf7ee70da605f19a974905854249baab72c1d017`: 20 completed games, lean20 lost
all 20 against Kaito v43 and Igor MultiRoute. Those used validation seeds are
not untouched holdouts. Sanskrit owns the existing Claude VM, and FLORA now
owns the distinct `cloud-composition/` lane.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
