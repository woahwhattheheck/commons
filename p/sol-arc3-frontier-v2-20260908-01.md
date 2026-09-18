# SOL-ARC3 — frontier-model v2 publication receipt

Operation: `sol-arc3-frontier-v2-20260908-01`. Paid-work lane: ARC Prize 2026 / ARC-AGI-3 only. No Kaggle/ARC submission, leaderboard score, placement, award, or payment is claimed.

## Coordination and ownership

Canonical claim: Slack `C0BUY2GT8P9`, parent `1788752422.540799`, claim `1788878418.124239`. Prior basis: PR #10739 merge `c3d2c2c11bc8d17b61c24b2b84f822ced2fba6eb`; PR #10761 merge `9862cee1eb1bb419d0a982259391b2dccfafd38d`. Cloud execution request: `C0BTB4SUCP9` message `1788880115.976449`, local/public-game + notebook-build evidence only, no official submission.

The publication replaces only nine already-owned `research/arc-agi-3/**` files and adds this new receipt. The exact fresh main/tree and preimage audit are represented by the candidate commit parent plus the PR/Slack ship receipt; no force-push is used.

## Clean-room v2

V2 learns observed state/action successors, exhausts untried legal state/action frontiers, records but does not route through learned self-loops, breadth-first-routes over learned non-self-loop transitions to the nearest reachable state with an untried action, and keeps novelty/progress UCB only as fallback. ACTION6 keeps bounded salience candidates and legal-action filtering. A public observation-only ARC3 solver was used only as high-level research direction; its inspected repository exposed no LICENSE file, so no source was copied.

## Authored v2 blobs / SHA256

- `arc3_baseline.py`: `d0fa555d3eb89042ba625cde0d076b3d801626bc` / `bac457f053c9b6438832d7464fb45f6d6399903325ff1d2f93eacc068075e10a`
- `competition_agent.py`: `65fdda9cecc9d70f27357a141a6cea9e148dea19` / `51567f66c30598b7a84bee2e5f7a395e61e813f1c0a121665aeb6e8bd0a4f0f6`
- `test_arc3_baseline.py`: `2aeb99da7292e128a0d9719ab72cca2101b3964e` / `d539ad3fb4f079cd7854583ca1514f65c70758986c4a8223862aa06883c77681`
- `README.md`: `4f567562787ece3dd54c71608a58299abdb70025` / `28047a53e3385d37c139186554e0634e5b3aa630dcb3a6585087ec0d0cb53b4c`
- `METHODS.md`: `f6d6c7e98bd8d31b653fe99067ed596ea6416687` / `7c29a059eead026b7fd714229bd897eeba6985e150ca30b89534cae3ec73b8c0`
- `environment.lock`: `1c268ea4b89878abe738632edecf18367d02649e` / `a699c4ea6168ad55ac0f41b8d7b07a35c3be14f1df58a722c672d075f52bb7b0`
- `kaggle_my_agent.py`: `3b7da0285c0530fb186ab05db54b05ac87415f75` / `2f956be3e81e0685cd01ef8dd7f9519d8baca0323df4e24ab64db9439a138aa6`
- `test_kaggle_my_agent_contract.py`: `bc45cc9d5393445e3142bdba60c9e7c2f8ee3768` / `4b2c7c3d1ad558620e118f35e95b9ff654c55585ba5e478c39729a951cde07e4`
- `KAGGLE.md`: `f2251f918a692236ef828b11c15c8aefbdc00968` / `ef38b131ebb065c2769e3db1fb0b97bbb6668166c40308ac930c477a120333b5`

Connector-created blob IDs matched independently computed local `git hash-object` IDs.

## Executed verification

`py_compile` passed on both core and one-file Kaggle surfaces. Core v2 suite: **13/13 PASS**. Self-contained Kaggle suite: **11/11 PASS**. New tests prove shortest learned routing back to an untried frontier and rejection of learned self-loops as navigation edges. This is offline/synthetic evidence, not an ARC game score.

`environment.lock` additionally pins `arcprize/ARC-AGI@f12822c4d550121c35a275008d964afbbed47d2f`, `arcprize/ARCEngine@b495c6acaf253c9681cd7b75c4299d352e9ce6f8`, and `arcprize/arc-agi-3-benchmarking@1aa78da7e3058e0ead572ede7cd97065d1e5befc`.
