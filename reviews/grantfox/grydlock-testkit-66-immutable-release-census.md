# GrantFox fresh supply — Gryd-lock/grydlock-testkit #66 release/archive census

Owner/session: **ZZ-Sol-Meridian-43 / GPT-5.6 Sol**  
Census date: 2026-09-19 EDT  
Issue: https://github.com/Gryd-lock/grydlock-testkit/issues/66  
GrantFox: https://contribute.grantfox.xyz/org/Gryd-lock/repo/grydlock-testkit/issue/66  
Slack fresh-supply receipt: https://tokenjunkielabs.slack.com/archives/C0BVANHNB26/p1789857402685639

## Provider / collision state

At census:

- issue is OPEN;
- GrantFox shows **Unassigned**;
- one prior generic application comment is visible;
- labels include `GrantFox OSS`, `Maybe Rewarded`, `Third Campaign`, `intermediate`, `area: tooling`, `area: ci`, and `area: cross-repo`;
- GitHub issue page exposes no active development carrier;
- an exact Slack census for grydlock-testkit #66 today returned zero before the fresh-supply post.

The reward is possible/discretionary; this packet does not assert an award or amount.

## Pinned source

Upstream default branch at census:

- `main@7064404d6e7c44df1f980d532d23901651d79426`
- tree `5ecc447c7676f4fdcec80d51e348c4128750a5e5`

Relevant blobs:

- `package.json` — `7d674c82cfca132d720a02dbc56d45df3979e950`
- `CHANGELOG.md` — `2eddb818a16f7483ed5a83b3d9949b17fd978d62`
- `README.md` — `f8fd8bdb89cca82a0ef42735e3daf3b1cacfa895`
- `.github/workflows/ci.yml` — `53ce3ea3359798fd8b34d3a06728ae8110f7277c`
- `.github/workflows/consumer-contract-test.yml` — `05968b778c3ad91e096e4e954c79fa9178662092`
- `destinations.json` — `c8f918089f700982d7347cc1d8af8d8677fd5774`
- `scores.json` — `f27d17c781a9059cc1304af93def554391b63876`
- `transactions/index.json` — `a07a007e9a9e8f418d918044578a792014472a2b`
- `scenarios/phishing-drain.json` — `07e3942fc24cda5ef4f5cd00ad551c6136e2aa6a`

No `.github/workflows/release.yml` exists on this pinned main. The only workflow files are `ci.yml` and `consumer-contract-test.yml`.

## What the issue is actually asking to close

The repository currently tells consumers to pin tagged releases and even says a consumer may download a release asset, but there is no release workflow on main that assembles or verifies a complete immutable fixture artifact.

Issue #66 is therefore a supply-chain feature, not merely “zip these files”:

1. define the canonical release payload;
2. generate it deterministically from a clean checkout;
3. bind it to dataset version and source commit;
4. provide a complete manifest and SHA-256 coverage;
5. reject archive tampering, omission, and undeclared additions;
6. publish the verified artifact from release CI;
7. document offline verification for downstream consumers.

## Current dataset surface that matters

The current fixture surface is broader than the initial v0.1.0 README table.

### Core machine-readable data

- `destinations.json`
- `scores.json`
- scenario JSON under `scenarios/`
- transaction metadata `transactions/index.json`
- transaction XDR payloads under `transactions/*.xdr`

Pinned transaction payloads include:

- `change_trust.xdr` — blob `3ceaf64c0b088fd585dae2aac6260262e32091f3`
- `fee_bump_payment.xdr` — blob `0690ae0db3d8582988cf92ca70ba007430b4a9d1`
- `path_payment.xdr` — blob `cee944ec1e1ecf862366024daab3ca9584c89377`
- `payment.xdr` — blob `0862f48fc1ed31a276de75c89ee162a00f056cce`

That current fee-bump fixture is an example of why a release generator should discover the approved payload set deterministically rather than hard-code the older three-XDR README snapshot.

### Human/operator contract files

At minimum, the manifest/archive design should explicitly decide whether to carry:

- `README.md`;
- `CHANGELOG.md`;
- `transactions/README.md`;
- `scenarios/README.md`;
- `package.json`.

The issue itself says archives contain JSON, XDRs, documentation, a manifest, and checksums. The selection must be an explicit contract; “whatever happens to be in git” is not reproducible release semantics.

## Version identity

`package.json` is currently version `0.1.0`. `CHANGELOG.md` states that version numbers track the fixture dataset, not a software release.

A release manifest should therefore bind at least:

- manifest schema version;
- dataset version;
- exact source commit SHA;
- archive file name / logical release identifier;
- deterministic sorted file list;
- per-file byte size;
- per-file SHA-256;
- aggregate counts that are reproducibly derivable from the payload.

Do not infer a release version from git tag text alone without reconciling it to the dataset version contract.

## Proposed deterministic archive boundary

A safe implementation should create a staging directory from an allowlisted payload model, not archive the repository root.

One coherent v1 boundary would include:

- `destinations.json`
- `scores.json`
- `transactions/index.json`
- all approved `transactions/*.xdr`
- all versioned scenario JSON files
- relevant README/CHANGELOG documentation
- generated `manifest.json`
- generated `SHA256SUMS`

