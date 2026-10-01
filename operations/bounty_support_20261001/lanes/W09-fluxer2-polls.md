# W09 FLUXER2-POLLS — fluxerapp/fluxer-meta#2 Polls

Lane: W09 (BOUNTY-SUPPORT-20261001). Branch: `claude/bh-20261001-w09-fluxer2-polls`. Updated 2026-10-01.
Owned file: this file only.

## State: BLOCKED (agent submission forbidden by upstream policy) + seat OCCUPIED by an active upstream PR

| Field | Value |
|---|---|
| BountyHub listing | 4d7c4070-412c-44b4-a0d9-b1d2ef926d04 |
| Advertised / funded / promised | $500 / $0 / $500 (SWE intake v2, Slack ts 1790854130.570759 corrected post) |
| Payer | Kamalaja (ledger: YELLOW per SWE intake; not re-audited) |
| GitHub issue | https://github.com/fluxerapp/fluxer-meta/issues/2 — OPEN, NOT locked, no comments, no maintainer hold notice (labels Desktop, Mobile, Server; opened 2026-06-03 by Kamalaja) |
| Our PR state | none (no PR opened) |
| Our BountyHub claim state | none |
| Merge state | n/a |
| Payment state | none |

## Contribution route for #2 (tested, no throwaway PR)

- fluxer-meta has a live Pull requests page with zero PRs ever. It is the spec repo; code goes to fluxerapp/fluxer.
- fluxerapp/fluxer accepts external PRs at the platform level: the PR endpoint is enabled, 22 are open, and external authors' PRs are merged (e.g. #1159, #1143 by Taarek). So nothing is technically disabled. The block comes from the repo's policy, not the PR endpoint.
- The policy at main `7c9564b` (license AGPL-3.0-or-later, no CLA):
  - `.github/CONTRIBUTING.md:7,9`: "To prevent spam, only approved contributors may submit pull requests." / "To request approval, comment on an existing issue and ask to implement it. For work that extends beyond a defect fix, open a discussion first." https://github.com/fluxerapp/fluxer/blob/main/.github/CONTRIBUTING.md
  - `.github/CONTRIBUTING.md:36,41`: every commit needs a DCO `Signed-off-by` certification plus a GitHub-verified cryptographic signature. That is a personal attestation, so it would have to come from Bryce.
  - `.github/LLM_USAGE_POLICY.md:7`: "An LLM may assist a contributor privately with learning, investigation, planning and review. It MUST NOT author any part of a submission." https://github.com/fluxerapp/fluxer/blob/main/.github/LLM_USAGE_POLICY.md
  - `LLM_USAGE_POLICY.md:100`: "A contributor MUST NOT direct or permit an autonomous or semi-autonomous agent to create, edit, open, submit or comment on an issue, discussion, security report or pull request."
  - `LLM_USAGE_POLICY.md:120`: "Maintainers MUST close a submission that contains prohibited content." Line 125 says agent submission may get the account blocked from the repository.
- Under the lane orders ("if a policy forbids the submission ... stop that step and record BLOCKED with the exact policy text and link"), this lane cannot request approval on #2, comment, open a PR, or author code meant for submission. No implementation branch was prepared. Code written here is LLM output, and §8 forbids submitting it even after edits, so a prepared branch could never be used for #2.
- Push access to woahwhattheheck/fluxer could not be attached to this session (add_repo access:push was denied by the session permission classifier). That is moot given the policy block.

## Existing upstream polls work (the bounty seat)

- fluxerapp/fluxer#1129 "feat: Implement Polls" by Speykious: OPEN, 90 commits, head `Speykious:polls`, opened 2026-06-22. It has DB (PostgreSQL + Cassandra), API, gateway and app UI, a `SEND_POLLS` permission, expiry, anonymous voting, and graded rather than ranked voting. Review requested from hampus-fluxer and Jiralite. ApparentlyAdam's technical review (2026-09-01) found bugs that the author fixed. notrevenant left changes-requested. The latest author fixes landed 2026-09-26. https://github.com/fluxerapp/fluxer/pull/1129
- fluxerapp/fluxer#1300 "feat: message polls" by linktolink040-crypto: a one-commit, about 5000-line competing PR whose description disclosed LLM assistance. The community flagged it as a duplicate of #1129. The payer, Kamalaja, closed it on 2026-07-06 and the conversation was locked. https://github.com/fluxerapp/fluxer/pull/1300 . A second competing polls PR would repeat that outcome.
- Main `7c9564b` has no polls code (no `SEND_POLLS`, `poll_vote` or `MessagePoll` in TS sources).

## Note for Tessera/Luna2 (their lane, recorded only)

A WebFetch of https://github.com/fluxerapp/fluxer-meta/issues/5 on 2026-10-01 rendered it as not locked. The pinned hold by hampus-fluxer (2026-07-13), "I would like to ask submitters to hold off with any attempts to tackle this bounty for the time being. Thank you.", is still present. The rendered page may omit lock state, so their lane owns that reading.

## Blockers (exact)

1. The fluxerapp/fluxer LLM usage policy (lines 7, 100, 120 above) forbids agent-authored code, PR text, and agent-opened PRs or comments. Only work Bryce writes himself, independently, could enter this route.
2. The approval gate (CONTRIBUTING.md:7–9) needs an approval-request comment on an issue. Under the same policy, that comment must be Bryce's own words, and he would post it himself.
3. DCO sign-off plus a verified signature is a personal attestation from Bryce.
4. The bounty seat is occupied by the active PR #1129, and the payer closed a duplicate (#1300).

## Next action

- None for agents on #2. Keep it in the inventory as BLOCKED/OCCUPIED. Watch #1129: if it merges, the bounty goes to Speykious. If it closes unmerged, the only route still requires Bryce to do the independent work and approval request himself under the policy above.
- Coordinator: this applies to every fluxerapp/fluxer submission, including W10 (#3) and W11 (#8), and to the Tessera/Luna2 #5 route.
