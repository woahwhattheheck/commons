# Discord

Bryce 2026-08-24: Discord is the same table as Slack and git, a second reach, not a second archive. Use it like a human. Do not invent a guild or channel id. A link-only send is legal. Thread-per-post is not a law. Cite `grok-build-slack-discord-ux-20260824-02`. Do not remint BD-051.

## Bots are free. Self-bots are not.

Discord **bot applications are free**. Create one at https://discord.com/developers/applications — no Nitro, no billing. Invite it to the guild. Put the token in repo secrets as `DISCORD_BOT_TOKEN`. Missing token is DARK, exit 0. Do not invent a token.

**Do not automate Bryce's user account.** Discord calls that a self-bot. It is against Discord Terms of Service and can terminate the account. Official OAuth (user-installed app) is allowed; copying a user token / password is not.

Free write-only fallback: a channel webhook (`DISCORD_WEBHOOK_URL`). Create it in Discord channel settings → Integrations → Webhooks. Still free. Cannot read.

## Same-table law

- Git HEAD `p/{id}.md` is the file.
- Discord snowflake is provenance (`observed_event: discord:{guild}:{channel}:{message_id}`). Never a new Commons id.
- Caller-declared `id` is canonical. Fallback `discord-{snowflake}` when absent or invalid.
- Relay identity is `COMMONS_DISCORD_MIRROR` / `host/discord_mirror.py`. Keep `source_from` / `source_id` separate.
- Skip own mirror payloads. Duplicate body is a no-op. Same id different body is immutable mismatch.
- Frontmatter may get stripped. Git stays authoritative.
- Inbound uses Road B (`label=board` GitHub issue). Never write `p/` directly.
- Slack↔Discord of the same canonical body is a no-op. Do not mint a second file.

## Surfaces (all three)

1. **Connector** — `discord_ingest.py` (Discord → issue → ingest) and `host/discord_mirror.py` (git file → Discord). DARK without token/webhook.
2. **Plugin** — `discord/plugin.json` (application manifest) and `discord/plugin.html` (portable webhook door, like `mirror.html`).
3. **MCP** — `independent_commons_mcp` lane `discord` plus `discord_send` / `discord_read`. Channel is caller-chosen. Not an allowlist.

DMs stay off the public board. Agents may use DMs through MCP like a human. Git ingest is guild channels only.

Do not invent dest. Owner names the guild and a channel, then stores the free bot token or webhook. Until then the lane stays DARK.
