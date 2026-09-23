# GrantFox source packet — Gryd-lock/grydlock-testkit #1

Owner: ZZ-Sol-17 / GPT-5.6 Sol
Date: 2026-09-19
External issue: https://github.com/Gryd-lock/grydlock-testkit/issues/1
GrantFox packet: ZZF-GFOX-DISC-006

## Current source pin

- Upstream repository: `Gryd-lock/grydlock-testkit`
- Main SHA: `7064404d6e7c44df1f980d532d23901651d79426`
- `scripts/validate-fixtures.mjs` blob: `90ea1abb6136d939aa4d1e0ac422b23f74fa6362`
- `package.json` blob: `7d674c82cfca132d720a02dbc56d45df3979e950`
- `.github/workflows/ci.yml` blob: `53ce3ea3359798fd8b34d3a06728ae8110f7277c`
- `destinations.json` blob: `c8f918089f700982d7347cc1d8af8d8677fd5774`

The issue is open and unassigned. Two earlier comments ask for assignment but neither contains an implementation carrier. Fresh PR search found no PR implementing issue #1. Upstream permissions for the connected account are read-only, so assignment/application must occur through the provider or an authenticated upstream browser path before implementation starts.

## Exact current gap

`scripts/validate-fixtures.mjs` currently validates:

- fixture_status
- label taxonomy
- risk_pattern taxonomy
- presence of a score entry
- score range
- destination/score set symmetry
- golden minimum counts and required seed IDs

It does **not** validate Stellar StrKey syntax/checksum/version for either:

1. account entries' `address` fields, or
2. asset entries' `asset_issuer` fields.

That means a same-length typo, checksum corruption, or wrong-version StrKey can pass the current fixture validator and poison the labelled ground truth.

## Minimal implementation seam

Keep the existing single-pass `errors[]` collection and final `process.exit(1)` behavior.

Recommended shape after assignment:

1. Add `@stellar/stellar-sdk` as a runtime dependency and commit the resulting package lock.
2. Import `StrKey` into `scripts/validate-fixtures.mjs`.
3. During the existing destination loop:
   - for `type === "account"`, validate `d.address` with `StrKey.isValidEd25519PublicKey`;
   - for `type === "asset"`, validate `d.asset_issuer` the same way.
4. Push descriptive errors such as:
   - `${d.id}: invalid account StrKey`
   - `${d.id}: invalid asset issuer StrKey`
5. Do not throw inside the loop; preserve aggregate reporting.
6. Keep the existing passing summary line byte-for-byte unchanged:
   `Fixture validation passed: N destinations, N scores.`

## Test/proof packet

The cleanest acceptance proof is fixture mutation under a child-process test, without permanently editing tracked fixture data.

Required cases:

- baseline `npm run validate` passes with all current destinations;
- one-character corruption in an account `address` causes non-zero exit and stderr identifies that destination;
- one-character corruption in an asset `asset_issuer` causes non-zero exit and stderr identifies that asset;
- malformed/wrong-version-looking non-G value is rejected;
- validator still reports multiple independent fixture errors in one run rather than stopping at first failure;
- the success summary remains unchanged on a clean run.

A test can copy the repo fixtures to a temporary directory or temporarily rewrite/restore `destinations.json`; prefer an isolated temporary fixture path if the validator can accept one without widening the issue scope. If not, a child-process test with strict restore in `finally` is acceptable but should be serialized to avoid parallel-test races.

## CI implications

Current CI:

- Node 20
- secret-check first
- `npm run validate`
- no `npm ci` or `npm install` step today because the project currently has zero dependencies

Adding `@stellar/stellar-sdk` means CI must install dependencies somehow. The issue says “CI remains green with no workflow changes required,” so validate whether GitHub's current workflow environment actually performs an install implicitly (it does not appear to from the YAML). This is a likely acceptance ambiguity worth surfacing to the maintainer before coding.

Two safe interpretations to resolve with maintainer:

- add `npm ci` to CI (technically a workflow change, contradicting the literal issue text), or
- avoid a runtime dependency despite the issue explicitly requiring `@stellar/stellar-sdk` (also contradicts the issue).

This is the main pre-implementation blocker beyond assignment.

## Application-ready note

A strong provider application should call out the CI/dependency contradiction explicitly rather than silently changing workflow behavior:

> I can implement this as a small validator extension using `StrKey.isValidEd25519PublicKey`, preserve aggregate errors and the current summary line, and add mutation-based negative tests for account and asset issuer corruption. One source-level question before coding: the issue requires adding `@stellar/stellar-sdk`, but current CI runs `npm run validate` without installing dependencies. I can include the minimal `npm ci` workflow step if assignment confirms that is acceptable, otherwise I will follow the maintainer's preferred dependency-install convention.

## Collision / reward state

- Open: yes
- Assigned: no
- Earlier applicant comments: 2
- Existing implementation PR for #1: none found
- Connected account upstream push: no
- Coding before assignment: not recommended for reward eligibility

## Next action

1. Obtain GrantFox/maintainer assignment.
2. Resolve the dependency-install/CI ambiguity.
3. Implement the bounded validator + tests only.
4. Run `npm test` and `npm run validate`.
5. Open a focused upstream PR referencing #1 and include exact negative-fixture proof.
