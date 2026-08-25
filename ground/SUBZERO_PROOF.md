# SUBZERO PROOF — Explorer v2 proof-classification

Slack `1787648254.904309` (2026-08-25), JOJO
`SHIP JOJO`:

> Next slot is assigned: Subzero Explorer v2
> proof-classification hardening on fresh current main.
> Grok Heavy backend audits remain candidate evidence
> pending non-Grok synthesis.

A Slack assignment is **CLAIMED**. v1 Artifact Explorer
(`ground/SUBZERO_EXPLORER.md`) is already a file. Do not remint
`rivet-ship-subzero-explorer-20260825-01`,
`jojo-subzero-explorer-v2-followup-20260825-01`, `SUBZERO_TECH`,
`SUBZERO_BUYERS`, or the three DEMON panel ids. The receipt-gap
schema is already a file.

Unique leftover: classify each proof claim. Hash-match stays
`STRUCTURAL_ONLY`. Titan status does not decide this leftover.

## Proof classes

`STRUCTURAL_ONLY` · `RUNTIME_MEASURED` · `CROSS_PROCESS` ·
`CUSTOMER_READY` · `UNRESOLVED` · `CLAIMED` · `FINDER-FAILED` ·
`FINDER-UNVERIFIED`

Refused promotions from a hash-match: `RUNTIME_MEASURED`,
`CROSS_PROCESS`, `CUSTOMER_READY`.

Missing job / step / order / sha / runner / receipt is
`UNRESOLVED`, never 0. A string `"true"` is not a JSON boolean.

## Bindings

| field | pin |
|---|---|
| job | `subzero-explorer-v2-proof-classification` |
| step | `classify-public-excerpts` |
| order | `1` |
| sha | v1 explorer pin `dd8da6c23497fe9f05cccd1c604b0a78a89c5ae3` |
| runner | `host/subzero_proof.py` |
| receipt | this leftover, not the Slack body |

Grok Heavy audits stay
`CANDIDATE_PENDING_NON_GROK_SYNTHESIS`. This leftover does not
synthesize them.

## Door

`subzero-proof.html` reads `ground/SUBZERO_PROOF.json`.
Possessing the link is authorization. No auth. No gate. Blank
`from=` still lands as `UNSEATED`.

```bash
python3 host/subzero_proof.py
python3 host/subzero_proof.py --root .
python3 host/subzero_proof.py --self-test
python3 -m unittest -v test_subzero_proof.py
```

Open door. No auth. No gate. titan: **NOT_WRITTEN**.
Talk is not a land. FINDER-FAILED / FINDER-UNVERIFIED, never 0.
