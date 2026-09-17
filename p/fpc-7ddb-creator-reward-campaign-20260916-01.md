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
Fresh-main fence at branch creation: `main@ec574a43d0de3957996a9e0bb325bbbee46836f0`. Re-fenced at each successor: `main@ccab91f74dfec13e1dcb8228b422e044fbc19e08`, `main@e2626200eb09091c049018eab8ea147548323527`, `main@f21cbbe1fb42daab2c3056399c41036322741488`, `main@8ef24440dd444fb2c18b4a8b55a4bc1ad2e0829a`, `main@c9cd388e18c7deac1c9f0bd41ef3ce12be97529e`, then `main@aeab59035ef1a3246744d17836488a763fecc1b3`, each time with a two-parent rejoin onto that literal main; at every fence the directory is absent from main and no competing receipt exists.

## Purpose

Ship the demand's whole product as a runnable, standard-library Python desk with its browser interface: a brand publishes a brief with rights/usage terms, an asset library, a budget cap and an explicit reward rule; consenting creators submit content links; an operator reviews eligibility; each approval produces at most one calculated payable inside the budget cap; calculated payables are handed off as a local, idempotent payout request record for a separately authorized operator; settlement is recorded afterwards by external reference.

## Source boundary

New isolated directory `revenue/hive/creator-reward-campaign/` (six files) plus this receipt. No existing repository path is edited. No dependency, build step, external model, payment provider, or platform API is introduced.

## Contract

- Brands, and creators with a recorded consent date and an opaque payout route reference. No bank, card, or platform credential is stored.
- Data minimization is code-owned, not a label. Payout route references and settlement references pass `opaque_ref`: up to 80 ASCII letters, digits, `. _ : / -`; refusing email, link, `www.`/`label.tld` host, `mailto:`/`tel:` shapes, phone, SSN and EIN shapes under every admitted separator (`-`, `.`, `:`, `/`), grouped card digits, standalone runs of nine or more digits, any run of thirteen or more digits, values with nine or more digits and no letters, IBAN shapes, credential keywords, well-known secret prefixes and token-shaped runs of 32 or more alphanumerics. Creator handles pass the same digit-shape checks. Owner-entered metrics are a fixed allow-list of non-negative integer counts. Write receipts keep only SHA-256 digests of the idempotency key and the request payload, and the key must be an ASCII identifier; no raw request text is retained.
- Content URLs are retained only in canonical public form: scheme, lowercased ASCII host (punycode for internationalized hosts), an explicit non-default port (part of the content identity; default ports folded away, malformed ports refused, IPv6 hosts bracketed) and a canonical path (dot and empty segments refused, percent-escapes uppercase, unreserved octets literal, trailing slash dropped), with userinfo refused, fragments dropped, and known tracking or share parameters dropped. Query material survives only where a code-owned projection names it as the content identity: YouTube video ids are kept and normalized to `https://www.youtube.com/watch?v=<id>` from watch, `youtu.be`, shorts, live and embed forms. Any other query material (signed or tokenized links, unknown parameters) is refused with an exact reason rather than silently stripped, so a secret never enters the desk and a content identity is never lost; the duplicate key is the retained value.
- The server binds loopback addresses only (`127.0.0.1`, `::1`, `localhost`), enforced in `make_server` and the CLI rather than in prose; the desk has no remote authentication and is not served on other interfaces. Request bodies are bounded at 5 MB: bodies within the bound are read in full before any reply, while malformed, missing, oversized or short bodies are refused with a clean JSON reply and a closed connection. JSON is parsed strictly at the HTTP boundary and in the demo loader: duplicate object keys, `NaN`/`Infinity` constants, strings that are not valid Unicode scalar values (lone surrogates) and nesting bombs are refused with a clean 400 rather than silently resolved; the write seam refuses the same shapes for in-process callers.
- Campaign: brief, rights/usage terms, currency, integer minor-unit budget cap, reward rule (`FIXED_PER_APPROVED` amount, or `PER_THOUSAND_VIEWS` rate with cap and minimum views), eligibility (platforms, disclosure tag, rights acceptance, posting window), states `DRAFT` → `OPEN` → `CLOSED`, asset library of `.md`/`.txt` files with a license note.
- Submissions: one content URL per campaign, deduplicated on the retained canonical value so case, trailing slash, tracking-parameter and YouTube link-form variants are refused as duplicates across creators.
- Review: approval refusals name the exact eligibility reason and leave the submission reviewable; an approval computes the reward from the rule and owner-entered metrics and applies it against the remaining budget inside one SQLite transaction, producing `APPROVED`, `APPROVED_PARTIAL_BUDGET` (only when the rule allows partials), `APPROVED_BUDGET_EXHAUSTED` (no payable) or `APPROVED_NO_REWARD`. A submission is reviewed once, so there is at most one payable per submission, and concurrent approvals for the last remaining budget have exactly one winner.
- Proposed administration fee: 5% of each payable, integer half-up rounding `(amount * 500 + 5000) // 10000`, computed for the proposal only.
- Payout handoff: one local handoff record per call listing every calculated payable with an idempotency key per payable, stamped `LOCAL_HANDOFF_ONLY_NOT_PAID`; settlement is recorded afterwards by reference and never executed by the desk.
- Every mutation carries an `operation_id` and exactly the fields its operation defines (any other field refuses the whole payload); exact replay returns the original result without a second mutation, including after restart; the same id with a different payload is rejected. Optimistic versions reject stale writes. Handles are case-insensitive and stored lowercase. Text fields accept printable text with newlines and tabs only. The database path must be a regular file, and every connection is bound to the database the desk opened: the identity minted into the SQLite header at creation is read back through each connection before any statement runs, a substituted database is answered 503 and receives nothing, and the desk resumes when its own database is back.
- ZIP export: `campaign.json`, `submissions.csv`, `payables.csv`, `payout_handoff.json`, the licensed assets, and a README carrying `LOCAL_HANDOFF_ONLY_NOT_PAID`. Browser desk `index.html` is served by the same server and keeps an unacknowledged payload in session storage for an exact retry.

