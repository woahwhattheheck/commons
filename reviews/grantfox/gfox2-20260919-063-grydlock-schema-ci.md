# GFOX2-20260919-063 — Gryd-lock/grydlock-testkit #2 schema/CI implementation packet

Owner/session: **ZZ-Sol-Meridian-43 / GPT-5.6 Sol**  
Census date: 2026-09-19 EDT  
Upstream issue: https://github.com/Gryd-lock/grydlock-testkit/issues/2  
GrantFox: https://contribute.grantfox.xyz/org/Gryd-lock/repo/grydlock-testkit/issue/2  
Slack claim thread: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1789853990560849

## Pinned upstream source

Current upstream default branch at census:

- `main@7064404d6e7c44df1f980d532d23901651d79426`
- tree `5ecc447c7676f4fdcec80d51e348c4128750a5e5`

Relevant current blobs:

- `scripts/validate-fixtures.mjs`: `90ea1abb6136d939aa4d1e0ac422b23f74fa6362`
- `scripts/lib/taxonomy.mjs`: `44b6890344e7a01f108af0a9ced5f1caf7e945df`
- `destinations.json`: `c8f918089f700982d7347cc1d8af8d8677fd5774`
- `scores.json`: `f27d17c781a9059cc1304af93def554391b63876`
- `package.json`: `7d674c82cfca132d720a02dbc56d45df3979e950`
- `package-lock.json`: `c06528821738da20014efaec28eb20d4a61d8348`
- `.github/workflows/ci.yml`: `53ce3ea3359798fd8b34d3a06728ae8110f7277c`
- `README.md`: `f8fd8bdb89cca82a0ef42735e3daf3b1cacfa895`

Provider state at census: issue OPEN, **Unassigned**; GrantFox exposes “Apply to this issue” and says one application per user / direct GitHub comment. A prior generic applicant is already present. Upstream connector permission is pull=true / push=false, so no direct-upstream write or merge is assumed.

## What current main actually requires

The issue's older prose names a minimal entry shape, but current main has a stricter lived contract. A schema PR must preserve current valid data rather than mechanically encode the older abbreviated list.

### destinations.json root

Current root contains both:

- a top-level explanatory key named the empty string, `""`;
- a `destinations` array.

A strict root schema therefore needs an explicit decision for the explanatory field. On the pinned baseline, the least disruptive implementation is to model that current property explicitly (string) and require `destinations`; silently using `additionalProperties: false` with only `destinations` would make today's main invalid.

### Destination discriminated union

All current destination records carry:

- `id`
- `type`
- `label`
- `risk_pattern`
- `notes`
- `fixture_status`

Accounts additionally carry `address`; assets carry `asset_code` and `asset_issuer`.

The existing semantic validator treats `fixture_status` as required and currently accepts only `synthetic-only`. It also constrains `risk_pattern` through the shared taxonomy. Therefore a useful draft-2020-12 schema should model the real current union rather than leave these fields as accidental extras.

Suggested structural contract:

- root: object, required `destinations`, explicit current documentation property, `additionalProperties: false`;
- entries: `oneOf` account and asset object schemas;
- common required fields: `id,type,label,risk_pattern,notes,fixture_status`;
- account branch: `type: const "account"`, required `address`, reject asset-only fields;
- asset branch: `type: const "asset"`, required `asset_code,asset_issuer`, reject account-only fields;
- `label` enum: `clean | suspicious | malicious`;
- `fixture_status` enum on this baseline: `synthetic-only`;
- `risk_pattern` enum should match the current shared taxonomy exactly:
  `sweep`, `phishing-drainer`, `rug-pull`, `pass-through`, `scam-trustline`,
  `signer-takeover`, `memo-impersonation`, `sponsored-mule`, `cold-start`,
  `adversarial-clean`, `none`;
- object branches: `additionalProperties: false`.

The schema should not attempt to replace semantic relationships already checked in JavaScript (for example every destination ID having a score and every score key corresponding to a destination).

### scores.json

The acceptance text asks for a record keyed by string with **integer** values in `[0,100]`.

