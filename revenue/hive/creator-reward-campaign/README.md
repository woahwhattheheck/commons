# Creator Reward Campaign Desk

A runnable, standard-library Python workspace for administering creator reward campaigns: a brand publishes a brief with rights/usage terms, an asset library, a budget cap and an explicit reward rule; consenting creators submit content links; an operator reviews eligibility; approvals produce exactly one calculated payable per submission inside the budget cap; calculated payables are handed off as a local, idempotent payout request file for a separately authorized operator; settlement is recorded afterwards by reference. The interface is included; no build step, external model, payment provider call, platform API, or package installation is required.

This is the implementation and first synthetic sample for Hive demand `bm-hive-20260908-021`. The demand's proposed offer, **$99/month campaign software plus a proposed 5% administration fee**, is a hypothesis: `PROPOSED_NOT_ACCEPTED`. No brand commission, creator payout, platform posting, provider account, subscription sale, or revenue is asserted by this package.

## Run

From this directory, with Python 3.10 or newer:

```sh
python3 server.py --db creator-reward.sqlite3 --demo
```

Open `http://127.0.0.1:8766`. The optional `--demo` flag replays `example.json`: one fictional brand, three consenting fictional creators, one open campaign with a `50000` minor-unit budget and a `20000`-per-approval rule, two licensed assets, four submissions, three reviews that produce two full payables and one partial payable that exhausts the budget, one rejection for a missing disclosure, and one local payout handoff. Restarting with the same database and flag replays the recorded operations instead of duplicating them. Without `--demo`, start with an empty workspace. Database files are runtime data and should not be committed.

`--db`, `--host`, and `--port` are configurable. The database path is checked once at startup: it must be a regular file, existing or new; links, directories and special files are refused, a file that is not a SQLite database is refused, and a SQLite database that is not a desk database is refused and left untouched; the CLI exits 2. This is a startup shape check, not an ongoing custody guarantee: the desk opens its database by pathname for each operation, as SQLite itself does for its journal, so the directory that holds the database is part of the operator's trusted environment, and a process able to rename or replace files there while the desk runs is outside this desk's threat model. `--host` accepts loopback addresses only (`127.0.0.1`, `::1`, `localhost`); the server refuses any other bind target in code, because the desk has no remote authentication and is not served on other interfaces in this version. Everyone with access to the machine's loopback interface shares the complete operator view; this is a single-operator desk, not a multi-tenant portal. Request bodies are bounded at 5 MB: bodies within the bound are read in full before any reply, while malformed, missing or oversized `Content-Length` values are refused with a closed connection. JSON is parsed strictly: duplicate object keys, `NaN`/`Infinity` constants, strings that are not valid Unicode scalar values (lone surrogates) and nesting bombs are refused with a clean 400 rather than silently resolved, in request bodies and in the demo script alike. The browser needs modern JavaScript and a secure context (localhost or HTTPS) for operation IDs.

## Complete the sample workflow

1. Create a brand, then add creators with the date their consent was recorded and an opaque payout route reference issued by the payout system of record. Handles are case-insensitive and stored in lowercase, so one creator has one spelling. Payout route references and settlement references must satisfy the code-owned opaque-reference grammar in `server.py`: up to 80 ASCII letters, digits, dots, underscores, colons, slashes or hyphens, refusing email, link, `www.`/`label.tld` host, `mailto:`/`tel:` shapes, phone, SSN and EIN shapes under every admitted separator (`-`, `.`, `:`, `/`), grouped card digits, standalone runs of nine or more digits, any run of thirteen or more digits, values with nine or more digits and no letters, IBAN shapes, credential keywords, well-known secret prefixes and token-shaped runs of 32 or more alphanumerics. Creator handles pass the same digit-shape checks. The desk stores no bank, card, or platform credential; its write receipts keep only SHA-256 digests of the idempotency key and the request payload, and the key itself must be an ASCII identifier. Owner-entered metrics are a fixed allow-list of non-negative integer counts (`views`, `likes`, `comments`, `shares`, `saves`). Free-text fields (brief, rights terms, asset content and licenses, review notes) are operator-authored content and are stored as entered.
2. Create a campaign as a draft: brief, rights/usage terms, currency, budget cap in minor units, a reward rule, eligible platforms, disclosure tag and the posting window. Add asset files (`.md`/`.txt`) with a license note. Open the campaign.
3. Record submissions: campaign, creator, platform, content URL, posted date, whether the disclosure is present, whether the creator accepted the rights terms. Only the canonical public form of the URL is retained and returned: scheme, lowercased ASCII host (internationalized hosts in their punycode form), an explicit non-default port (part of the content identity; default ports are folded away, malformed ports are refused, IPv6 hosts stay bracketed) and a canonical path (dot and empty segments refused, percent-escapes uppercase, unreserved octets literal, trailing slash dropped), with userinfo refused, fragments dropped, and known tracking or share parameters (`utm_*`, `fbclid`, `si`, `igsh`, and similar) dropped. Query material survives only where a code-owned projection names it as the content identity: YouTube video ids are kept and normalized to `https://www.youtube.com/watch?v=<id>` from watch, `youtu.be`, shorts, live and embed forms. Any other query material (signed or tokenized links, unknown parameters) is refused with an exact reason rather than silently stripped, so a secret never enters the desk and a content identity is never lost. The same content URL is refused twice in one campaign regardless of case, trailing slash, tracking parameters or YouTube link form, and the duplicate key is the retained value.
4. Review each submission. Approval requires the campaign to be open, the disclosure present (when required), the rights terms accepted (when required), and the post inside the campaign window; otherwise the desk refuses the approval with the exact reason and the submission stays reviewable. Rejection always works and records the note.
5. On approval the reward is computed from the rule and the owner-entered metrics, then applied against the remaining budget inside one transaction: full payable, partial payable (`APPROVED_PARTIAL_BUDGET`, only when the rule allows partials), `APPROVED_BUDGET_EXHAUSTED` (no payable), or `APPROVED_NO_REWARD` (rule produced zero). A submission can be reviewed once, so there is at most one payable per submission.
6. Choose **Hand off calculated payables** to write one local handoff record listing every calculated payable with an idempotency key per payable. Nothing is transferred; a separately authorized operator submits those requests to the payout provider of record, then records the external settlement reference on each payable.
7. **Export ZIP** returns `campaign.json`, `submissions.csv`, `payables.csv`, `payout_handoff.json`, the licensed assets, and a README stating `LOCAL_HANDOFF_ONLY_NOT_PAID`.

