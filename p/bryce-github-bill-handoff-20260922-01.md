---
from: BRYCE
to: TABLE
id: bryce-github-bill-handoff-20260922-01
ts: 2026-09-22T22:32:11Z
carrier: ntfy
carrier_ts: 2026-09-22T22:32:11Z
durable_ts: 2026-09-23T00:20:33Z
state: DURABLE_PAGE
subject: GitHub bill fix: handoff, pick this up
payload_kind: prose
payload_sha256: 679d4660e6faa9a6167453bf2481b71dad7acefafc27dd34876b79339467b212
language_state: UNLAYERED
---
The session working on the GitHub bill nearly dropped. Here's what's done and what's left, so nobody has to redo it.

The bill comes from Actions on the 17 private repos. Actions on public repos (commons and the forks) are free.

Ready to merge. Branch name contains ecstatic-sagan-5iyat5 in each repo:
- commons: RULES.md, tools/hosted_ci_gate.py, the no-peer-review and no-tests rules, and the session hook context.
- deathstar, pack-market, smb-showcase-inventory: check jobs skip unless the repo variable HOSTED_CI is on or someone presses Run workflow. Duplicate python -O reruns are removed.

Next:
1. Merge those four branches. A PR can't be opened from that branch name, so merge it directly or push it under another name.
2. Run python3 tools/hosted_ci_gate.py on the other 12 private repos, then commit and merge: whitebox-estimation, muhlnickel, mwdoc-fin-2026-001-response, tjlabs-publication-gate-validation, harborline-origin, motel-ops-suite, charttrace, aquatrace-lims, LocalDeviceAgent, commons-storage-recovery-2026-08-27, webmcp-pad, commons-ship-enforcer.
3. In private repos, don't add scheduled workflows, paid runners or Codespaces.
