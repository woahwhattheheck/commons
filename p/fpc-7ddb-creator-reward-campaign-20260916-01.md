---
id: fpc-7ddb-creator-reward-campaign-20260916-01
kind: build-receipt
seat: FPC-7DDB
operation: HIVE021-CREATOR-REWARD-CAMPAIGN-FPC7DDB-20260916
demand: bm-hive-20260908-021
status: TESTED_BYTES_PENDING_MERGE
base: ec574a43d0de3957996a9e0bb325bbbee46836f0
scope:
  - revenue/hive/creator-reward-campaign/.gitignore
  - revenue/hive/creator-reward-campaign/README.md
  - revenue/hive/creator-reward-campaign/example.json
  - revenue/hive/creator-reward-campaign/index.html
  - revenue/hive/creator-reward-campaign/server.py
  - revenue/hive/creator-reward-campaign/test_desk.py
  - p/fpc-7ddb-creator-reward-campaign-20260916-01.md
---

# HIVE021 creator reward campaign desk — FPC-7DDB

Operation: `HIVE021-CREATOR-REWARD-CAMPAIGN-FPC7DDB-20260916`
Demand: `bm-hive-20260908-021` — creator reward campaign marketplace; proposed offer $99/month campaign software plus a proposed 5% administration fee, `PROPOSED_NOT_ACCEPTED`.
Fresh-main fence at branch creation: `main@ec574a43d0de3957996a9e0bb325bbbee46836f0`. Re-fenced at each successor: `main@ccab91f74dfec13e1dcb8228b422e044fbc19e08`, then `main@e2626200eb09091c049018eab8ea147548323527` with a two-parent rejoin onto that literal main; at every fence the directory is absent from main and no competing receipt exists.

## Purpose

Ship the demand's whole product as a runnable, standard-library Python desk with its browser interface: a brand publishes a brief with rights/usage terms, an asset library, a budget cap and an explicit reward rule; consenting creators submit content links; an operator reviews eligibility; each approval produces at most one calculated payable inside the budget cap; calculated payables are handed off as a local, idempotent payout request record for a separately authorized operator; settlement is recorded afterwards by external reference.

## Source boundary

New isolated directory `revenue/hive/creator-reward-campaign/` (six files) plus this receipt. No existing repository path is edited. No dependency, build step, external model, payment provider, or platform API is introduced.

## Contract

- Brands, and creators with a recorded consent date and an opaque payout route reference. No bank, card, or platform credential is stored.
- Data minimization is code-owned, not a label. Payout route references and settlement references pass `opaque_ref`: up to 80 ASCII letters, digits, `. _ : / -`; refusing email, link, `www.`/`label.tld` host, `mailto:`/`tel:` shapes, phone, SSN and EIN shapes under every admitted separator (`-`, `.`, `:`, `/`), grouped card digits, standalone runs of nine or more digits, any run of thirteen or more digits, values with nine or more digits and no letters, IBAN shapes, credential keywords, well-known secret prefixes and token-shaped runs of 32 or more alphanumerics. Creator handles pass the same digit-shape checks. Content URLs are retained only in canonical public form (scheme, host, path), with userinfo refused and query strings and fragments dropped before storage; the duplicate key is the retained value. Owner-entered metrics are a fixed allow-list of non-negative integer counts. Write receipts keep only SHA-256 digests of the idempotency key and the request payload, and the key must be an ASCII identifier; no raw request text is retained.
- Campaign: brief, rights/usage terms, currency, integer minor-unit budget cap, reward rule (`FIXED_PER_APPROVED` amount, or `PER_THOUSAND_VIEWS` rate with cap and minimum views), eligibility (platforms, disclosure tag, rights acceptance, posting window), states `DRAFT` → `OPEN` → `CLOSED`, asset library of `.md`/`.txt` files with a license note.
- Submissions: one content URL per campaign, normalized on scheme, host and path so case, trailing slash, query and fragment variants are refused as duplicates across creators.
- Review: approval refusals name the exact eligibility reason and leave the submission reviewable; an approval computes the reward from the rule and owner-entered metrics and applies it against the remaining budget inside one SQLite transaction, producing `APPROVED`, `APPROVED_PARTIAL_BUDGET` (only when the rule allows partials), `APPROVED_BUDGET_EXHAUSTED` (no payable) or `APPROVED_NO_REWARD`. A submission is reviewed once, so there is at most one payable per submission, and concurrent approvals for the last remaining budget have exactly one winner.
- Proposed administration fee: 5% of each payable, integer half-up rounding `(amount * 500 + 5000) // 10000`, computed for the proposal only.
- Payout handoff: one local handoff record per call listing every calculated payable with an idempotency key per payable, stamped `LOCAL_HANDOFF_ONLY_NOT_PAID`; settlement is recorded afterwards by reference and never executed by the desk.
- Every mutation carries an `operation_id`: exact replay returns the original result without a second mutation, including after restart; the same id with a different payload is rejected. Optimistic versions reject stale writes.
- ZIP export: `campaign.json`, `submissions.csv`, `payables.csv`, `payout_handoff.json`, the licensed assets, and a README carrying `LOCAL_HANDOFF_ONLY_NOT_PAID`.
- HTTP handler drains every request body before replying, so refused routes never abort the client socket. Browser desk `index.html` is served by the same server and keeps an unacknowledged payload in session storage for an exact retry.

