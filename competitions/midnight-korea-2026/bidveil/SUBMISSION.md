# Midnight Korea Hackathon 2026 — BidVeil submission package

## One-liner

**BidVeil lets contractors prove they meet a buyer's qualification rules without revealing the sensitive evidence underneath.**

## What is novel

Most procurement tooling treats qualification as a document-transfer problem. BidVeil treats it as a predicate-proof problem. Requirements are public and versioned; contractor values remain private; only the exact requirement result is revealed. Opportunity-scoped commitments/nullifiers make proof reuse observable without creating a globally linkable contractor identifier.

## Midnight fit

The product is shaped around Midnight's selective-disclosure/ZK model: Compact circuit inputs are private by default, while explicitly disclosed receipt/nullifier state can be public. The chain scaffold demonstrates that split. The final sponsor-toolchain gate must compile and simulate the contract before submission.

## Demo assets

- `README.md` — product + reproducible local demo
- `DEMO_SCRIPT.md` — under-two-minute narration
- `THREAT_MODEL.md` — privacy and adversary boundary
- `fixtures/` — synthetic opportunity + private profile
- `bidveil/` — dependency-free deterministic semantic engine + CLI
- `tests/` — hostile suite
- `contract/bidveil.compact` — Midnight Compact integration scaffold
- `contract/README.md` — chain gate and known blocker

## Submission checklist

- [x] Product concept and privacy story implemented
- [x] Deterministic local demo implemented
- [x] Hostile replay/transplant/stale/tamper/type tests implemented
- [x] Private-value non-disclosure regression implemented
- [x] Compact source scaffold included
- [ ] Install/pin sponsor-supported Compact toolchain
- [ ] Compile `contract/bidveil.compact`
- [ ] Add Compact simulator tests and generated-artifact hashes
- [ ] Bind on-chain requirement digest to exact predicate definition
- [ ] Deploy to sponsor-supported local/dev/test network
- [ ] Record transaction/proof demo and public-safe video
- [ ] Register/enroll through organizer surface
- [ ] Submit repository/video through organizer surface
- [ ] Preserve organizer submission receipt

Unchecked items are external/toolchain gates. This document does not convert them into completed work.

## Prize / revenue truth

This is a competition engineering artifact only. There is no claim here of organizer acceptance, eligibility approval, finalist status, ranking, prize, payment, buyer acceptance, or revenue.
