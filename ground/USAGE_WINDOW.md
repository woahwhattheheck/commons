# Active usage-window control

`host/usage_window.py` keeps one local coordinator ledger for the temporary
high-burn window. It records actual observations of the shared weekly plan meter
for Work, workspace agents, and Excel. Ordinary chat usage is a different meter.
The fixed scope is `codex-work-weekly-plan`.

This tool does not read account pages, fetch quota, schedule tasks, start agents,
or invent percentages. The coordinator supplies observations from a legitimate
authenticated reading method. Keep the ledger in the private cloud session,
outside the public repository; evidence should describe the visible result and
source without including cookies, credentials, or private page contents.

## Start and observe

Choose one stable expected account identifier. Initialize the window once with
the actual observation timestamp, including timezone. Supply the next ordinary
weekly reset time only when it is known from the account's usage information.
The ordinary reset that already occurred is not the special outage reset.

```sh
python3 host/usage_window.py --state /tmp/usage-window.json init \
  --account "$EXPECTED_ACCOUNT" --at "$OBSERVED_AT"
```

Record a real percentage only after checking the account and weekly meter scope.
`--trusted --account-specific` declares what the caller actually verified; these
flags do not perform authentication and do not turn general platform news into
account evidence. The source and evidence fields are mandatory.

```sh
python3 host/usage_window.py --state /tmp/usage-window.json observe \
  --account "$EXPECTED_ACCOUNT" --meter-scope codex-work-weekly-plan \
  --at "$OBSERVED_AT" --kind meter --remaining-percent "$ACTUAL_REMAINING" \
  --ordinary-reset-at "$ACTUAL_NEXT_WEEKLY_RESET" \
  --source "$OBSERVATION_SOURCE" --evidence "$OBSERVATION_EVIDENCE" \
  --trusted --account-specific
```

When the page is signed out, unavailable, or does not expose this meter, append an
`unavailable` observation with the actual timestamp and reason. Omit percentage
and trust flags. Mode remains unchanged and the last real reading remains visible.

```sh
python3 host/usage_window.py --state /tmp/usage-window.json observe \
  --account "$EXPECTED_ACCOUNT" --meter-scope codex-work-weekly-plan \
  --at "$OBSERVED_AT" --kind unavailable \
  --source "$OBSERVATION_SOURCE" --evidence "$OBSERVED_FAILURE"
```

For a trustworthy notice explicitly confirming the special reset was applied to
this exact account, use `--kind explicit_reset_applied --trusted
--account-specific` and retain its actual source and evidence. A public promise,
scheduled reset notice, or generic service-restored notice does not qualify.

Record public rollout reports as `--kind public_signal`, with the report URL and
its actual meaning in the evidence. These are alerts to watch the account; they
never establish that this account reset. `--account` still identifies the window
being watched. Do not pass `--account-specific`, a percentage, or an ordinary
reset deadline for this kind. The command rejects those contradictory inputs.

The latest advisory remains visible as `PUBLIC_SIGNAL`. It cannot change mode,
hide a failed meter attempt, or advance `NEXT_POLL_AT`. Public reports arriving
frequently therefore cannot indefinitely postpone checking the actual meter.

## Transition contract

The initial mode is `HIGH-BURN`. An initial 100% or repeated 100% reading is never
reset evidence. `CONSERVATION` is sticky; neither later readings nor a process
restart changes it back. Reinitializing an existing ledger fails without a write.

Reliable account-specific evidence switches to conservation on either:

- An explicit notice that the special reset was applied to this account.
- A previous weekly reading of 95% or less, followed by an increase of at least
  five percentage points, while both the previously known and
  currently reported ordinary reset deadlines remain in the future.

The later reading need not still be near 100%: active work may consume part of
the replenished allocation before the next poll. For example, a trusted change
from 63% to 88% before the ordinary deadline qualifies. A small fluctuation of
less than five points does not. These are decision examples, not account readings.

Unknown ordinary-reset timing cannot establish the percentage-jump transition.
Crossing the old ordinary reset deadline does not count as a special reset, even
when the page now shows a new future deadline. A special reset may move the next
deadline; a jump before the old deadline still qualifies. Untrusted observations
remain in the record but never supply a comparison reading or change its cycle.
Account mismatches, other meter scopes, non-finite percentages, missing evidence,
and timestamps that move backward are errors with no ledger mutation.

An optional `--id` makes provider event retries explicit. Repeating an identical
observation is idempotent; reusing an ID for different evidence is an error.

## Coordinator loop

Before dispatch, inspect:

```sh
python3 host/usage_window.py --state /tmp/usage-window.json status --allow-new-work
```

Exit 0 allows useful work in high-burn mode. Exit 2 means conservation: launch no
new optional work, notify active lanes, halt nonessential work, and perform only
the preservation needed to checkpoint completed output. Exit 1 means a ledger or
input error; inspect the diagnostic and preserve existing state. The tool reports
the mode, last real percentage and timestamp, reset evidence, observation count,
warnings, and next action.
`LAST_METER_ATTEMPT_TIMESTAMP` separates account-reading attempts from public
signals; `LAST_OBSERVATION_TIMESTAMP` includes both kinds of activity.

`NEXT_POLL_AT` and `POLL_DUE` are instructions for the already-running coordinator,
not a scheduled task. The default interval is 120 seconds and can be set at init
to 60–180 seconds. A meter older than 180 seconds is explicitly stale. Failed
attempts do not make the last successful meter reading look fresh. If no reading
is available, useful high-burn work continues while the coordinator retries the
legitimate method. Conservation has no further high-burn poll request.

Persistence uses a POSIX advisory lock on a stable sidecar plus a flushed,
atomically replaced JSON file and directory sync. Concurrent cooperating writers
cannot discard one another's observations. A crash before replacement leaves the
last completed ledger intact. This is local active-session coordination, not a
distributed quota API or automatic cancellation service.
