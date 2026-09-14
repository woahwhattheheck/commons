# Agent False-Success Survival Proof

A dependency-free, offline evidence compiler for a specific agent failure mode: a transport looks successful while the payload is an HTML login/error page, malformed JSON, a JSON-RPC error, or an MCP tool error—and the client still tells the agent the call succeeded.

This is a real diagnostic product, not a mock transport. It consumes captured exchanges from the client/system under test, classifies the transport and MCP semantics independently, compares the client's recorded disposition, and emits a deterministic content-addressed proof. It does **not** call a live endpoint, use credentials, or contact a vendor.

## Decision model

A complete proof requires every family below. Missing one produces `HOLD_INCOMPLETE_MATRIX`; a hostile exchange reported by the client as success produces `FALSE_SUCCESS_DETECTED`; a complete matrix whose captured client behavior agrees with the policy produces `SURVIVED`.

- `HTTP_200_HTML`
- `HTTP_200_LOGIN_HTML`
- `HTTP_200_MISLABELED_HTML`
- `HTTP_NON_2XX`
- `JSON_RPC_ERROR`
- `MCP_TOOL_ERROR`
- `MCP_WRAPPED_HTML`
- `MALFORMED_JSON`
- `VALID_CONTROL`

`SURVIVED` is intentionally narrow. It means only that the supplied captured behavior matched this fixed policy over the required matrix. It is not a production certification, security certification, vendor endorsement, or proof that an uncaptured route behaves correctly.

## Why both raw and wrapped HTML matter

A reverse proxy can return raw `200 text/html`, but another layer can also wrap the same landing page in a syntactically valid JSON-RPC/MCP result. The classifier therefore inspects both the response bytes and MCP `result.content[].text`; a JSON wrapper cannot launder HTML into semantic success.

## Capture schema

The input is strict `agent-false-success-capture/v1` JSON. Unknown keys, duplicate JSON keys, non-finite numbers, bool-as-int aliases, noncanonical SHA-256/base64, duplicate case IDs, oversized bodies, malformed timestamps, and a declared family that the captured bytes do not actually demonstrate all fail closed.

Each case records only:

- stable case/family ID;
- HTTP status and content type;
- bounded response bytes as base64;
- the observed client disposition (`SUCCESS` or `ERROR`);
- SHA-256 commitments for the client-event evidence and source capture.

Published proof findings omit raw response bodies. They retain body/source/client-event digests, byte counts, semantic reasons, and the observed-vs-policy comparison.

## CLI

From the repository root:

```bash
python -m revenue.agent_false_success_survival demo \
  revenue/agent_false_success_survival/fixtures/synthetic_capture.json
```

Compile a proof create-exclusively:

```bash
python -m revenue.agent_false_success_survival compile capture.json --out proof.json
python -m revenue.agent_false_success_survival verify capture.json proof.json
```

The compiler refuses to overwrite an output. Input reads require a regular, non-symlink file and bind the opened inode during the read.

## Fixed commercial shape

**Same-Day Agent Survival Proof — $2,500 fixed scope — `PROPOSED_NOT_ACCEPTED`.**

Inputs: a bounded set of captured client exchanges covering the required matrix, client build/version, and content-addressed source/client-event evidence.

Deliverables: deterministic proof JSON, case-by-case false-success findings, replayable acceptance checks, and a concise remediation map keyed to the failed boundary (transport status, media type/body, JSON-RPC, MCP tool result, or wrapped HTML).

Acceptance tests: all required families are present and byte-valid; proof verification recomputes exactly; raw hostile content cannot be represented as accepted by policy; a valid structured control remains accepted.

Exclusions: no live production probing, credentials, customer data extraction, penetration testing, provider/account mutation, code deployment, SLA/compliance certification, or guarantee of uncaptured behavior. Any implementation/remediation work is separately scoped.

No issue, PR, email, silence, or technical finding constitutes buyer acceptance. Price stays a proposal until a counterparty explicitly agrees. Payment/cash/revenue remain literal provider facts only.

## SigNoz internal target overlay

`targets/signoz.json` maps public first-party evidence to this proof matrix. It is research/positioning evidence only and permanently carries `external_send_authorized=false`. Before any contact, re-read live Slack ownership plus mailbox/provider history and acquire a single-writer last-inch claim for the exact opportunity/target/thread.