## Reward rules and money

All money is integer minor units. `FIXED_PER_APPROVED` pays `amount_minor` per approved submission. `PER_THOUSAND_VIEWS` pays `views * rate_minor_per_thousand // 1000`, capped at `cap_minor`, and nothing below `minimum_views`; views are owner-entered verified metrics at review time, not platform API reads. The proposed administration fee is `5%` of each payable, rounded half up, computed for the proposal only. Budget arithmetic is `budget_minor - sum(payables)` and is enforced inside the approval transaction, so concurrent approvals for the last remaining budget have one winner.

## Persistence and concurrent edits

SQLite stores brands, creators, campaigns, assets, submissions, payables, handoffs, and write receipts. Unique indexes enforce one creator handle, one asset name per campaign, one content URL per campaign, and one payable per submission. Optimistic versions reject stale writes rather than overwriting another edit.

Each JSON mutation includes an `operation_id` (an ASCII identifier of up to 200 characters) and exactly the fields its operation defines; a payload carrying any other field is refused as a whole rather than partially applied. Text fields accept printable text with newlines and tabs; other control characters are refused. Repeating the exact operation and payload returns the original result without another mutation, including after reconnect or process restart. Reusing the ID with a different payload is rejected. The desk retains only SHA-256 digests of the id and the payload, never the request text. The browser keeps an unacknowledged payload in that tab's session storage and offers **Retry pending edit**; do not change a payload when retrying it.

## API

`GET /api/state` returns the shared workspace with per-campaign budget totals. `GET /api/export/{campaign_id}` returns the ZIP. JSON POST endpoints, each taking a unique `operation_id`:

- `/api/brand/create`: `name`.
- `/api/creator/create`: `handle`, `consent_on`, `payout_route_ref`.
- `/api/campaign/create`: `brand_id`, `title`, `brief`, `rights_terms`, `currency`, `budget_minor`, `rule`, `eligibility`.
- `/api/campaign/action`: `id`, `version`, `action` of `open`, `close`, or `asset` (`name`, `license`, `content`).
- `/api/submission/create`: `campaign_id`, `creator_id`, `platform`, `url`, `posted_on`, `disclosure_present`, `rights_accepted`.
- `/api/submission/review`: `id`, `version`, `decision` of `approve` or `reject`, `note`, `metrics` (integer counts from `views`, `likes`, `comments`, `shares`, `saves`; `views` drives the per-thousand rule).
- `/api/payable/handoff`: `campaign_id`.
- `/api/payable/settle`: `id`, `version`, `settlement_ref`.

The imported `Desk` class exposes the same implementation for local integration; the HTTP boundary adds nothing.

## Boundaries

The desk records what an operator enters, minus the shapes it refuses: payout route and settlement references pass the opaque-reference grammar before they are stored, content URLs are kept only in canonical public form, and write receipts hold payload digests rather than request bodies. It does not contact brands or creators, post or verify content on any platform, read platform metrics, execute or schedule transfers, hold funds, issue invoices, interpret contracts or advertising-disclosure law, or assert that any payable is owed. `LOCAL_HANDOFF_ONLY_NOT_PAID` is stamped on state, handoff records, and exports.

## Validation

```sh
python3 -W error::ResourceWarning -m unittest -v test_desk.py
python3 -O -W error::ResourceWarning -m unittest -v test_desk.py
python3 -m py_compile server.py test_desk.py
```

The suite uses real temporary SQLite files, threads, a process-style database reopen, ZIP readback, and a real HTTP server/client. It covers one payable per submission, partial and exhausted budget states, a concurrent race for the last budget with one winner, per-thousand math with cap and minimum, integer fee rounding, duplicate content URLs across creators and URL forms, eligibility refusals, platform/consent/campaign-state gates, idempotent handoff and settlement by reference, stale versions, exact operation replay, concurrent identical retries, restart persistence, asset naming, malformed inputs, ZIP contents, the idempotent demo load, HTTP status codes, and the data-minimization boundary: card, account, IBAN, email, link, host, phone, SSN and EIN (under every admitted separator), credential-keyword, secret-prefix and token-shaped payout route and settlement references are refused, identity-number handles and free-form metric fields are refused, secret-shaped operation ids are retained only as digests, signed or tokenized content URLs are refused while tracking parameters are dropped and YouTube identities survive canonicalization and dedupe across link forms, and the retained bytes (state JSON, SQLite files, ZIP members, write receipts) are searched to prove none of those values entered the desk; loopback-only binding at the server and CLI; and raw-socket checks that malformed, missing, oversized and short request bodies and unknown routes receive clean JSON replies. Browser interaction is exercised through the HTTP API; a visual pass in a real browser is not claimed by these tests.
