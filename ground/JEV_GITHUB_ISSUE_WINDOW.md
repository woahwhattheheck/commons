# GitHub issue-update window + gap minute

Refs #16537.

This adapter records two coverage facts without claiming a full GitHub census:

1. The explicit 19:24 UTC gap minute stays `LOWER_BOUND` with zero items read.
2. A later issue-update window (the post-20:06 slice) is compiled from provider `updated_at` rows into the landed connector-projection packet.

Run:

```text
python -m integrations.command_center.jev_github_issue_window packet.json
```

The packet schema is `commons.jev_github_issue_window/v1`. Incomplete pages stay `has_more=true`. The gap source never becomes complete merely because a later window was read.
