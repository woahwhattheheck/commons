# Judge demo script — ~100 seconds

**0–15s — problem**

“Every bid portal asks small contractors to spray the same sensitive insurance, revenue, workforce and certification evidence across counterparties. BidVeil flips that: reveal the qualification result, not the underlying dossier.”

**15–35s — public requirement generation**

Show `fixtures/opportunity.json`: insurance active, annual revenue >= 250k, service region IN/KY, security training current. Emphasize that this is public and version-bound.

**35–55s — private profile**

Briefly show that `fixtures/private-profile.json` contains synthetic private values, then close it. Run `prove`. Open the receipt and point out that `750000`, `US-IN`, issuer IDs, evidence digests, and the subject secret are absent.

**55–75s — privacy + anti-replay**

Show `subject_commitment` and `nullifier`: both are scoped to the exact opportunity digest. Explain that a real Compact proof checks the private predicate; the checked-in local harness only demonstrates deterministic semantics and therefore says `LOCAL_SEMANTIC_SIMULATION_NOT_ZK` in-band.

**75–90s — hostile path**

Change the insurance issuer to `fake-carrier` or revenue to `249999`; rerun. The first becomes `HOLD_WRONG_ISSUER`; the second becomes `NOT_QUALIFIED`. No soft fallback.

**90–100s — Midnight path**

Show `contract/bidveil.compact`: private circuit arguments, public receipt/nullifier, one-use nullifier set. State the remaining chain gate plainly: compile/simulator/deploy with sponsor tooling and bind requirement definitions mechanically on-chain before calling it deployed.
