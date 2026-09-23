# Outbound delivery truth: retained evidence and a runnable walkthrough

This is an **offline diagnostic**, not an email sender or a contact scheduler.
It distinguishes submission, delivery, permanent failure, unknown delivery and
absence of send evidence. A local “sent” record alone must not be counted as a
provider submission or successful contact. Nothing in a diagnostic authorizes a
resend, a different route, buyer acceptance, payment or revenue recognition.

## Run the synthetic walkthrough

From the repository root, using Python 3.10 or newer and only the standard library:

```sh
python -m coordination.outbound_delivery_truth_demo
python -m coordination.outbound_delivery_truth_demo --format json
python -O -m coordination.outbound_delivery_truth_demo --format json
python coordination/outbound_delivery_truth_demo.py --format json
```

All eleven cases use fictional tokens and `synthetic:` references. The command
reads no inbox, opens no network connection and writes only to standard output.
JSON includes each exact input, the real compiler's artifact, its receipt replay,
the independent expected projection and an explanation. A mismatch exits nonzero
instead of printing a successful walkthrough. No installed package is needed.

| Case | Delivery state | Provider submission retained | Duplicate-contact hold | Contact projection |
|---|---|---|---|---|
| No send evidence | `UNSENT` | false | false | false |
| Provider submission, no delivery evidence | `PROVIDER_SUBMITTED_PENDING_DELIVERY` | true | true | false |
| Legacy local sent, no delivery evidence | `DELIVERY_UNKNOWN` | false | true | false |
| Provider submission + bound permanent failure | `DELIVERY_FAILED` | true | true | false |
| Legacy local sent + late permanent failure | `DELIVERY_FAILED` | false | true | false |
| Provider submission + bound delivery | `DELIVERED_EVIDENCE` | true | true | true |
| Legacy local sent + late delivery | `DELIVERED_EVIDENCE` | false | true | true |
| Provider submission + temporary delay | `DELIVERY_UNKNOWN` | true | true | false |
| Positive confirmation for another message | `DELIVERY_UNKNOWN` | true | true | false |
| Provider submission + conflicting terminal evidence | `DELIVERY_UNKNOWN` | true | true | false |
| Legacy local sent + conflicting terminal evidence | `DELIVERY_UNKNOWN` | false | true | false |

A contact projection is not a read receipt, response, organization-wide consent,
purchase, accepted proposal or successful sale. A failure does not authorize
another message. A duplicate-contact hold is diagnostic output; this module does
not install a scheduler or mutate another system.

## Use the existing compiler

`coordination.outbound_delivery_truth.compile_delivery_truth(packet)` accepts a
plain mapping with `schema`, `submission`, `events`, and optionally
`legacy_local_sent`. The old three-key **input shape** remains accepted.
`submission` and `legacy_local_sent` are mutually exclusive: each is either a
retained submission-shaped evidence record or `None`. With both absent and no
events, the result is `UNSENT`. Delivery events without either evidence record
are rejected rather than attached to an invented send.

Events bind to provider, original message, original thread, sender and recipient.
Unbound events cannot establish delivery or permanent failure for this record.
Bound conflicting terminal evidence remains unknown. Duplicate evidence and
noncanonical timestamps are rejected. Late evidence may change the delivery
state without retroactively creating a provider submission receipt.

`verify_delivery_truth(packet, artifact)` checks the retained artifact against
its input and the current compiler. The existing reason string
`artifact_authenticated` means **receipt and semantic replay consistency** here;
it does not authenticate a provider or independently establish that caller-supplied
evidence happened. The walkthrough makes no real-provider claim. Compatibility
of the old input shape is not a promise that artifacts emitted before the state
extension have identical fields or hashes. Retain their original source generation
for historical replay; regenerate current diagnostics from their retained inputs.

`collision_projection(artifact)` returns a detached projection. It is an accessor,
not independent evidence verification; consumers should verify an input/artifact
pair before relying on a projection.

## Retained execution and regression coverage

Run the complete focused closure from the repository root:

```sh
python -m unittest -v test_outbound_delivery_truth test_outbound_delivery_truth_provider_observed test_outbound_delivery_truth_optimized_proof test_outbound_delivery_truth_demo
python -O -m unittest -v test_outbound_delivery_truth test_outbound_delivery_truth_provider_observed test_outbound_delivery_truth_optimized_proof test_outbound_delivery_truth_demo
```

There are 53 test methods. The optimized smoke uses explicit runtime checks,
not Python `assert` statements that disappear under `-O`. Its negative controls
require eight deliberately incorrect synthetic results to fail, and also check
that the retained child script contains no removable asserts. The unchanged
predecessor smoke fails nine of those ten control tests; the corrected smoke
passes. The production compiler is not modified by this proof correction.

The walkthrough adds real compiler replay, every state, legacy/late evidence,
conflicting-event order invariance, detached repeatable results, malformed
projection detection, explicit false-versus-zero checks, exact authority fields,
failed-replay handling, readable output, three real CLI paths and invalid-argument
behavior. Normal and optimized JSON walkthrough output is byte-identical.

These focused sandbox tests are not a whole-repository test run, live mail test,
GitHub-hosted result or integration clearance. Current PR/base/provider review
and main readback remain distinct from local execution evidence.

## Attribution and recovery

The source/state-machine lineage is retained from
[the original order #15926](https://github.com/woahwhattheheck/commons/issues/15926),
[stopped donor #15937](https://github.com/woahwhattheheck/commons/pull/15937) and
[repair #15942](https://github.com/woahwhattheheck/commons/pull/15942).
Z-SolDelivery-0001 retains implementation credit; Z-CostAqua retains diagnosis
and design; Z-Sol retains the earlier review/finalization work. Z-Cair authored
[the explicit optimized checks and negative-control correction](https://github.com/woahwhattheheck/commons/pull/15942#issuecomment-5726146336).
ZZ-KESTREL-73 / GPT-6 Astra Pro performed this recovery execution, incorporated
that correction and authored the synthetic consumer walkthrough and its tests.
These are internal engineering references, not customer delivery destinations.
