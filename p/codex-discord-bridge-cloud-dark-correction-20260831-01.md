# Discord bridge lifecycle correction — cloud dark, source reachable

Current main still described `discord-bridge` as `PRODUCING / CONSTRAINED` from an activation whose evidence expired after six hours. That evidence measured three Windows tasks, HTTP health, and advancing replay.

Subsequent owner-laptop recovery retired those tasks and verified zero remaining matching processes. The cloud-only implementation remains on main, but the latest outbound run reached its readiness check and correctly failed `DARK`: `DISCORD_BOT_TOKEN` and `COMMONS_DISCORD_CHANNEL` were absent from the GitHub Actions environment. No authenticated cloud sync/readback exists.

This correction keeps the working source and cloud placement. It changes only lifecycle truth:

- capacity: `LIVE`;
- stage: `EXERCISED`;
- condition: `BLOCKED`;
- producing resources: 34 → 33;
- total resources: unchanged at 66.

Evidence:

- base main: `333eb7f2d3c51ea753c889880f3a7ecf15e65c36`;
- cloud placement: [PR #6191](https://github.com/woahwhattheheck/commons/pull/6191), merge `b893c601b3c873762034aea5ecb49578439307f2`;
- failed-dark run: [33384940953](https://github.com/woahwhattheheck/commons/actions/runs/33384940953), outbound job `99465359621`;
- local retirement receipt: [Slack](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1788128957320909);
- correction claim: [Slack](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1788180414734879).

The exact continuation is private provider-account work: configure the existing GitHub Actions Discord credential and channel without exposing either value, then require one authenticated sync/readback before restoring `PRODUCING`. This change does not perform that account action.

No Discord contact, credential read/write, Windows task restoration, workflow refactor, outreach, payment, revenue, cash, Grok, or Cursor activity occurred. Public Commons posting and source roads remain open.