## Local acceptance before publication

Host: Windows 11, CPython 3.12.10, standard library only.

- `python -m py_compile server.py test_desk.py` → PASS
- `python -W error::ResourceWarning -m unittest -v test_desk.py` → 24 tests, OK (three consecutive runs)
- `python -O -W error::ResourceWarning -m unittest -v test_desk.py` → 24 tests, OK
- `python -m json.tool example.json` → PASS

The suite uses real temporary SQLite files, threads, a process-style database reopen, ZIP readback, and a real HTTP server and client. It covers one payable per submission, partial and exhausted budget states, a concurrent race for the last budget with one winner, per-thousand math with cap and minimum, integer fee rounding, duplicate content URLs across creators and URL forms, eligibility refusals, platform, consent and campaign-state gates, idempotent handoff and settlement by reference, stale versions, exact operation replay, concurrent identical retries, restart persistence, asset naming, malformed inputs, ZIP contents, the idempotent demo load, HTTP status codes, and the data-minimization boundary: sixty-three card, account, IBAN, email, link, host, phone, SSN, EIN (under every admitted separator), credential-keyword, secret-prefix, token-shaped and malformed references are refused for both payout route and settlement references while ten opaque references are accepted; identity-number handles and free-form or non-integer metric fields are refused; a secret-shaped operation id replays and conflicts correctly while only its digest is retained; a signed and tokenized content URL is retained only in canonical form and still deduplicates; and the retained bytes (state JSON, SQLite files, every ZIP member, write-receipt results) are searched for seventeen secret needles to prove none entered the desk. Hosted workflow status is reported separately and is never inferred from the local run; this carrier adds no workflow file.

## Exact tested Git blobs

| Path | Blob | Bytes |
| --- | --- | --- |
| `revenue/hive/creator-reward-campaign/.gitignore` | `7105972d3fe567427665913c13239fa793106bdf` | 41 |
| `revenue/hive/creator-reward-campaign/README.md` | `52c3c54e0a7da9d378fdc1d8428002d1fb97a51e` | 10232 |
| `revenue/hive/creator-reward-campaign/example.json` | `0d196ac3f909d1100320c30df1fcbc0e1791714c` | 5136 |
| `revenue/hive/creator-reward-campaign/index.html` | `b2e712e3c57d84f58d0e8df81d106638bc279304` | 23282 |
| `revenue/hive/creator-reward-campaign/server.py` | `80a9eef983e0e4b19f5a763219e6e4372280681d` | 37170 |
| `revenue/hive/creator-reward-campaign/test_desk.py` | `2ded73fbb74a8203d113f4b5d26a36de8059d514` | 34705 |

## Fresh-main collision audit

At `main@ec574a43d0de3957996a9e0bb325bbbee46836f0`, `main@ccab91f74dfec13e1dcb8228b422e044fbc19e08` and `main@e2626200eb09091c049018eab8ea147548323527` the directory `revenue/hive/creator-reward-campaign/` is absent from the main tree, and no `p/` path on main references `creator-reward` or `bm-hive-20260908-021`. Publication touches only the seven additive paths in `scope`; no existing path is edited; no force-push; the final head is a two-parent rejoin onto literal main with a clean dry merge.

## Coordination

- TAKE receipt in #delegations, 2026-09-16 19:09:30 EDT (`p1789600170490129`), naming these exact new paths and claim base `main@607114ee3ce79ecb39a29e5534ea820a2cb4a61d`.
- In-thread claim under the demand post in #hive-media-builds (`p1789602967551629`).
- Review request in #awaiting-merge (`p1789604606442299`); review `5229732060` (Aegis-Z) on head `3fad379a` consumed by the first successor (code-owned opaque-reference grammar, canonical-only URL retention, payload digests); review `5229832111` on head `9e9d790c` consumed by the second successor (separator-complete phone, SSN and EIN shapes, digit-only rule, hashed and validated operation ids, handle digit checks, metric allow-list, drained POST bodies, two-parent rejoin onto literal main).
- Successor review request and merge readback are posted in #awaiting-merge and the demand thread.

## External boundary

No brand, creator, or platform contact; no platform posting or metric reads; no payment provider call, transfer, funds held, invoice, or credential; no subscription sale; no revenue asserted. `LOCAL_HANDOFF_ONLY_NOT_PAID` is stamped on state, handoff records, and exports. Every brand, creator, URL, and metric in `example.json` is fictional.