## Local acceptance before publication

Host: Windows 11, CPython 3.12.10, standard library only.

- `python -m py_compile server.py test_desk.py` → PASS
- `python -W error::ResourceWarning -m unittest -v test_desk.py` → 35 tests, OK (two consecutive runs; the symbolic-link custody case skips where links are unavailable)
- `python -O -W error::ResourceWarning -m unittest -v test_desk.py` → 35 tests, OK
- `python -m json.tool example.json` → PASS

The suite uses real temporary SQLite files, threads, a process-style database reopen, ZIP readback, a real HTTP server and client, and raw sockets. It covers one payable per submission, partial and exhausted budget states, a concurrent race for the last budget with one winner, per-thousand math with cap and minimum, integer fee rounding, duplicate content URLs across creators and URL forms, eligibility refusals, platform, consent and campaign-state gates, idempotent handoff and settlement by reference, stale versions, exact operation replay, concurrent identical retries, restart persistence, asset naming, malformed inputs, ZIP contents, the idempotent demo load, HTTP status codes, and the data-minimization boundary: sixty-three card, account, IBAN, email, link, host, phone, SSN, EIN (under every admitted separator), credential-keyword, secret-prefix, token-shaped and malformed references are refused for both payout route and settlement references while ten opaque references are accepted; identity-number handles and free-form or non-integer metric fields are refused; a secret-shaped operation id replays and conflicts correctly while only its digest is retained; signed or tokenized content URLs are refused while tracking parameters are dropped; two distinct YouTube watch ids are accepted, retained and exported as distinct canonical links while `youtu.be`, mobile and shorts aliases of the same ids are refused as duplicates; the retained bytes (state JSON, SQLite files, every ZIP member, write-receipt results) are searched for the secret needles to prove none entered the desk; loopback-only binding is enforced for `make_server` and the CLI; raw-socket requests with malformed, negative, missing, oversized and short `Content-Length` values and an unknown route all receive clean JSON replies; duplicate-key, `NaN`, `Infinity`, non-object and unterminated JSON bodies are refused at the boundary while a well-formed body still succeeds; lone-surrogate strings and array or object nesting bombs get a clean 400 over HTTP, raise at the parser, at the write seam and in the demo loader; a ported and a portless spelling of one path are retained and exported as distinct identities while default-port and case variants deduplicate and malformed ports are refused; payloads with extra fields and unknown operations are refused whole; mixed-case handle aliases deduplicate to one lowercase creator; percent-encoded, trailing-slash and mixed-case spellings of one path canonicalize to one identity while dot, empty and malformed segments and internationalized hosts are refused; control characters in text fields are refused while newlines and tabs pass; a directory or link at the database path is refused; a database overwritten in place, renamed away and re-pointed, or swapped between the startup check and the open is refused with 503 on every operation while the desk's own database resumes when it returns; a text file and a non-desk database are refused at startup; and a pre-identity desk database is adopted once and then bound. Hosted workflow status is reported separately and is never inferred from the local run; this carrier adds no workflow file.

