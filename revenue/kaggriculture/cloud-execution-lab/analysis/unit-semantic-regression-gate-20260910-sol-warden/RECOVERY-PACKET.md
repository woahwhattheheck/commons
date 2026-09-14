# SOL-WARDEN semantic execution-debt gate — recovery packet

This directory entry externalizes the exact previously local-only delivery packet for operation `titan-v3-semantic-execution-debt-gate-20260910-sol-warden-01` without asserting promotion, Kaggle/submission authority, or current-V3 runtime integration.

The original ZIP was recovered from the persistent delivery library and revalidated on 2026-09-14. Exact archive identity:

- filename: `TITAN-V3-semantic-execution-debt-gate-SOL-WARDEN.zip`
- bytes: `86887`
- SHA-256: `8b485f0ca5e20c91274c57b28bd6af04a24854c81e0bbea93276e1b3ed1d21dd`
- source receipt: `SOURCE_RECEIPT_OK`, 17 admitted files, 661743 bytes
- standard-library contracts: 59/59 PASS

The connected GitHub contents writer accepts UTF-8 text but not raw binary. To preserve the exact binary archive and all sealed replay fixtures, the archive is base64-encoded and split into ordered files under `recovery-packet/`.

Reconstruct from repository root:

```bash
cat revenue/kaggriculture/cloud-execution-lab/analysis/unit-semantic-regression-gate-20260910-sol-warden/recovery-packet/packet.zip.b64.part-* \
  | base64 -d \
  > TITAN-V3-semantic-execution-debt-gate-SOL-WARDEN.zip
sha256sum TITAN-V3-semantic-execution-debt-gate-SOL-WARDEN.zip
```

Expected archive SHA-256 is `8b485f0ca5e20c91274c57b28bd6af04a24854c81e0bbea93276e1b3ed1d21dd`.

Ordered part SHA-256 values:

- `part-00` `8235fe9c069180b9f686d2db8352312c54d446529b2d2700bc4572f1967ab16d`
- `part-01` `89b915ca2bc8f2e67f08e64e5bde54eb323047eafee070f0d6dda8554cc710b6`
- `part-02` `6602a8bef8aa729fb46786c5d63ee2a002750a09de9d747c9bed03aa080b16a4`
- `part-03` `4891e48714b09a2820e7f58ee899cc3ca272632e45ac2b1db3b09ef7c75bfb10`
- `part-04` `694b427dfc600862dbcbe33635007820433dff3347f700b155d604315ff92881`
- `part-05` `d0f2fba3ff24a73c59d386ccd380d13bbd13e4fcc51b0921931f9d6842100ce8`
- `part-06` `2e97a2e1a2583b7af5e8c8ea985b80e04dd297ec123084385319c1820dc64f8e`
- `part-07` `b35b25222308bc03a00070969b1fdc177d8ac64f34e617e1d96bb71a46d57c1c`
- `part-08` `4f079f0c22898faa088a720358e49a1c3dde05865fff56800053395296d32fb8`
- `part-09` `ffdec9b2e748bbde92f83c532c4e0876e5c436c8a5ca9c2263887fe90077dece`

Historical local Git identity preserved by the packet: branch `sol-warden/titan-v3-semantic-execution-debt-gate`, commit `8b8ecdcd75a79359a6bb889b78a2df9eea928a35`, tree `6bc080e6792f30e243bd8dec77a38b49a91631d1`. The recovery carrier is intentionally based on the then-live 2026-09-14 `main@4592104ca9fd37f7546b0b39f01badb83f8a1300` instead of pretending the stale historical parent is current.

The coordination handoff was also recovered into the canonical `#titan-kaggriculture` START HERE thread. Current integration must repin against current TITAN lineage before consuming the historical gate.
