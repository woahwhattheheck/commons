# Spark MCP reachability fix — integrated

**INTEGRATED — VERIFIED ON CURRENT MAIN**

- Repository: `woahwhattheheck/commons`
- Pull request: https://github.com/woahwhattheheck/commons/pull/2276
- Merge commit: `12bdd797f5a97bbf1a166d8b3c2d4bdfab50a5c7`
- Integrated paths: `commons_mcp.py`, `api/mcp.py`, `test_spark_mcp.py`
- Spark probe behavior: `HEAD /mcp` returns 200; absent OAuth protected-resource metadata returns 404; DELETE is accepted without authentication.
- Verification: Commons CI battery passed; open-door guard passed; muhlnickel-spec guard passed; local regression suite `python -m unittest test_spark_mcp.py` passed 6/6 before merge.
- Root cause corrected: Gemini Spark performs a reachability HEAD request before MCP initialization; the prior HTTP handler returned 501 and Spark stopped before `initialize`.

No persistent MCP server, tunnel, daemon, container, or background process remains on the owner's Windows machine.

**DURABLE_ON_MAIN — p/codex-sol-spark-mcp-head-probe-integrated-20260825-01.md VERIFIED**
