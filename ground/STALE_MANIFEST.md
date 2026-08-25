# STALE MANIFEST — KEYB size agrees, bytes do not

Slack `1787638201.498979` (2026-08-25), DEMON correction:

> `C:\Users\lucys\Desktop\MUHL_KEYB\keyb01.manifest.json` is dated
> 2026-08-21T14:23:58Z and claims 430,860 bytes with SHA-256 prefix
> `a63396...`. `keyb01.mno` is still 430,860 bytes but was modified
> later at 2026-08-21T14:25:19Z; its current measured SHA-256 is
> `cca2b76224eaab93ed69b42a9b464d42f493ca9d233d693b02cb803bb5cbdfed`.

Size agrees. Bytes do not. The public Commons copy of that stale
claim is `excerpts/20260821/keyb01.manifest.json`. Do **not** land,
wire, execute, or describe this container as manifest-verified.

## Preserve

- Public `excerpts/20260821/keyb01.manifest.json` stays the first
  canonical body. Do not remint it. Do not overwrite it.
- Desktop `keyb01.manifest.json` and `keyb01.mno` stay on the owner
  machine. This cloud box cannot read them. Cited hashes are
  **CLAIMED desktop measurements**, not a re-hash from here.
- `ground/WORKING_BUILDS.json` rook and titan-census dispositions
  stay unchanged. Only the earlier KEYB hash assertion is superseded.

## Chronology (cited)

1. `2026-08-21T14:23:58Z` — desktop manifest written (`a63396…`).
2. `2026-08-21T14:25:19Z` — `keyb01.mno` modified 81 seconds later
   (`cca2b762…`). Intent of that mutation is **UNRECONCILED**.
3. `2026-08-22T00:48:56Z` — Action Pad PUSH
   `p1-ap-push-keyb-man-20260821-01` copied the stale claim onto
   Commons.

A new measured replacement manifest is refused until an
owner-machine inspect says the post-manifest mutation was intended.

## Measure

Instrument: `host/stale_manifest.py`. Stdlib only. It reads the
public manifest and `ground/STALE_MANIFEST.json`. It does not write
titan. It does not smash `commons.mno`. It does not add a gate. It
does not upload `keyb01.mno`.

```bash
python3 host/stale_manifest.py
python3 host/stale_manifest.py --self-test
python3 -m unittest -v test_stale_manifest.py
```

Public structural inspect of the checked-in manifest: magic
`KEYB01v1`, 16×128, depth 8, 16489 gates, mouths HELP / READ /
WRITE / FIRE / SURFACE / ACK, claimed 430860 / `a63396…`. Git
copies do not run. Desktop container remains **UNMEASURED** here.

Missing public claim or missing cited SHA is **NOT_LANDED**. Talk
that still treats KEYB as manifest-verified is **CLAIMED**. A catalog
that names both hashes, size-agree / hash-disagree, NOT_VERIFIED,
refuse-rewrite, and UNRECONCILED intent is **INTEGRATED** for this
leftover.

## Desk

`land.js` `isStaleManifestTalk` names the MUHL_KEYB-manifest-is-stale
/ size-agrees-bytes-do-not / do-not-integrate-as-verified copy
CLAIMED until this leftover path is on current main.
`staleManifestState` names the measured instrument.
DIO / JOJO: do not land, wire, or execute the container as verified.
Owner-machine read-only inspect of the current `.mno` stays their
lane. titan: **NOT_WRITTEN**.

Possessing the link is authorization. No auth. No gate.
