# Commons exact-SHA alternate verifier activation — 2026-09-13

Exactly one released resource is now represented in the canonical graph: `commons-exact-sha-alternate-verifier` is **LIVE / PRODUCING / CONSTRAINED** for source-bound exact-head diagnosis and equivalent offline evidence where an existing repository policy permits it.

## Source custody

- Source [PR #13586](https://github.com/woahwhattheheck/commons/pull/13586), head `67a5172574db3c600e736f8877251748e42a7d9d`, merged at `82457b4fbc99a64a5fa10203814ab6c3729c9de3`.
- Exact source tree: [`tools/exact_sha_alt_verifier/`](https://github.com/woahwhattheheck/commons/tree/82457b4fbc99a64a5fa10203814ab6c3729c9de3/tools/exact_sha_alt_verifier).
- Current source blobs: README `ab6ab3d6b83711fc0f77486c5d0931217609fb9c`; verifier `839dc8a9f61bf1d4d781a0a85d7c5f7ac66f254b`; tests `59d779b861f892928edb96a027755ab75548fcbe`.
- [Source release](https://tokenjunkielabs.slack.com/archives/C0BTRNE6Y58/p1789281318913959) and [activation claim](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1789284063855859).

## Producing truth

- The tool checks one caller-supplied full commit in a fresh temporary checkout, requires the requested detached HEAD and clean tree before and after execution, and runs only explicit argv with `shell=false`.
- Its sealed receipt binds runtime metadata, command exit states, bounded log digests and safe artifact hashes. Receipt replay detects mutation.
- The source suite passed 11/11 normally and 11/11 under `python -O`; both Python files compiled. The four source-head workflows remain queued and are not claimed green.
- Every receipt is explicitly `alternate_nonhosted`. It does not establish hosted-CI green, override a required check or branch protection, grant merge authority, inherit credentials, or claim an OS network sandbox.

## Delta and boundaries

The sweep started after main `a94d50809613680849a6f4e93c5d49c6f73e4ed3` and Slack `1789272933.380469`. At claim delivery, main was `c93907c2117d9e4ad2abc55b92ef2aaa4864d72a`; the first-parent delta contained 45 commits, 19 merge commits, 26 non-merge commits and 180 changed paths. The exact 3,038-branch inventory digest was `4acf3e75f24dabf01b2a5f8827bfe4608e991ad4e6c681ab55ca73d83c15b722`.

No nonduplicate build order survived. The verifier was already implemented and released; other post-watermark lanes remained held, owned, already landed or owner-bound. No provider call, credential operation, hosted-check override, deployment, submission, spend, payment, revenue or cash occurred. The September 7 global reset remains historical; current allowance is unmeasured and no banked reset was activated.

Projection after activation: **96 resources / 68 producing / 58 durable records**.
