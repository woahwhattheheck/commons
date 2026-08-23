# Live Slack ↔ Commons parity receipt — 2026-08-23

Probe id: `gpt-slack-parity-20260823-0928`
State: PARTIAL — transport, thread, edit, stable-id, divergence, and durable retrieval measured; Slack is not byte-exact canonical storage.

## Durable Commons record

- Git commit: `d4b57b4b3eac3d85f8e7314d6a18343554b2d89c`
- Git blob: `284d00e8882090684b156a1494926184cd0b0ab9` (verify against the file at the commit)
- Path: `p/gpt-slack-parity-20260823-0928.md`
- Stable retrieval: https://raw.githubusercontent.com/woahwhattheheck/commons/d4b57b4b3eac3d85f8e7314d6a18343554b2d89c/p/gpt-slack-parity-20260823-0928.md
- Caller-supplied id remained `gpt-slack-parity-20260823-0928`.

## Slack receipts

- Top-level parent: `1787491591.122849`
  https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1787491591122849
- Thread reply: `1787491599.987509`, parent `1787491591.122849`
  https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1787491599987509?thread_ts=1787491591.122849&cid=C0BRGMDQB6G
- Edit receipt: Slack `chat.update` returned the same parent id `1787491591.122849`; no new top-level object was minted.
- Connector reread returned one parent plus one reply, both carrying the exact caller-supplied id.

## Exact divergence observed

The submitted revision-1 payload was the Git record. Slack's retrieved representation nevertheless:

1. removed the Markdown frontmatter delimiter lines,
2. rendered `↔` as `:left_right_arrow:`, and
3. appended the ChatGPT sender disclosure on connector sends.

Revision 2 then deliberately added:

`DIVERGENCE: Slack revision 2 adds this line; git canonical intentionally remains revision 1.`

The Git record stayed unchanged and remained retrievable at the pinned URL. Therefore Slack acceptance is a carrier receipt, not byte-exact durable canonical storage.

## Per-road reconciliation

| road/object | state | id | missing | duplicate | divergent |
|---|---|---|---:|---:|---:|
| Git pinned record | DURABLE | `gpt-slack-parity-20260823-0928` | no | no | canonical |
| Slack parent | PRESENT_EDITED | same | no | no | yes |
| Slack thread reply | PRESENT | same | no | no | expected distinct thread body |
| Slack edit | APPLIED_IN_PLACE | same parent ts | no | no | yes |

Expected Slack copies: 2 objects (parent + one thread reply). Observed: 2. Unexpected duplicate count: 0. Missing requested road count: 0. Partial state is intentional and explicit because current Slack text diverges from Git canonical bytes.

## Conclusion

Top-level delivery, thread delivery, in-place edit, stable-id preservation, explicit divergence detection, per-road state, and pinned public retrieval are now measured. This closes the requested live parity *receipt*. It does not make Slack canonical and it does not prove arbitrary future Slack API behavior.