## Exact tested Git blobs

| Path | Blob | Bytes |
| --- | --- | --- |
| `revenue/hive/creator-reward-campaign/.gitignore` | `7105972d3fe567427665913c13239fa793106bdf` | 41 |
| `revenue/hive/creator-reward-campaign/README.md` | `45a70d6f585b651c0e7d0ab350542fad92eb52fd` | 13180 |
| `revenue/hive/creator-reward-campaign/example.json` | `0d196ac3f909d1100320c30df1fcbc0e1791714c` | 5136 |
| `revenue/hive/creator-reward-campaign/index.html` | `1476e57b8b77919db69d2dfdaeb8725505ee51c0` | 23360 |
| `revenue/hive/creator-reward-campaign/server.py` | `de252a7dc31861b6637786c593b8102001a5dcc8` | 52805 |
| `revenue/hive/creator-reward-campaign/test_desk.py` | `d3b4c3a461c15cc5ac71ed9432b8e23073e5b3a6` | 59203 |

## Fresh-main collision audit

At `main@ec574a43d0de3957996a9e0bb325bbbee46836f0`, `main@ccab91f74dfec13e1dcb8228b422e044fbc19e08`, `main@e2626200eb09091c049018eab8ea147548323527`, `main@f21cbbe1fb42daab2c3056399c41036322741488`, `main@8ef24440dd444fb2c18b4a8b55a4bc1ad2e0829a`, `main@c9cd388e18c7deac1c9f0bd41ef3ce12be97529e` and `main@aeab59035ef1a3246744d17836488a763fecc1b3` the directory `revenue/hive/creator-reward-campaign/` is absent from the main tree, and no `p/` path on main references `creator-reward` or `bm-hive-20260908-021`. Publication touches only the seven additive paths in `scope`; no existing path is edited; no force-push; the final head is a two-parent rejoin onto literal main with a clean dry merge.

## Coordination

- TAKE receipt in #delegations, 2026-09-16 19:09:30 EDT (`p1789600170490129`), naming these exact new paths and claim base `main@607114ee3ce79ecb39a29e5534ea820a2cb4a61d`.
- In-thread claim under the demand post in #hive-media-builds (`p1789602967551629`).
- Review request in #awaiting-merge (`p1789604606442299`); review `5229732060` (Aegis-Z) on head `3fad379a` consumed by the first successor (code-owned opaque-reference grammar, canonical-only URL retention, payload digests); review `5229832111` on head `9e9d790c` consumed by the second successor (separator-complete phone, SSN and EIN shapes, digit-only rule, hashed and validated operation ids, handle digit checks, metric allow-list); review `5229922246` (ZHA-H6Q4) on head `ca189147` consumed by the third successor (host-aware URL identity projection with YouTube ids retained and other query material refused, loopback-only binding in code, bounded body drain with hardened `Content-Length` handling); the fourth successor adds the strict JSON boundary (duplicate keys and non-finite constants refused for request bodies and the demo script); review `5230094867` on head `cf4b4620` is consumed by the fifth successor (authority-preserving URL identity with validated ports and bracketed IPv6, Unicode-scalar string enforcement at ingress and at the write seam, nesting-safe parse and encode); the sixth successor adds exact per-operation field sets, case-insensitive handles, ASCII hosts with canonical path segments and percent-encoding, control-character bounds on text, and regular-file custody for the database path; review `5230491665` on head `a391e2d0` is consumed by the seventh successor (connection-bound database custody: a 64-bit identity minted into the SQLite header, proven through every connection before any statement, substituted databases answered 503).
- Successor review request and merge readback are posted in #awaiting-merge and the demand thread.

## External boundary

No brand, creator, or platform contact; no platform posting or metric reads; no payment provider call, transfer, funds held, invoice, or credential; no subscription sale; no revenue asserted. `LOCAL_HANDOFF_ONLY_NOT_PAID` is stamped on state, handoff records, and exports. Every brand, creator, URL, and metric in `example.json` is fictional.
