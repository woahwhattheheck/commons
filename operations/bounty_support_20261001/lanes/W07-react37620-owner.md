# W07 REACT37620-OWNER — react/react#37620 (facebook/react#37620)

Updated 2026-10-01. Sole submission owner for this issue.

## State (each kept separate)

| Field | Value |
|---|---|
| BountyHub listing | `cb7e2ac5-31e5-48c8-95c6-2e2c47bf8bac` (https://www.bountyhub.dev/en/bounty/view/cb7e2ac5-31e5-48c8-95c6-2e2c47bf8bac) |
| Advertised / funded / promised | $100 / $0 escrow / $100 PROMISED (`paymentStatus: PROMISED`, pledge `isAccepted:false`, `isPaid:false`) |
| Payer | `devlootxyz-bounties` (`paymentVerified:false`). Payer ledger accepted as-is. |
| Assignment type | `exclusive`: "only the assignee may claim this bounty. Other users can send an assignment request to be considered." (BountyHub UI text) |
| Assignment status | `assignee: null`. 13 assignment requests, all `PENDING`, none answered (oldest 2026-09-15, newest 2026-10-01). None from woahwhattheheck. |
| BountyHub claim | `claims: []`, `claimed:false`, `solved:false`. No claim by us. |
| GitHub issue | OPEN, label `Status: Unconfirmed`, no maintainer response. |
| Competing upstream PRs (all open) | #37648 (xyjk0511), #37654 (Jr-kenny), #37694 (theworker02), #37705 (sidshehria). #37694 and #37705 have byte-identical reconciler diffs. |
| Our PR | NOT OPENED. READY-TO-SUBMIT. Blocked on the fork (see blockers). |
| Merge state | none |
| Payment state | none |

Source: `GET https://api.bountyhub.dev/api/bounties/cb7e2ac5-31e5-48c8-95c6-2e2c47bf8bac` (public API, read 2026-10-01).

## Root cause (found in a local clone of facebook/react @ 7c6ac13)

`packages/react-reconciler/src/ReactFiberBeginWork.js`, `updateDehydratedSuspenseComponent`:
1. A `use(browser())` bailout makes Fizz emit `<!--$!-->` (client-render fallback, digest `REACT_RECOVERABLE_DIGEST`). `mountDehydratedSuspenseComponent` schedules the boundary at `DefaultLane`.
2. First pass: `isSuspenseInstanceFallback`, so `retrySuspenseComponentWithoutHydrating`. That queues deletion of the dehydrated fragment (the server fallback DOM), sets `memoizedState = null` and mounts the primary children.
3. The primary suspends on the client-created promise. Second pass: `memoizedState === null`, so `mountSuspenseFallbackAfterRetryWithoutHydrating`. A new fallback is inserted and the server fallback is deleted, which restarts the animation.
4. `/server-promise` doesn't suspend in step 3, so it never reaches the fallback path.

## Fix (my design; differs from the 4 open PRs)

In the second pass, when the instance is `<!--$!-->` with the recoverable `browser()` digest and `current.memoizedProps === nextProps`, the fix:
- removes the dehydrated fragment from `deletions`,
- restores the dehydrated `SuspenseState`, and
- completes it as a dehydrated boundary that suspended. That path already exists for hydration suspends: the retry listener is attached via `Update`, and on resolve the retry client-renders the content.

The fix is local to the one boundary and adds no root-level commit delay, which was the mechanism #24236 used and was reverted for. A changed fallback prop keeps the current recreate behavior. Server-error fallbacks are out of scope: each retry re-queues the hydration error, which shows up as double reporting when the #24236 FIXME tests are ungated.

## Checks run (all in ~/work/react)

- New test 1 FAILS on unmodified main (fallback `<p>` replaced by an identical node) and PASSES with the fix. New test 2 passes.
- experimental + stable: Fizz, PartialHydration, SelectiveHydration, FizzShellHydration, FizzSuspenseList, PartialHydrationActivity suites: 561/561 passed on each channel.
- www-modern variant true/false (3 suites): 276/276 each. `--prod` experimental (3 suites): 276/276. Reconciler `ReactSuspense*`: 10 suites, 220/220.
- `yarn lint` passed, prettier clean.
- `yarn flow dom-node` and `flow-ci dom-node`: the single error is `Internal error: check job timed out after 100 seconds` in `react-client/src/ReactFlightClient.js`. Identical on unmodified main in this VM. No type errors.

## Artifacts

- Upstream-format patch: `operations/bounty_support_20261001/lanes/W07-react37620-owner/0001-Keep-server-fallback-when-browser-only-content-suspe.patch` (author `woahwhattheheck <293286387+woahwhattheheck@users.noreply.github.com>`, no trailers)
- PR title/body (follows `.github/PULL_REQUEST_TEMPLATE.md`): `operations/bounty_support_20261001/lanes/W07-react37620-owner/PR_BODY.md`
- Local branch: `~/work/react` `fix-ssr-fallback-remount-browser-only` (commit c7b6d2a on 7c6ac13)

## Support lanes

- W08 (tests / #24236 history) and W15 (dom-bindings/Fizz): branches `claude/bh-20261001-w08-react37620-tests` and `claude/bh-20261001-w15-react37620-dom` did not exist on origin at my read. Nothing to integrate yet. No dom-bindings or Fizz change is needed for this fix. If W08 lands a test, it replaces or extends my two tests in `ReactDOMFizzServer-test.js`.
- dot: BH-REACT-37620-LIVE-REPRO, deployed demo, reset inconclusive (DevTools blocked). BH-REACT-37620-NODE-CONTINUITY: React 19.3.0 + JSDOM reproduces "original removed 1, replacement inserted 1" on /client-promise, with the controls retaining the node. That matches the mechanism above and the failing-before test.

## Blockers / owner steps (exact)

1. **Fork missing (READY-TO-SUBMIT; one missing step).** `git ls-remote https://github.com/woahwhattheheck/react.git` gives `could not read Username` (not found). `add_repo woahwhattheheck/react push` gives "you don't have access to woahwhattheheck/react". Fork creation through `mcp__github__fork_repository` is blocked by the machine hook. Needed: fork https://github.com/facebook/react to woahwhattheheck/react (Bryce or coordinator). Then: `git am` the patch on main, push the branch, and `create_pull_request` to facebook/react with PR_BODY.md.
2. **BLOCKED-owner: Meta CLA.** PR template item 10: "If you haven't already, complete the CLA." CLA signature status for woahwhattheheck is unknown until the `meta-cla` bot runs on a PR. Bryce signs at https://code.facebook.com/cla (personal signature; not done by agents).
3. **BLOCKED-owner: BountyHub exclusive assignment.** The listing is exclusive with no assignee: "only the assignee may claim this bounty". To be eligible to claim, Bryce's BountyHub account must send an assignment request on the listing page above and be accepted by `devlootxyz-bounties`. 13 earlier requests have been pending without response since 2026-09-15. Two of them cite their own open PRs (#37648, #37705). Merge without assignment does not make the claim eligible.
4. Email blockers per RULES rule 3: this session's Gmail connector exposes read/draft-list tools only (no send) and Slack writes are hook-blocked. Coordinator to relay items 1–3 to Bryce.

## AI-use / disclosure

facebook/react's CONTRIBUTING and PR template contain no AI-use policy or disclosure question (checked `.github/PULL_REQUEST_TEMPLATE.md` and `CONTRIBUTING.md` at 7c6ac13). The PR body states only technical content.

## Next action

Once the fork exists: `git ls-remote` the fork, add_repo push, push branch `fix-ssr-fallback-remount-browser-only`, open the PR with PR_BODY.md, subscribe_pr_activity, answer review.
