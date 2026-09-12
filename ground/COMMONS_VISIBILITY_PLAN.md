# Commons visibility plan

First draft, written from a full read of the workspace. Every item is free to take, change or drop. Peers are free to fix anything here, including the parts already built.

The idea is to turn the sentences seats already write on every hop into rows the system computes once. Serve those rows in forms every harness can read: plain JSON over an unauthenticated GET, in tiers small enough for any context window.

Status key: **BUILT** (in `host/coordination_state.py`, see `ground/COORDINATION_STATE.md`) · **OPEN** (unclaimed; take it) · **OWNER** (needs Bryce's decision).

## A. Ownership

| id | item | status |
|---|---|---|
| A1 | **Holdings keyed on the change, not the marker.** One file per change key on `state/claims`, fast-forward-only writes, TTL and heartbeat, automatic lapse. The key strips base SHA, date and retry suffixes, or uses the content digest. | BUILT (`take` / `renew` / `release` / `holders` / `key`) |
| A2 | **Review-holding merge check.** A check run that stays pending while an unexpired review holding on the same head is live. | OPEN |
| A3 | **Lane load signal.** Active holders per lane over the last N minutes, shown before a seat takes a fourth. | OPEN (data is in `holders`) |

## B. Changes on a moving main

| id | item | status |
|---|---|---|
| B1 | **Disjoint-advance certificate** per open PR, computed against its own base tip: merge-base, paths, tip delta, overlap, and the composed tree. With no overlap, the reviewed bytes compose exactly and the certificate carries the custody arithmetic. | BUILT (`drift`) |
| B2 | **One lane per change.** PRs joined by identical content key and supersession text; chain, open members, newest open. | BUILT (`lanes`) |
| B3 | **Serialized integration.** A merge queue, or one integrator queue composing onto the queue head. | OWNER (repository settings) |
| B4 | **Root-moved event.** When a canonical branch tip moves, every lane on that root reads rebind-required or disjoint-ok, from B1. | OPEN (B1 gives the per-PR half) |
| B5 | **Shared files carry hunks.** For paths two open PRs share, compose reviewed hunks, not whole blobs. Split AGENT_VIEW.md into per-topic fragments so parallel doc edits stop sharing a blob. | OPEN |
| B6 | **Generated-path moves.** Classify board-ingest, projection and MANUAL rebuild commits as generated in the certificate, so they read distinctly from feature merges. | OPEN |

## C. Verdicts and hosted truth

| id | item | status |
|---|---|---|
| C1 | **Verdict fields** parsed from review text: source, composition, current_main, hosted and economics, each with its review id; superseded and retracted reviews skipped; bound to the current head. | BUILT (first-draft parser) |
| C2 | **Verdicts as check runs** `titan-review/<field>`, so GitHub's own UI and merge rules see review state that COMMENT reviews cannot carry. | OPEN |
| C3 | **Hosted enum**: NOT_EXECUTED_QUEUED / RUNNING / APPROVAL_GATED / CANCELLED_NOT_RUN / FAILED / SUCCESS, with a rollup that keeps queued distinct. | BUILT (`hosted`) |
| C4 | **Actions queue depth and oldest queued age** on every head read. | BUILT (`queue`) |
| C5 | **Queued-run watch with a declared next step.** Register "on SUCCESS do X, on failure do Y" against a run id, fired when the state changes. | OPEN |
| C6 | **Reusable exact-head checkout** (`workflow_call`), plus a lint for bare `actions/checkout@v4` in evidence workflows. | OPEN |

## D. Experiments

| id | item | status |
|---|---|---|
| D1 | **Experiment ledger keyed by hypothesis id.** Every bench side by side (forensic estimate, small gate, field gate, frozen panel) with sample size, under the declared objective. | OPEN |
| D2 | **Gate objective as a versioned file** that reducers import, so PR prose, reducer and fixtures read one definition. | OPEN |
| D3 | **Shared strict-receipt library with poison fixtures**: literal requested panel, strict non-bool ints, finite scores, duplicate rejection before indexing, exact cartesian membership, live-canonical freshness. | OPEN |
| D4 | **Lane registry using the five-field factor report**: canonical parent, durable carrier, terminal state, next gate, intended production consumer. A REJECTED status propagates to every line that composed the lane. | OPEN |
| D5 | **Finding registry with three-layer activation census**: detector hits, candidate callbacks, realized actions. Each null carries its search space. | OPEN |
| D6 | **Opponent registry keyed by digest**, and causal-witness records with an `observable` field. | OPEN |

## E. Artifacts and facts

| id | item | status |
|---|---|---|
| E1 | **Artifact registry keyed by sha256**: git blob, commit, path, Slack file, and workflow artifact with its producing job's conclusion. | OPEN |
| E2 | **Receipt resolver.** Any id (PR, review, run, blob, marker) returns its state in one call. | OPEN (PR half is in `coordination.json`) |
| E3 | **FACTS card**: engine field types, evaluator output schema, protection/ruleset state, compute roads when runners are busy, "patch large JSON, never retype it". | OPEN |
| E4 | **Defect-class registry → lints.** Examples: `py_compile` under a clean-tree check; `${{ }}` inside a `run:` heredoc; artifacts under `if: always()`; coercing reducers; a carrier that pins a donor blob it doesn't carry; falsy-default synthesis; a strict reducer with a stale good-fixture; whole-file transcription drift. | OPEN |

## F. Directives, capabilities, feeds, email

| id | item | status |
|---|---|---|
| F1 | **Owner-directive index**: explicit owner mark, one broadcast row per op id listing every surface it went to, and a per-seat ACK column filled from heartbeats. | OPEN |
| F2 | **Capability fields in `seats/<NAME>.json`**: `can_push_github`, `polls` (the surfaces the seat actually reads, app DMs included), `native_namespaces`, egress and rate limits. Events from a seat that can't push carry `durability: local-only`. | OPEN |
| F3 | **Needs-runner queue**: work orders that name what they need a runner to be able to do, with the canonical packet, a one-publisher rule and a return slot. | OPEN |
| F4 | **Needs-owner queue** for owner-auth items. The first successful owner action retires a row. | OPEN |
| F5 | **Org-wide merged feed**: channels, thread replies, app DMs and upstream repos, with threads flattened and cross-posts deduped by content hash plus source permalink. | OPEN |
| F6 | **Email-thread ledger generated from Gmail**, one row per thread with its state, linked to its lane. | OWNER (scope) |

## Tiers every surface should follow

| tier | size | contents |
|---|---|---|
| head | ≤ 2 KB | seq or observed_at, tip SHAs, counts, newest cursor |
| window | ≤ 32 KB per page | seq-keyed deltas |
| cards | ≤ 8 KB | one topic each |
| ledgers | paged | full rows with links |

Rows carry ids and one-line summaries. Hash lists travel by reference: a certificate or resolver id, never retyped into posts.

## How to take an item

Take it the way the fleet takes any lane. Optionally, run `python host/coordination_state.py take vis-<id> --holder NAME` to mark it on `state/claims`. Build it, then say where it landed. Change this file when an item's status changes.
