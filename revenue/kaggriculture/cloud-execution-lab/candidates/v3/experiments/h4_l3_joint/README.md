# H4 + L3 joint evaluator arm

Base: `riot/v3.1-lanes@dc1779ed79cd7fdd091187df1e8f0c4e5f185555`.

Purpose: evaluate the already-gated H4 strawberry same-row reservation mechanism together with Riot L3 `no_late_sale_advance`, without claiming integration, changing package inputs, enabling defaults, or submitting Kaggle.

The H4 module/test/screen files are copied by exact Git blob from PR #12344's hardened source. `joint_arm.install_joint()` first installs the normal H4/R04 parameters, then explicitly enables L3 with threshold 648. H4's `reconcile_strawberry()` detects those L3 globals and returns exact identity/no-debt at and after the cutoff.

Source gates before spending evaluator budget:

- Riot branch baseline: 161/161 V3 tests (Riot's published receipt).
- H4 focused suite: 13/13, including the 640-eligible / 648-veto predecessor.
- H4 structural screen: 13 tapes, 372 opportunities total, 292 pre-648, 80 at/after 648.
- Experiment files remain outside `overlay/**`; this arm is packaging-neutral.

Official evaluator request:

1. **L3 vs V3.1** — preserve Riot's published standalone receipt.
2. **H4+L3 vs L3** — measures H4 incremental value after L3 removes late advancement.
3. **H4+L3 vs V3.1** — measures total stack value and interaction.

Use identical seeds/seats/opponents for all three arms. Report mean/median paired ΔM, W/T/L transitions, positive/negative cells, H4 activation count+quantity split pre/post-648 (post must be zero), L3 suppressed-step telemetry, and process/deadline failures. Reject the joint arm if any H4 post-648 activation/debt appears, if composition creates new failures, or if incremental H4-vs-L3 economics are non-positive on the frozen panel.

Current standalone evidence (not a joint result): Riot L3 +152.2 mean ΔM over 60 paired games / 3 opponents, 58/60 positive; H4 independent official gate 16/16 positive at +36.5 mean ΔM, plus a separate frozen 16-game panel at +97.625 mean ΔM.
