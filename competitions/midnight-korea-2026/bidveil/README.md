# BidVeil

**Private qualification. Public confidence. No document spraying.**

BidVeil is a Midnight Korea Hackathon 2026 carrier for privacy-preserving subcontractor qualification. A buyer publishes a bounded requirement generation; a contractor proves only the predicates necessary for that opportunity—insurance active, revenue above a threshold, region in an allowed set, training current—without disclosing the underlying values or source documents.

The checked-in zero-network harness is a deterministic semantic prototype. Its strongest state is `QUALIFIED` **inside local replay only**. It never claims an on-chain ZK proof, buyer acceptance, contract award, payment, or revenue.

## Why this problem

Procurement teams routinely ask contractors to email sensitive insurance, financial, identity, workforce, certification, and reference evidence to multiple counterparties. That creates unnecessary disclosure, stale copies, and replay risk. BidVeil's product boundary is selective disclosure:

- private claim values stay private;
- public requirement definitions are versioned and digest-bound;
- only requirement IDs plus `SATISFIED`/`UNSATISFIED`/`HOLD` state are revealed;
- a subject commitment is scoped to one exact opportunity generation;
- an opportunity-scoped nullifier gives a stable anti-replay identity without exposing the source secret;
- any malformed, stale, future, wrong-issuer, transplanted, or unknown evidence fails closed.

## Run the complete local demo

From this directory:

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
PYTHONPATH=. python -O -m unittest discover -s tests -v
rm -f /tmp/bidveil-receipt.json
PYTHONPATH=. python -m bidveil.cli prove fixtures/opportunity.json fixtures/private-profile.json \
  --at 2026-09-13T12:00:00Z --out /tmp/bidveil-receipt.json
PYTHONPATH=. python -m bidveil.cli verify-integrity /tmp/bidveil-receipt.json
PYTHONPATH=. python -m bidveil.cli verify-replay fixtures/opportunity.json fixtures/private-profile.json \
  /tmp/bidveil-receipt.json --at 2026-09-13T12:00:00Z
```

Expected terminal states:

- tests pass under normal and `python -O`;
- prove emits `decision=QUALIFIED` and `mode=LOCAL_SEMANTIC_SIMULATION_NOT_ZK`;
- integrity check emits `VERIFIED_INTEGRITY_ONLY`;
- private-source replay emits `VERIFIED_LOCAL_REPLAY`.

Open the receipt: it contains no private numeric/string claim values, no issuer IDs, no source evidence hashes, and no subject secret.

## Architecture

1. `fixtures/opportunity.json` — public requirement generation.
2. `fixtures/private-profile.json` — **synthetic demo-only private source**; a real client keeps this locally.
3. `bidveil/engine.py` — strict schema normalization, predicate evaluation, scoped commitments/nullifier, deterministic receipt.
4. `bidveil/cli.py` — create-exclusive receipt generation, integrity verification, and private local replay.
5. `contract/bidveil.compact` — Compact integration scaffold showing private circuit predicate inputs and one-use requirement nullifiers.
6. `contract/README.md` — exact chain gate and the unresolved predicate-definition binding blocker.
7. `THREAT_MODEL.md` — adversary model and fail-closed decisions.
8. `SUBMISSION.md` / `DEMO_SCRIPT.md` — judge-facing package.

## Hash domains

The Python prototype uses canonical JSON + SHA-256 for deterministic local engineering receipts. The Compact scaffold uses Compact-native `persistentHash`. **They are intentionally not represented as cross-runtime equivalent.** A chain-ready build must add authoritative Compact encoding test vectors before mapping one hash universe into the other.

## Midnight integration status

`contract/bidveil.compact` targets Compact language `0.23` from current public examples. This session's runtime has no `compact` or `compactc`, so `COMPACT_COMPILE_NOT_RUN` is a real blocker. No chain deployment, wallet, proof server, transaction, or hackathon submission is claimed.

The next chain gate is documented in `contract/README.md`; it must be completed in an environment with the sponsor toolchain before describing BidVeil as a Midnight-deployed DApp.

## Competition truth

Engineering carrier: `MIDNIGHT-KOREA-BIDVEIL-ZBQYN7R5-20260913` / Commons issue #14191. Competition registration/submission, organizer acceptance, ranking, prize, payment, and revenue are separate external facts and are not inferred by this repository.
