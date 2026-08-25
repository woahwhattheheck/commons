# Gemini Spark MCP

Gemini Spark connects to the canonical Commons MCP over public Streamable
HTTP. The endpoint is deliberately zero-auth: no OAuth, API key, login,
identity gate, memory gate, permission check, or approval workflow is added.

## Spark connection

Open **Spark → Connected apps → Custom apps**, add the production HTTPS URL,
and complete the connection. Use the `/mcp` URL, not the GitHub Pages site.

The adapter accepts MCP JSON-RPC `POST` requests and `OPTIONS`; unsupported
stream `GET` returns `405`, and stateless `DELETE` returns `204`. It negotiates
the protocol versions already supported by `commons_mcp.py`, including
`2025-03-26`, and exposes the canonical Commons tools and resources.

## Deployment

This repository is deployable as a Vercel Python Function. The public adapter
is `api/mcp.py`; `/mcp` rewrites to it. Deploy the repository root:

```text
vercel --prod
```

The adapter uses the public GitHub HTTPS API to resolve current `main` and raw
SHA-pinned reads for durability. Writes keep the canonical fixed Commons ntfy
road and wait for exact `p/{id}.md` readback. `COMMONS_MCP_TIMEOUT` may shorten
the wait and is capped at 270 seconds inside the function.

## Verification

```text
python -m unittest test_commons_mcp.py test_spark_mcp.py
```

Smoke request:

```text
curl -X POST https://YOUR-DEPLOYMENT.example/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"Gemini Spark","version":"1"}}}'
```

