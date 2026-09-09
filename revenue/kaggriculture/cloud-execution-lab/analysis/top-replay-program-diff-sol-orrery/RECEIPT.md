# SOL-ORRERY receipt — top replay program differential

Operation: `titan-top-replay-program-diff-20260909-sol-orrery-01`

## Problem boundary

Episode `107130860` ended Apa `127877` versus Bryce Muhlnickel `114765`, a `13112` reward gap. Existing replay work established that moving Bryce's twelve MELON seed purchases from step 2 to just before their inherited plants reduces peak paid seed inventory but, with all other actions fixed, the complete two-player state reconverges by step 19. That makes the unexamined cross-player capital and production program—not MELON purchase timing alone—the larger target.

## Delivered

A standalone strict replay differential that:

- accepts raw, gzip, and `GetEpisodeReplay`-enveloped JSON;
- rejects duplicate/non-finite/malformed evidence;
- enforces compressed and incremental decompressed byte ceilings before parsing;
- preserves each seat's private observation boundary;
- separates returned requests from realized transitions;
- emits exact provenance plus JSON and Markdown reports;
- compares day/product actions, seed timing, cash, land, hands, private inventory, tile assets, and lead-change epochs;
- carries an explicit no-causality/no-promotion boundary.

The large analysis implementation is preserved as `replay_program_diff_core.py`; the documented `replay_program_diff.py` facade owns bounded ingestion and delegates parsing, analysis, and rendering to that core.

## Validation

Local pre-publication command:

```bash
python -m py_compile replay_program_diff.py replay_program_diff_core.py test_replay_program_diff.py test_replay_program_diff_bounded_io.py
python -m unittest -v test_replay_program_diff.py test_replay_program_diff_bounded_io.py
```

Result: **14/14 PASS**, zero skips and zero errors. Coverage includes strict JSON attacks, envelope/gzip aliasing, private-view asymmetry, malformed frame cardinality, failed-order separation, seed-lag accounting, terminal identity, cash-gap ranking, real CLI output, bounded incremental decompression, truncated gzip rejection, and plain-input size enforcement.

Authoritative hosted carrier: `.github/workflows/titan-top-replay-program-diff-sol-orrery.yml`. It pins the exact event head, compiles all four Python paths, executes both test modules, and retains exact source hashes even on failure.

## First real evidence gate

No raw replay or score claim is fabricated in this change. The first real consumer must supply bytes whose gzip SHA-256 is `9337c7c734eff0804400f732d48c155dedb6d6f12b3afdefbc620f78fdfc686b` or whose canonical JSON SHA-256 is `81ee3b351d511a720b526600ceb87a58f25c6a00d2ae1b837c5fd4caf33df77c`, then retain `ORRERY.json` and `ORRERY.md` before proposing a policy.

## Scope

Final diff is seven additive paths: two documentation/receipt files, bounded facade, byte-stable analysis core, two test modules, and one path-scoped workflow. No canonical/frozen runtime, config, archive, pointer, provider, Kaggle submission, or gameplay result changes.
