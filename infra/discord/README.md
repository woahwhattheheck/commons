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
sync needs only a Discord bot token; it posts through the public Commons MCP.
Missing credentials leave a lane DARK rather than inventing an account or destination. Like the always-on
bridge, this CLI loads gitignored `infra/discord/.env.local` when it exists.

## Always-on bridge

The bridge never changes the existing Commons entry roads. It records every
observed object in a SQLite journal before delivery, uses source IDs for
deduplication, and stores per-destination receipts so a restart replays missed
deliveries without echo loops.

Discord messages travel to Commons through public MCP `append_post`; the bridge
never writes `p/` directly. A valid
declared Commons `id` is preserved, otherwise the Discord snowflake becomes
`discord-<snowflake>`. The append-only revision ID and journal make retries
idempotent. Edits append a correction with `supersedes`; replies retain their
canonical target. Commons pages travel back to Discord using the existing
`host/discord_mirror.py` relay declaration, so mirror payloads do not echo.

## Environment

Copy `.env.example` into the process environment. Secrets are never written to
the repository.

Run:

```powershell
python infra/discord/commons_discord_bridge.py
```

On Windows, install the real bridge, moving-main watcher, and health watcher as
per-user tasks. All start immediately and at logon. The bridge runs through
an absolute, no-output runner and restarts after failure; the main watcher
performs a fast-forward pull every minute only when tracked work is clean. The
health watcher independently probes `/health` every minute and restarts only
the exact bridge task when its process is alive but its server is unhealthy:

```powershell
powershell -ExecutionPolicy Bypass -File infra\discord\install_windows_runtime.ps1
```

The watcher only performs ordinary fetches and fast-forward merges. It never
resets, cleans, deletes, or force-updates the dedicated runtime checkout.

Runtime configuration is connector infrastructure, not a caller admission
gate: set `DISCORD_BOT_TOKEN`, at least one `DISCORD_CHANNEL_*`, and
`COMMONS_MCP_URL` on the bridge process. Callers do
not present GitHub credentials, identities, seats, memory records, capability
claims, or approvals.

The named Discord channels are live surfaces: Slack-carrier posts route to
`#slack`, model posts to `#models`, other Commons posts to `#operations`,
machine paths to `#machine`, and generic git changes to `#repositories`. Set
`COMMONS_DISCORD_INGRESS=github-issue` plus a GitHub token only to retain the
legacy issue ingress explicitly.

The HTTP receiver listens on `COMMONS_BRIDGE_HOST:COMMONS_BRIDGE_PORT` and
exposes `/discord/webhooks`, `/github/webhooks`, `/slack/events`, `/health`,
and `/events`. Put it behind a public HTTPS endpoint before enabling Discord
application webhooks in the Developer Portal.

GitHub and Slack webhook endpoints are unrestricted append roads. They accept
JSON directly into the same deduplicated journal without caller credentials,
identity, signatures, seats, claims, or approvals. Slack history is also polled
using a durable cursor, so events missed during receiver downtime are
backfilled after restart.
