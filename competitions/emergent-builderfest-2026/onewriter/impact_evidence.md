# OneWriter impact evidence plan

Status: **MEASUREMENT PLAN — NO IMPACT CLAIMS YET**

The contest values business impact, but a plausible metric is not evidence. This plan defines what the deployed app should measure during authorized internal use before submission copy is upgraded from hypothesis to result.

## Measurement unit

The denominator is an **outbound intent**: one worker proposes one normalized organization × route × purpose × opportunity action. Provider outcomes are downstream facts, not the denominator.

## Evidence boundary

The bundled offline fixture contains trusted synthetic roles, timestamps, provider references, and human-event references. Those are sufficient to test OneWriter's state semantics and receipt binding, but they are **not external-event authentication**. Any real-world provider/human outcome used in an impact claim must come from the deployed system's authenticated backend/adapters and authoritative server timestamps. The receipt hash chain proves integrity of retained decision input; it does not prove an external event happened.

## Required counters

| Metric | Definition | Evidence source | Claim gate |
| --- | --- | --- | --- |
| Outbound intents observed | Unique proposed intents accepted into OneWriter | authenticated deployed event log | count directly |
| Collision attempts | Lease acquisitions denied because another lease is active | denied receipt `active_lease` | count directly |
| Collisions prevented | Same as above, provided the denied claimant did not later bypass the app | receipt + bypass review | require bypass check |
| Duplicate touches prevented | Acquisition denied after `SENT_DNR` backed by authenticated provider evidence | denied receipt `sent_dnr` + provider adapter evidence | require provider evidence |
| Stale lanes recovered | New lease acquired after backend-authoritative, time-valid stale expiry | system expiry + later lease receipt | count directly |
| Route failures separated | Authenticated provider bounce recorded `DEAD_ROUTE`, not buyer rejection | provider adapter evidence + receipt | require authenticated provider evidence |
| Human reopens | `SENT_DNR` reopened by authenticated human-source evidence | human-source evidence + receipt | require authenticated human evidence |
| Arbitration latency | lease-decision time minus proposal/claim time | authoritative server timestamps | report median + n only |

## Before/after design

Prefer a short prospective internal run rather than reconstructing unverifiable history.

1. Use an existing owner-approved baseline only if it already has trustworthy intent and duplicate-touch timestamps; otherwise label baseline `NOT AVAILABLE`.
2. During the OneWriter window, require workers on the selected lane to propose through the deployed app before external mutation.
3. Keep scope comparable: same team/channel family and the same time-window definition.
4. Report raw counts and denominators before percentages.
5. Exclude bypassed work, missing authenticated provider/human evidence, test/synthetic events, and after-the-fact imports from real-world outcome claims.

## Strong claims allowed only after evidence

Acceptable future language *if measured and source-authenticated*:

- "During the measured window, OneWriter observed **N** outbound intents and blocked **C** concurrent duplicate claims."
- "It also blocked **D** attempts against provider-evidenced SENT lanes and safely recovered **R** backend-expired leases."

The synthetic demo may instead say only that the deterministic fixture exercised those semantics; it must not present fixture references as verified provider/human events.

Do **not** translate prevented duplicates into invented dollars, customers saved, conversion lift, or revenue unless independently evidenced.

## Evidence packet for judges

Capture the deployed URL/build timestamp; screenshot/video of the synthetic collision demo; exported synthetic receipt chain with offline verifier result; separately an owner-cleared aggregate internal run with no private buyer identities; authenticated provider/human evidence-source description for any external-outcome metric; exact measurement window, denominator, exclusions, and app version/commit; and the statement that OneWriter does not itself send messages.

## Privacy boundary

Public contest evidence should use aggregate counts or synthetic routes. Never publish real lead names, direct email addresses, private Slack content, customer correspondence, payment details, or provider identifiers unless specifically cleared by the owner and appropriate for disclosure.
