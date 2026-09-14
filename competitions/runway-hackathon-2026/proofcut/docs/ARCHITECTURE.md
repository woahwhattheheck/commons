# Architecture and truth boundary

ProofCut compiles two different visual classes and never conflates them:

1. **Factual shots** — captions backed by one or more content-addressed evidence records. No generative provider is allowed to satisfy these claims.
2. **Generated connective shots** — abstract or stylistic transitions explicitly marked `runway-generated-connective-only`. Evidence and claim text are not injected into their prompts.

The compiler emits a canonical manifest hash. The render planner updates only generated shots with provider results and leaves factual provenance untouched.

The real Runway adapter is three-key fail-closed: `execute=True`, a positive credit ceiling, and `RUNWAYML_API_SECRET`. The default provider is deterministic and network-free.

For predictable preflight budgeting the adapter uses WAN 3.0 at 480p: current Runway pricing is 5 credits/second; supported duration is 2–30 seconds. The provider SDK remains optional.
