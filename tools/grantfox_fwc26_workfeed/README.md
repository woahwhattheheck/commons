# GrantFox FWC26 workfeed compiler

This is an **offline intake compiler** for the Swarm ZZ GrantFox/FWC26 queue. It turns supplied GitHub issue snapshots into a deterministic JSON + Markdown workfeed without claiming work, assigning contributors, contacting maintainers, or pretending that discretionary campaign rewards are guaranteed payment.

## Safety / authority boundary

The compiler is advisory only. It never:

- calls GitHub, GrantFox, Slack, wallets, or payment systems;
- claims or assigns an issue;
- treats `MAYBE REWARDED` / “may be rewarded” as a guaranteed amount;
- converts a campaign pool mention into issue-specific compensation;
- overwrites an existing output directory.

A candidate is campaign-eligible only when all three labels are present:

- `GRANTFOX OSS`
- `MAYBE REWARDED`
- `Official Campaign | FWC26`

Open + unassigned issues become `READY` only when the supplied snapshot also contains no observed claimant comments and no open pull requests. If the issue text describes a required application/assignment step, it becomes `CLAIM_REQUIRED`; supplied claimant/PR observations become `CLAIMED_OR_PR_OPEN`. Assigned and closed/mislabeled issues remain visible but cannot enter `READY`.

## Input

JSON array or JSONL. Minimal object:

```json
{
  "repository": "StableRoute-Org/Stableroute-backend",
  "number": 551,
  "title": "sliding-window rate limiter scoped per tenant/API key",
  "url": "https://github.com/StableRoute-Org/Stableroute-backend/issues/551",
  "state": "open",
  "labels": ["GRANTFOX OSS", "MAYBE REWARDED", "Official Campaign | FWC26"],
  "assignees": [],
  "claimant_comments": [],
  "open_pull_requests": [],
  "body": "Part of the campaign — this task may be rewarded. Run `npm test`."
}
```

`labels` may also contain GitHub-style objects with `name`; `assignees` may contain objects with `login`. `claimant_comments` (or `claim_comments`) and `open_pull_requests` (or `open_prs`) are optional upstream coordination inputs; any supplied claimant or open PR blocks `READY`. `coordination_claims` (or `swarm_claims`) records active internal owners from Slack/workboard evidence and produces `SWARM_TAKEN`, preventing another seat from treating the same packet as free. `observed_at` (or `snapshot_observed_at`) may carry the timezone-aware evidence timestamp.

## Run

```bash
python -m tools.grantfox_fwc26_workfeed.compile issues.json --out-dir /tmp/gfox-feed

# Optional hard freshness floor: missing/older observed_at snapshots are not routable.
python -m tools.grantfox_fwc26_workfeed.compile issues.json --out-dir /tmp/gfox-feed-fresh \\
  --fresh-after 2026-09-19T17:30:00-04:00
```

Outputs:

- `queue.json` — schema-versioned machine-readable feed with explicit false authority flags.
- `QUEUE.md` — human-readable queue with status, reward-evidence class, security-sensitive marker, and extracted local verification commands.

The output directory is create-exclusive; reruns must use a new directory so an older evidence packet cannot be silently replaced.

## Tests

```bash
python -m unittest discover -s tools/grantfox_fwc26_workfeed/tests -v
python -O -m unittest discover -s tools/grantfox_fwc26_workfeed/tests -v
```

The tests cover campaign label gating, assignment state, claim-step detection, observed claimant/open-PR blocking, active swarm-owner collision blocking, timezone-aware freshness floors, discretionary-vs-explicit reward evidence, command extraction, security-sensitive marking, hostile duplicate keys, malformed coordination fields, invalid URLs/issue numbers, authority flags, and create-exclusive output.
