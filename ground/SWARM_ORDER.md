# Commons swarm order — owner directive, 2026-09-12

Bryce directs GPT-led integration, quick GPT review of Claude, Muse and Grok
work, continued throughput when GPT tokens are scarce, and actual use of the
existing command center. GPTs remain the principal builders as well as leads;
they are not a dedicated review department. This standing directive supersedes
older "no review gates", "merge without review" and "roles never authority"
language **for work integration and release**. It does not change shared tool
access, credentials, or public read access. A channel post cannot retire it.

## One operation, one working queue

Use `command.html` and `integrations/command_center/`, not a replacement board.
Open PRs are the code queue. `state/coordination` is a derived snapshot;
`state/claims` is the existing atomic claim ledger. PRs, exact artifacts and
provider receipts remain authoritative. Stale snapshots never authorize a merge.

Every active seat, including GPT, starts a work unit by reading the command
center and claiming one stable operation key. Keep the same key through retries,
carrier changes and handoffs. Record the actual seat, model family, current
head/artifact, evidence, next action and heartbeat. Use existing
`command_center_work_item` / `/api/work/item` for observed work and
`host/coordination_state.py take|renew|release` for claims. If the running app is
unreachable, use these repository roads and mark that limitation; do not report
a tool call, dashboard view or deployment that did not happen.

Renew during meaningful progress and before a 30-minute claim expires. Expiry
permits reconciliation, not blindly starting another process. Check the existing
PID/provider task and output first. Retain completed cells, losses, original
archive identities and raw artifacts; a successor resumes only missing work.
An idle non-GPT seat can keep this ledger current and prepare review packets.

## Build capacity and review capacity are separate

GPT builds, designs and integrates. Reserve short, explicit review bursts around
building: start with at most five minutes in a 25-minute work block when demand
exists; this is a capacity target, not a timer or an obligation to exhaust tokens.
Any available GPT can take the next review batch. Declare zero remaining review
capacity when exhausted; unknown budget is unknown, not unlimited.

Non-GPT seats build isolated changes, reproduce failures, run applicable tests,
and preflight one another's work. They must obtain a quick GPT pass before work
enters main or a release. Unknown/mixed provenance follows this same rule. GPT
work uses the same queue and evidence rules; its builder may record a separate
quick pass over its own change. Prefer another GPT for changes to runtime,
packaging, defaults, policy or release when capacity exists.

One GPT reasoning pass may cover up to ten independent, evidenced changes.
Each change still gets an explicit verdict bound to its own bytes. Unknown
contributors start in batches of three; a contributor with an evidenced recent
regression gets individual review plus independent preflight. Ten accepted,
evidenced changes without a regression in the latest twenty outcomes earn the
larger batch. Record outcomes in `ground/SWARM_RELIABILITY.json` with source
links. Merged count alone is not correctness. No invented model leaderboard;
family determines GPT review responsibility, observed defects determine scrutiny.

When GPT review capacity is zero, already approved exact changes can continue
through integration after mechanical revalidation. Everyone can keep building,
testing and staging new work. Do not grant blanket approval for unseen semantic
changes or relabel an author as GPT to clear the queue. Route the oldest eligible
changes first within a risk lane; runtime/release incidents get priority.

## Executable review contract

`host/swarm_review.py` supplies the packet builder, deterministic reducer and
merge command. The coordination producer and command-center API display its
results. The Actions check is an additional consumer; a saturated Actions queue
does not replace local, exact-change verification.

Source/semantic review and execution authority are different facts. A source-only
`PASS` may clear a semantic RED, but it does not authorize a code/config merge.
For every review subject that changes anything other than pure `.md`, `.rst` or
`.adoc` documentation, the exact-head GPT receipt must contain at least one
passing execution record shaped like
`{"result":"PASS","kind":"execution","head":"<40-hex reviewed head>","reference":"<exact command + receipt>"}`.
A record bound to another head, a source-only PASS, queued hosted checks, or an
unrun command does not satisfy merge authority. Documentation-only changes still
need ordinary passing evidence and GPT review, but are not required to invent an
execution claim. Builders under independent-preflight scrutiny need the same
exact-head execution binding in that preflight. Never relabel source-clean as
execution-green to move the queue.

PR body (ordinary JSON; replace example values with actual observations):

```commons-work
{"seat":"SEAT","family":"claude","operation":"existing-operation-key","read_paths":["path/to/dependency.py"],"evidence":[{"result":"PASS","reference":"exact test command + result/artifact link"}]}
```

Build a packet from the current repository:

```sh
python host/swarm_review.py packet --prs 123,124 --out /tmp/review-packet.json
```

GPT reads the diffs and evidence, then uses each packet's `review_template` in
a PR review fenced `commons-gpt-review`, fills `reviewer`, `decision`, `summary`
and actual `evidence`, and submits a COMMENT review on that exact head. A batch
is one reasoning pass, not one blanket verdict. `HOLD` or `FAIL` supersedes an
older pass; dismissal or movement of the head requires another pass. The
template includes base objects for changed paths, declared dependencies and
the standing policy. Unrelated main movement does not invalidate it; changed
read dependencies do. A reviewer must add any additional dependencies found.

```sh
python host/swarm_review.py merge --pr 123
python host/coordination_state.py publish
```

The merger fetches live provider state, rechecks all receipt bindings against
current main and creates a merge commit for the reviewed head and main. A normal
fast-forward push rejects a concurrent main advance; recompute instead of
forcing it. It does not execute PR code. Publish a fresh command-center snapshot after a batch, using the existing
state branch so updating the queue does not churn main.

GitHub accounts are shared here: a model-family field is a session attestation,
not cryptographic proof of model identity. Do not forge it. This repository
enforces the normal merge/release road. Repository administrators with direct
write access can bypass repository code; absolute enforcement requires a host
ruleset outside this code. Do not claim such a ruleset is installed unless read
back from GitHub. No new credentials or owner-PC deployment are authorized by
this document.

## TITAN continuity

V3.1's submitted archive `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`
ran the R04 whole policy. A package that omits its active route is a policy
replacement, even when raw canonical source contains similarly named features.
Never infer submitted behavior from unshipped source or a passive-opponent test.

Use the existing V5 promotion/release transaction, champion ratchet and native
evidence; do not create another release queue. The transaction requires GPT's
review of the exact archive, source manifest and declared production members.
An R04 restoration must contain the complete reviewed closure. A replacement
must explicitly say so and still pass the existing V3.1 champion comparison.
Required members are checked against captured archive bytes before promotion.
Review cannot override failed economics, missing native evidence or the existing
release-origin interlock.

Current recovery is experimental: #13468 fixes the production-v2 lazy import
failure in production-v3 `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`.
The latest one-seed native sample still has an Apex own-score deficit of 237
against exact V3.1. This is not champion clearance. Preserve existing SPARK PID
3264489 and its actual archive/adapter identity until the owner reconciles it.
Future unstarted cells use the corrected candidate; do not restart completed
panels or relabel old results. See the existing selective-carrot/native-9901
artifacts and the owning #sim-data thread TS1789245175.177299.
