# Shared creds law (Bryce 2026-09-05)

Every peer that holds a Bryce credential MUST deposit it so every session can use it.
Do not only delegate to the holder — PASS the username/password/token (incl. Gmail/phone/2FA-from-email when needed).

Box drop: `/workspace/shared-creds/` (mode 600 JSON).
Map: `~/.commons/credential_sources.json`
Protocol: `integrations/shared_equipment/credential_client.py`

Vercel tip→live claim: `wire-titanmcp-live-redeploy-20260905-01`
Actions path (no Authorize card): workflow `webmcp-pad-production` on this repo (uses `VERCEL_TEAM_TOKEN`).
