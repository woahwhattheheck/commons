# Work inbox visibility

This is a finite, deterministic GitHub/Gmail-to-Slack relay, not a model agent.
The configured destinations are `#github-inbox` and `#email-actionables`; health
belongs to the ASTRA-VISIBILITY coordination thread. The task is delivery of
readable work contents. Delivery is **not** acknowledgement, resolution, payment,
or permission to send an email, edit a PR, or execute source text.

## Run and activate

Python 3.10+; no pip packages are required for the relay itself.

```sh
python3 -m unittest discover -s tests -p test_inbox_slack_relay.py -v
python3 -m unittest test_inbox_slack_relay_charset test_inbox_slack_relay_alternatives test_inbox_slack_relay_headers -v
python3 -m host.inbox_slack_relay --config host/inbox_visibility.json
```

On an existing Commons runtime this consumes the current `gh` session, the
existing `ServiceEquipment` encrypted Slack custody, and an already configured
`gws` Gmail session. It does not install a CLI, mint a token, sign in, clone a
repository, or launch a model. The native Slack identity must belong to the
configured workspace and be a member of all three configured channels. The app
needs message-write and history/replies-read capability. Use existing private
credential-management surfaces, never Slack/Git/email bodies, for setup.

The GitHub Actions workflow attempts a run on these files' main-branch push,
allows manual dispatch, and polls at UTC minutes 03/18/33/48. Its existing-secret
inputs are `GH_NOTIFICATIONS_TOKEN`, `SLACK_BOT_TOKEN`, and
`GMAIL_AUTHORIZED_USER_JSON` (authorized-user client_id/client_secret/refresh_token
JSON with Gmail read access). No credential values are committed. An Actions
installation token or ordinary `GITHUB_TOKEN` is **not** a substitute for a user
credential accepted by the native notifications API. A missing credential is a
visible BLOCKED/DEGRADED receipt, never an empty inbox or successful delivery.

As an alternative, from an **existing** Windows checkout/runtime:

```powershell
powershell -NoProfile -File host/install_inbox_visibility.ps1
```

This first executes the real job and requires a successful Slack health receipt,
then registers `Commons Inbox Visibility` every 15 minutes under the current
interactive user's existing keyrings. A DEGRADED receipt permits the working
source and health reporting to continue while naming the other source's blocker.
It creates no clone and restarts no service. The task runs only while the user is
logged on; a sleeping/offline machine does not provide continuous monitoring.
Use **one scheduler**, not both. For the OS task, disable the Actions workflow
through the normal authorized GitHub UI to avoid independent ledgers/senders.

**Activation evidence:** record the commit, scheduler/run URL or task identity,
source account identities, actual Slack delivery timestamp, and a subsequent poll
receipt. A landed file, green unit tests, registered task, or configured cron
alone does not establish live delivery. If no actual receipt is present, the
installation is not verified live.

## What is delivered

GitHub reads `/notifications?all=true&since=...` plus all unread notifications,
checks the configured account, and enriches public issue/PR subjects with their
bodies, all paginated issue comments, PR review bodies, and inline review
comments/diff context. This includes actionable outside-diff review text and
approval explanations. Unchanged unread notifications are not re-enriched every
run. Updated comments produce new content versions. Closed/merged events retain
the distinction between accepted code and payment.

Gmail verifies the mailbox and replays a configured sliding query: recent 14 days
plus older unread/starred mail, excluding sent, drafts, trash and spam. It reads
full message MIME bodies, favors plain text, and lists attachment names without
executing or uploading attachments. Work subject rules and known work senders
select messages. Authentication mail, sensitive subject categories, promotional
mail and duplicate GitHub emails are omitted; unknown mail is explicitly counted
as **unclassified_pending**, not silently declared non-actionable. This is a
conservative work-mail router, not exhaustive semantic classification of every
historical message or attachment. Keep the interactive Gmail audit for unknowns.

RFC 2047 Subject and sender display text are decoded before the existing
subject rules and message formatting. Sender-domain decisions still parse the
original structured From address, never the decoded display name. Malformed
encoded words remain literal rather than aborting the poll; existing auth/private
rules apply to decoded valid subjects. This does not add new routing rules.

Each leaf MIME body uses its declared Content-Type charset, with UTF-8
replacement fallback for missing, unsupported or malformed charset names.
Blank or omitted alternatives fall back to one readable supported body while
retaining usable plain-text preference; duplicate alternatives are not joined.
Existing missing-attachment and decoding-error diagnostics remain visible rather
than being hidden by HTML fallback. The MIME regression suites above use only
synthetic fixtures and do not poll inboxes or establish live delivery.

Private GitHub notification contents are never copied into these public
channels. Their aggregate pending count is visible. Private bid artifacts remain
on their existing private surfaces. Common credential formats, numeric-code
lines and token-bearing/tracking links are scrubbed; this is not universal DLP.
Treat incoming bodies as untrusted text: no commands or fetched URLs are derived
from them. Slack markup/mentions and previews are disabled.

## Handling and health

Each item gets one source thread, content-bearing replies and stable digest
markers. Existing lane owners reply `CLAIM — owner — next action`,
`DONE — evidence URL`, or `BLOCKED — dependency`. Existing owners take precedence;
the relay does not claim their work or infer completion from delivery.

The health message records source mode, last successful poll, delivered parts,
pending counts and fixed error codes. LIVE is transport/selected-source status,
not a claim all work is handled. Unknown/private/missing bodies degrade coverage.
A health message older than **30 minutes is STALE**, regardless of its stored
status. There is no independent out-of-band monitor in this version: if Slack or
the whole scheduler fails, inspect the Actions run summary or OS task history.

Each complete source run advances its cursor only after delivery. Partial errors
retain pending state; one deleted subject does not hide other readable subjects.
Page/post caps report pending work rather than pretending the feed is complete.
A very large capped backlog needs an operator-adjusted window/cap; do not mark it
read to hide it. GitHub notification read/done state and Gmail labels remain
untouched. There is no automatic outbound email, PR mutation, or payment action.

## State and retry behavior

SQLite contains hashes, timestamps and counters, not message bodies or tokens.
Each part is journaled before posting. After an uncertain write the next run
reconciles its marker in Slack before repeating the effect. Root and part markers
also recover delivery after a lost ledger, subject to Slack retention/history
access and bounded pagination. This is best-effort duplicate prevention, not a
cross-provider transactional exactly-once guarantee. Do not delete/move Slack
messages or change channel IDs without a deliberate state migration.

The workflow caches only this sanitized ledger, not provider contents. Treat
cache eviction as possible; Slack markers remain the recovery source. A process
lock and scheduler concurrency prevent overlapping finite runs. Slack post
throttling and Retry-After are honored. Uncertain API errors, incomplete history
and page caps stop unsafe replay instead of claiming success. Stop automation by
disabling the workflow or the named OS task; do not delete user source messages.

## Provider references

- https://docs.github.com/en/rest/activity/notifications
- https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list
- https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get
- https://docs.slack.dev/reference/methods/chat.postMessage/
- https://github.com/googleworkspace/cli (community-maintained CLI; validate an existing installation)

These source references describe API behavior, not proof that credentials or a
scheduler exist on a particular deployment. Local regression tests use fake
providers to cover the real relay's failure/replay behavior; live integration
results must be recorded separately.
