# Commercial scope — Hotel Room-Turn Evidence Pilot

## Fixed offer

**$2,500 USD — one property, seven calendar days.**

The pilot demonstrates a bounded evidence-to-room-readiness workflow using agreed de-identified fixtures. A room is not marked `READY` until housekeeping, maintenance, and a named manager all provide fresh, non-conflicting evidence for the same turnover generation.

## Included

- agree one property identifier, room roster, turnover IDs, named managers, and freshness windows;
- map de-identified housekeeping / maintenance / manager-release evidence into the strict input contract;
- exercise clean, blocked, missing, stale, conflicting, and wrong-turn cases;
- deliver deterministic JSON decision receipts plus a human-readable acceptance sheet;
- deliver the policy/evidence schema, verifier, hostile regression suite, and retained policy/report receipt procedure;
- one findings/review session for the pilot output.

## Explicitly excluded

- PMS or guest-data production access;
- production credentials;
- writing room status into a PMS;
- dispatching housekeeping or maintenance personnel;
- guest communications, charges, refunds, or booking changes;
- production deployment or recurring managed service;
- claims that this compiler authenticates a hotel system of record.

Any production integration, live-system access, expanded property scope, or recurring operation requires a separately written scope and price.

## Buyer acceptance hypothesis

The pilot is accepted when the agreed frozen test set and buyer-approved de-identified evidence set each produce exactly one deterministic `READY` or `BLOCKED` decision per in-scope current turnover, every `READY` binds all three required evidence classes to that turnover, every hold names its reason, input reordering is deterministic, and tampered/resealed outputs fail against the separately retained receipt.

## Payment boundary

This file is a commercial scope template, not evidence of buyer acceptance, authorization, payment, cash, or recognized revenue. The portfolio checkout order recommends manual capture after written scope/acceptance confirmation; the payment-link mint itself is outside this carrier.
