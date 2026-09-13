# Travelers Agent Tool-Call Evidence Gate

Execution-free evidence compiler for a bounded synthetic/nonproduction AI-agent pilot. It turns a frozen policy plus tool-call lifecycle events into a deterministic PASS/HOLD receipt without executing any tool itself.

It binds exact run/call/event identity, tool+version, arguments SHA-256, policy SHA-256, mutating-call human approval, approval freshness, dispatch identity, idempotency key, observed output/effect evidence, retry semantics, and completion. Same-ID conflicting evidence HOLDs. Mutating UNKNOWN outcomes HOLD. A retry after an unknown external effect HOLDs. Multiple successful mutating attempts must resolve to one stable effect receipt.

A tool failure can still receive evidence PASS when its failure and independently observed no-effect receipt are internally complete; the gate reviews evidence integrity, not business success.

## Authority ceiling

`EVIDENCE_ONLY_NO_PRODUCTION_TOOL_AUTHORITY`

The package performs no production tool execution, provider mutation, credential use, customer-data access, deployment, insurance/financial decision, payment, or revenue recognition. Every emitted receipt carries those authority flags as `false`.

## Run

```bash
python -m unittest revenue.travelers_agent_toolcall_evidence.test_gate -v
python -O -m unittest revenue.travelers_agent_toolcall_evidence.test_gate -v
python -m revenue.travelers_agent_toolcall_evidence.acceptance
python -O -m revenue.travelers_agent_toolcall_evidence.acceptance
```

Compile a packet containing exactly `policy` and `events`:

```bash
python -m revenue.travelers_agent_toolcall_evidence.cli compile \
  --packet packet.json --evaluated-at 2026-09-13T13:55:00Z \
  --json-out receipt.json --markdown-out receipt.md
```

Verify by exact deterministic replay:

```bash
python -m revenue.travelers_agent_toolcall_evidence.cli verify \
  --packet packet.json --evaluated-at 2026-09-13T13:55:00Z \
  --receipt receipt.json
```

PASS exits 0. HOLD, malformed evidence, or replay mismatch exits 2.

## Commercial pilot shape

For a bounded **paid synthetic/nonproduction pilot**, freeze one customer-selected tool policy and synthetic fixture, run the customer's own harness outside this package, import the resulting evidence, and return deterministic PASS/HOLD plus hostile replay. The implementation intentionally leaves production integration and all customer authority outside the carrier.
