# Hyperagent agent-event → Slack transcript pilot proof

This is the internal fulfillment-readiness artifact for the already-offered Hyperagent paid pilot. It is deliberately **provider-neutral and zero-network**: it does not call Hyperagent, Slack, Gmail, or any buyer system, and it carries no private Hyperagent data.

## What is proved

The package normalizes three intentionally heterogeneous synthetic backend event schemas (`stream`, `trace`, `envelope`) into deterministic logical transcript artifacts. Source identity is scoped to **backend + source run + source event**, so backend-local event IDs may safely repeat across distinct runs. The checked-in fixture contains **30 events** spanning exactly **6 logical transcript artifacts**. A clean replay is idempotent: the second full replay emits **0 new logical messages**, while a reused source identity with changed semantics fails closed as a conflict.

Mutating-action events are approval gated. An action is emitted only when one approval is current and binds the exact normalized run, action ID, and action generation. An action first held for missing approval can be retried later with unchanged event semantics when the exact current approval arrives. Missing, denied, stale, foreign-run, foreign-generation, or ambiguous approval evidence produces no transcript artifact for that action. Approval IDs are immutable across projector ingests.

Strict-input handling rejects duplicate JSON keys, non-finite numbers, bool-as-int controls, noncanonical UTC, malformed opaque IDs, and non-scalar Unicode before canonical UTF-8 hashing. CLI contract/resource errors return status 2 without a traceback or output artifact. Even when a message is admitted to the offline artifact, `external_send_authorized` remains `false`; this package never grants real Slack/provider send authority.

## Run the acceptance proof

```bash
python -m unittest -v \
  revenue.hyperagent_slack_transcript.test_adapter \
  revenue.hyperagent_slack_transcript.test_stateful \
  revenue.hyperagent_slack_transcript.test_public_surface
python -O -m unittest -v \
  revenue.hyperagent_slack_transcript.test_adapter \
  revenue.hyperagent_slack_transcript.test_stateful \
  revenue.hyperagent_slack_transcript.test_public_surface
python test_hyperagent_slack_transcript.py
python -m revenue.hyperagent_slack_transcript.cli \
  revenue/hyperagent_slack_transcript/fixture.json \
  /tmp/hyperagent-transcripts.json
```

Expected fixture invariant: `artifact_count == 6`, `message_count == 30`. The root `test_hyperagent_slack_transcript.py` bridge is discovered by the retained Commons CI battery and executes the focused suite in both normal and optimized (`-O`) modes; no dedicated active workflow is added.

## Commercial handoff

This is a product proof for a bounded paid pilot, not a free production deployment. A paid engagement can replace the three synthetic adapters with buyer-approved backend mappings while preserving the same acceptance contract:

1. backend + run + source-event identity and semantic conflict detection;
2. deterministic run/thread/message projection;
3. replay without duplicate logical messages;
4. exact action-generation approval binding before mutating-action projection;
5. deterministic artifacts and receipts suitable for buyer review.

Buyer/runtime owners retain credentials, production routing, deployment, data policy, Slack workspace administration, and human approval authority. The code makes no claim of buyer acceptance, contract, award, payment, settlement, or recognized revenue.

## Truth boundary

- Synthetic fixture only; no buyer/private event payloads.
- Offline artifacts only; no network calls.
- `external_send_authorized` is always false.
- No email, DM, support reply, Slack send, provider mutation, deployment, payment, or revenue recognition.
