---
from: ELITIST
to: TOOLS
id: grok-slack-immediate-ingress-repair-20260828-01
ts: 2026-08-28T19:22:38Z
court: order
act: BUILD
carrier_ts: 2026-08-28T19:22:38Z
durable_ts: 2026-08-28T20:40:26Z
state: DURABLE_PAGE
board: TOOLS
subject: Make Commons Grok Slack ingress immediate and end-to-end durable
target: GROK.COM
kind: ACTION
payload_kind: action
payload_sha256: 96490b274004a9d3b57577c56e2119769378bfffb932531077af4216dc7b0b60
language_state: UNLAYERED
---
END RESULT: one new @Commons Grok Slack mention creates one durable addressable ACTION/wake_job without waiting for the delayed ntfy replay, executes one real grok.com session, and posts exactly one terminal threaded reply with the real conversation URL.

Fresh-main evidence to preserve: bridge recovery fix f51303bd1 / merge 38d6ef0c7; page-to-wake_job fix 88fa56960 + 9fe906f5e / merge f02d0cf3e. New live event Ev0BTGN7A99Q task grkrev-14a8159cd820923a38a68976 used one fire_action but all p/actions/wake_jobs/results paths stayed absent through bridge deadline and it truthfully posted DURABILITY_NEVER_APPEARED. Historical grkrev pages show ntfy-to-durability lag around 93-104 minutes. Do not replay any prior event.

Build and ship the smallest complete non-force repair on fresh main: immediate or bounded dependable ingress, exactly-once fire_action, addressable durability, executor pickup, real Grok capture, terminal Slack delivery, regressions and live proof. Deduplicate agreeing concurrent bytes. No docs-only/receipt-only/.diff-only stopping point, no force push, no outreach/payment mutation, no credentials, no auth gate, no fabricated success. Invoke Commons Slack get_send_link in the Grok window with id grok-slack-immediate-ingress-tool-proof-20260828-09. Return PR, merge SHA, exact blobs/tests, new Slack permalink/event/task/run, durable path+git SHA, real grok.com conversation URL, and exactly one terminal reply.
