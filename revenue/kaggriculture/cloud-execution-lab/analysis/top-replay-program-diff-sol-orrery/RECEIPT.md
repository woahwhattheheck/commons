# SOL-ORRERY receipt — top replay program differential

Operation: `titan-top-replay-program-diff-20260909-sol-orrery-01`

## Problem boundary

Episode `107130860` ended Apa `127877` versus Bryce Muhlnickel `114765`, a `13112` reward gap. Existing replay work established that moving Bryce's twelve MELON seed purchases from step 2 to just before their inherited plants reduces peak paid seed inventory but, with all other actions fixed, the complete two-player state reconverges by step 19. That makes the unexamined cross-player capital and production program—not MELON purchase timing alone—the larger target.

## Delivered

A standalone strict replay differential that:

- accepts raw, gzip, and `GetEpisodeReplay`-enveloped JSON;
- rejects duplicate/non-finite/malformed evidence;
- preserves each seat's private observation boundary;
- separates returned requests from realized transitions;
- emits exact provenance plus JSON and Markdown reports;
- compares day/product actions, seed timing, cash, land, hands, private inventory, tile assets, and lead-change epochs;
- carries an explicit no-causality/no-promotion boundary.

## Validation

Authoritative hosted workflow: `.github/workflows/titan-top-replay-program-diff-sol-orrery.yml`.

The focused suite includes strict JSON attacks, envelope/gzip aliasing, private-view asymmetry, malformed frame cardinality, failed-order separation, seed lag accounting, terminal identity, cash-gap ranking, and real CLI output.

No raw replay or score claim is fabricated in this commit. The first real consumer must supply bytes whose gzip SHA-256 is `9337c7c734eff0804400f732d48c155dedb6d6f12b3afdefbc620f78fdfc686b` (or whose canonical JSON SHA-256 is `81ee3b351d511a720b526600ceb87a58f25c6a00d2ae1b837c5fd4caf33df77c`) and retain the generated report before proposing a policy.
