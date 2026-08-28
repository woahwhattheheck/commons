# Owner-context display host

Directive 10 leftover: a host outside the static Pages tree can annotate
the owner's interface with a privacy-preserving network-context digest.

Display only. Never a gate. Never authority. Never publishes a raw IP.
from= stays a claim. Two-slot hashed enrollment stays on `owner.json`.
Do not remint `owner_net.py`. Cite `BRYCE-1787134106972-vr8fo8`.

```text
browser
  -> GET https://<host>/owner-context
  -> host sees connecting peer, hashes pepper + LF + IP, drops the IP
  -> JSON {k, sha256, slot?, display_only, authority:false, gate:false}
  -> owner-net.html / owner.html may paint the digest
  -> posting, reads, writes, execution stay open
```

## Local simulation

```text
python3 host/owner_context.py simulate
python3 host/owner_context.py serve --bind localhost:8789
python3 host/owner_context.py doctor --no-probe
python3 test_owner_context.py
```

Simulate only accepts documentation-range fixtures (RFC 5737 / RFC 3849).

## Exact-host adapters

| kind | adapter |
|---|---|
| local stdlib | `python3 integrations/owner_context/service.py serve` |
| systemd | `commons-owner-context.service` |
| docker/compose | `Dockerfile` / `compose.yml` |
| already-connected Vercel | `api/owner_context.py` + `vercel.json` rewrite `/owner-context` on `commons-spark-mcp.vercel.app` |
| Cloudflare Worker | `worker.mjs` + `wrangler.toml.example` |

GitHub Actions is not an always-on host.

## Doctor

`python3 host/owner_context.py doctor` reports `CODE_LANDED`, `LIVE`, or
`NOT_LANDED`. It never invents LIVE. Missing public URL is
`EXTERNAL_HOST_ACTION`, not a remint.

## EXTERNAL_HOST_ACTION

Deploy the repo-controlled adapter onto an always-on host that can see
the connecting peer. Preferred already-connected host: existing Vercel
project `commons-spark-mcp.vercel.app` (`vercel.json` rewrite
`/owner-context` → `api/owner_context.py`). Confirm GET
`https://commons-spark-mcp.vercel.app/owner-context` returns JSON
`k=owner-context authority=false gate=false` with no raw IP. If that
project does not auto-deploy this repo, trigger a production deploy of
current main on the Vercel project already connected to
`woahwhattheheck/commons`. Do not mint a new Vercel project. Alternative
exact hosts: systemd unit, Docker compose, or Cloudflare Worker from
`wrangler.toml.example` (do not commit secrets). Then set
`owner.json context_host.public_url` to the live HTTPS origin and re-run
the doctor.

no auth. no gate.
