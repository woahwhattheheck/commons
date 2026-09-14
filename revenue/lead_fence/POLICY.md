# Mandatory outbound fence policy

This policy exists because an outbound campaign can be damaged by two otherwise-correct agents independently contacting the same lead within the same few seconds.

## Hard gate

Any automated or agent-assisted outbound sender using Commons coordination **must fail closed** unless all of these are true:

1. The exact recipient identity has been resolved.
2. `lead_fence.py claim` returned exit code `0` and `ok=true`.
3. The returned `path` and `commit_sha` are captured with the outbound work item.
4. The message has not already transitioned to `SENT`.

A Slack message saying “claimed,” a local note, a search result, or a plan is not a fence receipt.

## Collision behavior

Exit code `3` is not an error to retry aggressively. It means another sender owns the lead or the lead was already contacted. Suppress the outbound action and move to another target.

Exit code `4` or `5` is also a no-send result. The fence being unavailable must never degrade into “send anyway.”

## Lease duration

The default `ACTIVE` lease is 30 minutes. Use a short lease that covers drafting plus sending. If a draft is abandoned, release it immediately. If the worker crashes, the lease may expire and be acquired by another actor.

`SENT` is terminal. Re-contact requires an explicit future protocol/version decision; it must not happen by waiting for the lease to expire.

## Privacy

Do not add raw recipient email addresses, phone numbers, names, or URLs to claim JSON. The deterministic fingerprint is sufficient for collision detection on this public repository.

## Receipt example

Store at least:

```json
{
  "lead_fence_path": "revenue/lead_fence/claims/ab/ab...json",
  "lead_fence_commit": "<git commit sha>",
  "lead_fence_generation": 1,
  "outbound_message_id": "<provider receipt after send>"
}
```

The provider message ID is populated only after successful delivery and should be kept in the private campaign record when it contains sensitive data.
