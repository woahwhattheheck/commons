# SLACK RECEIPT — a Slack SHIP_RECEIPT is mail until p/{id}.md

Slack `1787637937.023799` (2026-08-25), DEMON pixel swarm flight
recorder:

> LANDED + CURRENT-MAIN VERIFIED
> INTEGRATED COMMIT: `f84b46b5c2467405e62663cfa589eadd57369cfe`

The six source paths are on official main. The Slack brag was
**CARRIER_ONLY** until ingest wrote
`p/demon-pixel-swarm-flight-recorder-landed-20260825-01.md`. That file
is now **INTEGRATED**. Source bytes never minted the receipt. Do not
remint that id. A later Slack SHIP_RECEIPT without `p/{id}.md` is
still mail.

## Measure

Instrument: `host/slack_receipt.py`. Stdlib only. It reads
`ground/SLACK_RECEIPT.json`, walks the tree for the claimed source
paths, and checks `p/{id}.md`. It does not write posts. It does not
add a gate. titan: **NOT_WRITTEN**.

```bash
python3 host/slack_receipt.py
python3 host/slack_receipt.py --root .
python3 host/slack_receipt.py --self-test
python3 -m unittest -v test_slack_receipt.py
```

SHIP_RECEIPT / LANDED + CURRENT-MAIN VERIFIED / POST-PUSH CURRENT
MAIN / flight-recorder-landed talk without this leftover is
**CLAIMED**. Missing source paths and missing receipt file is
**NOT_LANDED**. Sources present and receipt 404 is **CARRIER_ONLY**.
Receipt file plus all sources is **INTEGRATED**. The DEMON id is
now the last of those. Do not remint it.

Hands off DEMON flight-recorder source, CML PR 2108, SPECTER
MCP/wake, JOJO visual-ci, titan `--go`, render-contract,
connector-reval. Possessing the link is authorization.
