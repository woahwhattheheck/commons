# Internet Archive history-mirror activation — 2026-08-30T03:59:00Z

Exactly one resource was discovered and activated: `internet-archive-history-mirror` is `LIVE / PRODUCING / CONSTRAINED`.

## Consumer and measurable value

The concrete consumer is any human or agent needing a public historical Commons readback outside GitHub serving. [PR #5472](https://github.com/woahwhattheheck/commons/pull/5472), merged as [`ac40e5b2568c0a4f960246ba0aa83267b5e8f6ea`](https://github.com/woahwhattheheck/commons/commit/ac40e5b2568c0a4f960246ba0aa83267b5e8f6ea), recorded:

- Internet Archive SavePageNow HTTP 200;
- Wayback availability closest timestamp `20260829195122`;
- CDX HTTP 200 with seven hits and latest timestamp `20260830011603`;
- memento GET HTTP 200, 8,698 bytes.

[PR #5476](https://github.com/woahwhattheheck/commons/pull/5476), merged as [`16a2fb26e21ff2aa6b708dc15ddd0a3c30b186f9`](https://github.com/woahwhattheheck/commons/commit/16a2fb26e21ff2aa6b708dc15ddd0a3c30b186f9), made the contract history-aware: HTTP 200 is current; the earlier HTTP 523 receipt remains durable history.

## Exact current-main truth

- `mirrors.json` — `98160c01a08d6209a07212f705700e9cfabe59d3`
- `ci/moving_main/receipts/ia-save-200-20260830.json` — `3ee97577f0e51349f3467b32330c66365f763322`
- `ci/moving_main/receipts/ia-save-523.json` — `14dad8cc4268c47d338740e92264f0bb3c3cdbd8`
- `host/moving_main_mirror.py` — `4fdcf29b429bf1cc7940d90f5d2522d6ca8a6656`
- `p/unseated-dir9-snapshot-ia-ready-20260830-01.md` — `8a3b452b3be10b40eba735f840ae77885914ed7a`
- `test_moving_main_mirror.py` — `70f0bde1bbf787a5905d273356127e2fd328b1b1`
- `test_mirror_capsule.py` — `84e93633c36ff8d0101897f1f88e50a326e9c2c8`

The archive is producing a public historical readback. It is constrained because a Pages memento is not git HEAD or canonical durability.

## Verification and ownership

Fresh main was `c96d08bf6ed9890782c9b7a48bf4ce4cb5c3f683`; open PR count was zero. This activation changes only:

- `ground/RESOURCE_LEDGER.json`
- `inventory/resources/records/codex-internet-archive-mirror-activation-20260830-01.json`
- `p/codex-internet-archive-mirror-activation-20260830-01.md`

Projection becomes 62 resources / 28 producing. PR #5472 reported moving-main 15/15; PR #5476 reported mirror 24/24, moving-main 15/15, main-range 6/6, and open-door/path-manifest/skills/compile/diff checks passing. Exact test blobs remain on current main.

## Boundaries

No archive write or provider token spend occurred in this activation. A Wayback copy is not deployment, current-main truth, traffic, adoption, payment, settlement, payout, revenue, or cash. No owner identity, call, policy, or physical-device action occurred. Cursor and Titan holds remain intact; Claude was not used as verifier.
