# Compact integration gate

`bidveil.compact` is an intentionally small chain integration scaffold. It demonstrates the two core privacy properties needed by the judge story: predicate inputs are private circuit parameters, while only a receipt/nullifier becomes public; and each opportunity+requirement+subject secret derives a one-use nullifier.

It is **not yet a deployment artifact**. The build runtime used for this carrier had neither `compact` nor `compactc`, so no compile, proof-key generation, local devnet deployment, or Midnight transaction is claimed.

## Required chain gate

Use a Midnight-supported toolchain/environment and pin the version before submission. The source currently targets Compact language `0.23`, which matches the public `example-private-party`, `example-hello-world`, and current Preprod-era reference examples inspected during this build.

```bash
compact compile bidveil.compact managed/bidveil
```

Then add simulator tests that prove:

1. registered opportunity digest is required;
2. boolean/minimum private predicates reject false claims;
3. the exact same opportunity+requirement+subject secret cannot prove twice;
4. a different opportunity digest produces a distinct nullifier;
5. only the receipt/nullifier and explicitly disclosed identifiers reach ledger state.

## Deliberate blocker before production use

The prototype circuits accept the public predicate (`expectedValue` / `publicMinimum`) alongside a `requirementDigest`; they do **not yet mechanically recompute and bind that digest to the predicate definition on-chain**. A deployable version must either register the full normalized public requirement definition in ledger state or recompute its canonical Compact hash inside the circuit. Until then, the Compact source is a privacy-flow scaffold, not buyer-verifiable qualification authority.

The tested Python harness is deliberately separate: it provides deterministic product semantics and hostile tests, but its SHA-256 receipts are **not** represented as Compact `persistentHash` values or ZK proofs.