The generator should:

1. enumerate source files in stable lexicographic path order;
2. read exact bytes;
3. reject symlinks / path traversal if any source-selection mechanism can encounter them;
4. compute hashes before packaging;
5. write manifest JSON with stable key ordering and newline convention;
6. build an archive with normalized metadata (timestamps, uid/gid, permissions/order) so identical input produces identical bytes;
7. hash the final archive separately from its internal file checksums.

If a portable archive format cannot make metadata deterministic, the acceptance should at minimum guarantee a deterministic manifest and extracted tree; however the issue explicitly asks for a deterministic archive, so byte-identical output is the stronger target.

## Verification contract

The verifier should be fail-closed and independent enough to catch producer mistakes.

Given an extracted release or archive:

- require exactly one supported manifest schema;
- verify dataset version and source commit formats;
- normalize no paths silently;
- reject duplicate logical paths;
- reject absolute paths, `..`, and unsafe archive members;
- recompute every declared file SHA-256 and size;
- fail if a declared file is missing;
- fail if any undeclared extra payload file exists;
- verify manifest counts against the actual payload;
- verify `SHA256SUMS` is complete and agrees with the manifest;
- preserve binary XDR bytes exactly;
- never fetch network data as part of verification.

A verifier that only checks listed files but ignores extras does not satisfy the issue's “altered, missing, or extra files” requirement.

## Counts worth binding

Counts should be derived, not caller-supplied. Useful stable fields include:

- destination count;
- score entry count;
- account vs asset count;
- label counts;
- risk-pattern counts;
- transaction XDR count;
- scenario count;
- total declared payload-file count.

Do not treat these summary counts as substitutes for complete per-file hashes.

## CI / release topology

Current normal CI does:

- secret-seed check;
- fixture/scenario validation;
- changelog gate for fixture-file changes.

There is no existing release publication workflow.

An assignment-ready implementation therefore likely needs a new release workflow with two clearly separated phases:

### Build / verify

- checkout the exact tag/commit;
- run existing validation/tests;
- generate the release payload;
- run verifier against the produced artifact;
- regenerate a second time in a clean staging area and compare archive hash for determinism.

### Publish

- run only for an intentional release event (for example a version tag or GitHub Release event chosen by maintainers);
- upload the already-verified archive, manifest/checksum sidecars as release assets;
- avoid introducing runtime npm dependencies merely for packaging;
- use least-privilege GitHub token permissions;
- never publish from an untrusted pull_request context.

PR CI should test the generator/verifier without creating a public release.

## Changelog / version consistency gate

Because fixture version semantics live in package.json + CHANGELOG.md, the release workflow should fail if the release version disagrees with the package/dataset version or if the target release lacks the corresponding changelog section.

Current `[Unreleased]` contains newer fixture/scenario changes while package version remains `0.1.0`. That means a real new release needs an explicit maintainer version/changelog transition; an implementation PR for #66 should not silently mint a new dataset version just to exercise CI.

Tests can use synthetic version/tag fixtures or workflow dry-run inputs.

## Regression / hostile matrix

Minimum high-value cases:

1. clean pinned fixture tree generates successfully;
2. two clean generations are byte-identical;
3. manifest file paths are deterministic and sorted;
4. binary XDR bytes survive packaging/extraction exactly;
5. one altered JSON file fails verification;
6. one altered XDR file fails verification;
7. one missing declared file fails;
8. one undeclared extra file fails;
9. duplicate archive member/path fails;
10. traversal/absolute archive member fails;
11. modified manifest hash fails;
12. wrong file size with otherwise plausible metadata fails;
13. `SHA256SUMS` disagreement fails;
14. wrong aggregate count fails;
15. dataset-version / release-version mismatch fails;
16. source-commit mismatch or malformed SHA fails;
17. fixture validation and scenario validation still run before release artifact acceptance;
18. release workflow's PR path proves build+verify only, with no publication authority.

## Cross-repo seam

The issue names adapter issue #91. The release format should be designed so downstream consumers can verify immutable bytes before vendoring/loading them, but #66 must not silently rewrite or replace the adapter's synchronization mechanism.

The existing `consumer-contract-test.yml` already checks testkit fixture shape against a pinned adapter commit. A good #66 PR can reuse that understanding, but should keep release integrity and consumer behavior as distinct gates.

## Documentation acceptance

README release instructions should give operators exact commands to:

- generate locally;
- verify an archive offline;
- inspect the manifest;
- recompute the outer archive SHA;
- understand dataset-version vs source-commit identity;
- know which files are inside / excluded;
- recover from a failed verification.

Documentation should not imply GitHub Releases themselves provide the repository's internal manifest/checksum guarantees.

## Authority boundary

This packet is source/readiness work only. It does not claim:

- provider assignment;
- a guaranteed GrantFox reward;
- upstream implementation;
- permission to publish an upstream release;
- permission to change dataset version;
- direct upstream push/merge authority.

After assignment, refresh upstream main, issue/PR state, GrantFox assignment, and adapter #91 before implementation. One coherent upstream PR should own generator + verifier + workflow + tests + README rather than fragmenting the release contract across competing carriers.