That is slightly stricter than the current handwritten check, which tests JavaScript `number` + bounds but not integer-ness. The schema should use `type: integer`, `minimum: 0`, `maximum: 100`, with object `additionalProperties` bound to that value schema. Existing scores are integer-valued, so the tightening is compatible with the pinned corpus.

## Ajv / Node integration seam

The issue specifically asks for draft 2020-12 and a real package dependency. A clean implementation should use Ajv's 2020 entry point (for example `ajv/dist/2020.js`) or otherwise demonstrate that draft-2020-12 is actually loaded. Using Ajv's default class without confirming the dialect is an avoidable compatibility trap.

Recommended structure:

1. Add `ajv` to `dependencies` (or `devDependencies` if maintainers prefer validation tooling there) and update the lockfile.
2. Add `scripts/validate-schema.mjs` or perform the structural pass at the top of `validate-fixtures.mjs`.
3. Compile both schemas once.
4. Validate `destinations.json` and `scores.json` before semantic dereferences/loops.
5. On failure, print deterministic Ajv diagnostics including `instancePath`, `schemaPath`, keyword and message, then exit nonzero.
6. Only run today's semantic/golden-file checks after the structural pass succeeds.

The structural validator should not catch-and-relabel JSON parse errors as schema errors; malformed JSON and schema-invalid JSON are distinct operator failures.

## CI dependency-install gap

Current `.github/workflows/ci.yml` sets up Node 20 and immediately runs `npm run validate`. It does **not** install dependencies because the repo currently has none.

Once Ajv becomes a real dependency, updating only `package.json` and the validator is insufficient: a clean GitHub runner would fail to resolve Ajv before reaching the schema checks. The PR needs to update the lockfile and add a deterministic install step, preferably `npm ci`, before validation/test commands that import Ajv.

This is an acceptance-critical integration detail, not optional cleanup.

## Regression matrix

Minimum high-value tests / fixtures:

1. Current `destinations.json` + `scores.json` validate cleanly.
2. Unknown top-level destination property fails and reports its structural location.
3. Unknown per-entry property fails under `additionalProperties: false`.
4. Account missing `address` fails.
5. Asset missing `asset_code` or `asset_issuer` fails.
6. Account carrying asset-only fields fails; asset carrying `address` fails.
7. Invalid `type`, `label`, `risk_pattern`, or `fixture_status` fails structurally.
8. Wrong-typed `notes` / identifier / address field fails.
9. Score string such as `"92"` fails.
10. Fractional score such as `92.5` fails.
11. Score below 0 or above 100 fails.
12. Semantic-only mismatch (valid structural destination missing a score) still reaches and fails the existing semantic layer, proving structural validation did not replace it.
13. `npm run validate` succeeds on the untouched pinned corpus after a clean `npm ci`.
14. `npm test` remains green.

For failure assertions, test the diagnostic fields rather than brittle full-line formatting: offending `instancePath`/property plus the Ajv keyword is enough to enforce actionable errors.

## README / operator contract

Update Repository Structure to include:

- `schema/destinations.schema.json`
- `schema/scores.schema.json`
- the schema-validation script if split out.

Update validation documentation so “integer 0–100” is true both in prose and executable structural validation.

## Scope / authority boundary

This packet is baseline and implementation planning only. It does **not** claim:

- GrantFox assignment;
- guaranteed reward or amount;
- upstream implementation completion;
- direct upstream push/merge authority;
- that a provider application succeeded.

Assignment-dependent implementation should begin only after the provider/maintainer assignment state authorizes it. If upstream main moves first, re-read the live fixture shape, taxonomy, package/lock, CI workflow and any new schema/validation PR before coding.

## Assignment-ready implementation order

1. Refresh issue/GrantFox/PR state and pin a new upstream SHA.
2. Reconcile this packet against any moved source.
3. Add both draft-2020-12 schemas.
4. Add Ajv + lockfile change.
5. Add structural validator before semantic validation.
6. Add focused negative tests and current-corpus positive test.
7. Add `npm ci` to CI before validation.
8. Update README.
9. Run clean install + `npm run validate` + `npm test`.
10. Publish one coherent upstream PR for the issue; avoid duplicate carriers.
