# Agent Failure Autopsy

Agent Failure Autopsy is a USD 29 diagnostic for people who use Codex, Claude Code, or another coding-agent harness heavily and need a specific answer after one failed run.

The buyer supplies one failure sentence, the harness and stack name, and at least one redacted transcript, log, or screenshot. Within one business day after usable evidence arrives, the buyer receives an evidence-linked run reconstruction, the first meaningful divergence, primary and contributing causes with calibrated confidence, an adversarial challenge of plausible alternatives, supported fix steps, and a replay or regression-prevention check.

The USD 29 price does not reduce analysis quality. The bounded unit is one failed run. Analysis, adversarial challenge, evidence fidelity, and report quality remain full-strength. Operator time is measured only to understand economics and never to truncate work.

One clarification round is included. If the artifacts still cannot support a defensible diagnosis after that round, the USD 29 is refunded. This offer does not include code implementation, repository access, production access, secrets, unredacted credentials, or guaranteed certainty.

Canonical terms are in offer.json. The payment URL is pending and is not claimed as minted or live here.

## Package contents

- intake.schema.json defines the private intake record and the exact evidence that starts the clock.
- report.schema.json defines the diagnostic or refund record.
- fulfillment.py validates cross-document evidence links, timing, adversarial challenge, review, and refund behavior.
- RUNBOOK.md gives transferable fulfillment steps.
- report-template.md is the buyer-facing writing template.
- examples contains a synthetic, redacted coding-agent failure and an evidence-linked draft report.
- ../../test_agent_failure_autopsy.py exercises the validator with positive and discriminating negative cases.

Actual buyer artifacts and reports stay in an owner-private delivery system. Do not commit them to this public repository. Only the synthetic example belongs here.

## Validate the example

    python revenue/agent_failure_autopsy/fulfillment.py validate \
      --intake revenue/agent_failure_autopsy/examples/intake.json \
      --report revenue/agent_failure_autopsy/examples/report.json \
      --evidence-root revenue/agent_failure_autopsy/examples

    python -m unittest test_agent_failure_autopsy.py

The synthetic report is deliberately PEER_DRAFT with operator time NOT_MEASURED. It demonstrates structure and evidence fidelity; it does not establish delivery time, review time, buyer satisfaction, sales, or revenue.
