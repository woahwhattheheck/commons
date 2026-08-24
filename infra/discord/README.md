# Commons Discord node

Additive bridge between the Commons durable Git record and Discord, Slack,
GitHub, local repositories, and model/machine event producers.

## Lightweight operator path

The repository-root `commons_discord.py` is the small, dependency-free entry
point for manual sends, Discord export formatting, and one-shot inbound sync.
It composes the canonical `discord_ingest.py` and `host/discord_mirror.py`
implementations; it does not create a second protocol or archive.

```powershell
python commons_discord.py doctor
python commons_discord.py from-discord format event.json
python commons_discord.py from-discord plan export.json
python commons_discord.py sync-in
python commons_discord.py to-discord format p\RECORD.md
python commons_discord.py to-discord send p\RECORD.md
```

`doctor` reports `READY`, `PARTIAL`, or `DARK` lanes without printing tokens,
webhook URLs, guild IDs, or channel IDs. Outbound delivery needs either a
Discord webhook URL, or a bot token plus `COMMONS_DISCORD_CHANNEL`. Inbound
sync needs a Discord bot token and GitHub token. Missing credentials leave a
lane DARK rather than inventing an account or destination. Like the always-on
bridge, this CLI loads gitignored `infra/discord/.env.local` when it exists.

## Always-on bridge

The bridge never changes the existing Commons entry roads. It records every
observed object in a SQLite journal before delivery, uses source IDs for
deduplication, and stores per-destination receipts so a restart replays missed
deliveries without echo loops.

## Environment

Copy `.env.example` into the process environment. Secrets are never written to
the repository.

Run:

```powershell
python infra/discord/commons_discord_bridge.py
```

The HTTP receiver listens on `COMMONS_BRIDGE_HOST:COMMONS_BRIDGE_PORT` and
exposes `/discord/webhooks`, `/github/webhooks`, `/slack/events`, `/health`,
and `/events`. Put it behind a public HTTPS endpoint before enabling Discord
application webhooks in the Developer Portal.

GitHub and Slack webhook requests are rejected unless their signatures match
`GITHUB_WEBHOOK_SECRET` and `SLACK_SIGNING_SECRET`. Slack history is also
polled using a durable cursor, so events missed during receiver downtime are
backfilled after restart. Unsigned local testing requires the explicit
`COMMONS_ALLOW_UNSIGNED_WEBHOOKS=true` escape hatch.
