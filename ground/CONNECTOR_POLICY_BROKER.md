# Connector policy broker

`host/connector_policy_broker.py` is the repository-side policy layer for connector-backed GitHub and Slack writes. It is intentionally **not** a credential broker and it never receives vendor tokens. Its job is to turn a narrow JSON action request into a deterministic allow/HOLD decision before a connector write is attempted.

## Supported verbs

- `github.create_branch`
- `github.commit_files`
- `github.create_pull_request`
- `slack.post_message`
- `slack.upload_file`

Everything else fails closed. Requests use exact schemas: unknown fields are rejected rather than ignored. The broker accepts strict JSON only (no floats, custom objects, coercion hooks, or non-string object keys), canonicalizes the request and policy, and returns SHA-256-bound decision receipts that can be recomputed with `verify_decision`.

## Default security properties

A `Policy` is an application-layer boundary in addition to the provider's own OAuth/App permissions. It can restrict exact GitHub repositories, branch prefixes, repository path prefixes, Slack channel IDs, file counts/sizes, commit size, Slack message size, and Slack file size.

GitHub writes require a branch under an admitted prefix. Direct writes to the configured default branch are denied. Commit requests must carry an exact 40-hex `expected_head_sha` and `force` must be `false`, so the connector consumer can use optimistic concurrency instead of overwriting a moving ref. Workflow paths are denied unless a separately constructed trusted policy explicitly enables them. Approval is not a caller boolean: `workflow_approval_subject_sha256()` hashes the exact commit request (with its proof field cleared), and an elevated policy must retain that exact digest in `workflow_approval_sha256s`; changing the files, branch, head SHA, or correlation ID invalidates the approval.

Pull requests can be required to target the configured default branch and to remain drafts. Repository paths reject absolute paths, traversal, normalization ambiguity, backslashes, NULs, and duplicates.

Slack messages require an admitted channel ID and force link/media unfurling off. Slack file requests bind filename, exact byte length, and SHA-256 before the later upload URL/finalization sequence is invoked. Channel names are not policy identities; use immutable Slack channel IDs.

## Canary profile

`canary_policy(repository=..., slack_channel_id=...)` provides a deliberately narrow first-use profile:

- one repository;
- `agent-canary/*` branches only;
- `.connector-canary/*` files only;
- draft PRs only;
- one Slack channel ID;
- no workflow writes;
- small byte ceilings.

The policy engine itself performs no external side effects. A consumer should execute the connector action only after `decision.allowed is True`, then append the decision plus the provider's returned object ID/SHA/Slack timestamp to its own append-only audit sink. Never add raw credentials to either the request or the audit record.

## Minimal example

```python
from host.connector_policy_broker import Policy, authorize

policy = Policy(
    policy_version="prod/1",
    github_repositories=frozenset({"org/repo"}),
    github_branch_prefixes=("agent/",),
    slack_channel_ids=frozenset({"C0123456789"}),
)

request = {
    "action": "github.create_branch",
    "correlation_id": "agent-run-932",
    "repository": "org/repo",
    "branch": "agent/agent-run-932",
    "base_sha": "0" * 40,
}

decision = authorize(request, policy)
if not decision.allowed:
    raise RuntimeError(decision.code)
# Connector call happens outside this module.
```

## Evidence and limits

This module improves the reliability of the GPT-connected write surface by making intended resource/action authority explicit, deterministic, and testable. It does **not** provision a GitHub App, install Slack scopes, store/rotate OAuth secrets, create a remote append-only audit database, or modify provider administration settings. Those remain deployment responsibilities outside repository source.

Focused verification:

```bash
python3 -m unittest -v test_connector_policy_broker.py
python3 -O -m unittest -v test_connector_policy_broker.py
python3 -m py_compile host/connector_policy_broker.py test_connector_policy_broker.py
```

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Larger fixed engagements (separate product pages; checkout/intent stays there): [GGUF diagnostic · $12,000 / 10 days](../diagnostic.html) · [White Box pilot · $30,000 / 30 days](../commercial.html). Not remints of tip SKUs.

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite newbot-ground-md-live-cash-20260916-09 — do not remint. Cite grok-ground-md-larger-fixed-20260916-01.
