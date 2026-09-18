# Land — waitlist CCPA delete

The waitlist door tells people they may email the owner to request deletion
and that the public door has no lookup. This leftover is the owner-local
tool for that request.

Run on the owner machine:

```bash
python3 host/pack_waitlist_delete.py --jsonl ~/.tjlabs/waitlist-signups.jsonl --email the-request
```

The address is dropped from JSONL. A hash tombstone remains. Counts are
recounted without that row. The helper never prints the email. Sending stays
owner-gated and this tool sends 0.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP.
