# H4 + L3 joint practice arm

Base: `riot/v3.1-lanes@dc1779ed79cd7fdd091187df1e8f0c4e5f185555`.

Purpose: evaluate the already-gated H4 strawberry same-row reservation mechanism together with Riot L3 `no_late_sale_advance`, without claiming integration, changing package inputs, enabling defaults, or submitting Kaggle.

**Fidelity boundary:** this arm lives under `experiments/**`, outside the deterministic `build_v3.py` package inputs. Under the fleet SIM FIDELITY STANDARD it is a **practice/bench arm, not a 1:1 official gate candidate**. Any official promotion receipt must instead use a candidate built from the pinned canonical archive, the blob-verified official interpreter, live-submission TITAN-CONFIG, the frozen official paired-seat panel, and an exact stated opponent identity.

The H4 module/test/screen files are copied by exact Git blob from PR #12344's hardened source. `joint_arm.install_joint()` pins the live V3.1 R04 baseline before enabling H4 + L3@648:

- `r04_sale_horizon = 8`
- `r04_open_roundtrip = 0`
- `r04_row_order = true`
- `r04_evening_flush = true`
- `r04_sale_fertilizer = true`
- `r04_cattle_early = true`
- H4 strawberry top-up = on
- L3 no-late-sale-advance = on at cutoff 648

The arm fails closed on a non-baseline override instead of inheriting `r04_full_router.py`'s source defaults. H4's `reconcile_strawberry()` detects the L3 globals and returns exact identity/no-debt at and after the cutoff.

Source gates before spending practice evaluator budget:

- Riot branch baseline: 161/161 V3 tests (Riot's published receipt).
- H4 focused suite: 13/13, including the 640-eligible / 648-veto predecessor.
- H4 structural screen: 13 tapes, 372 opportunities total, 292 pre-648, 80 at/after 648.
- import-time + CI guard proving the exact live V3.1 R04 knob values, H4 ON, L3 ON/cutoff648, and rejection of non-baseline overrides.
- Experiment files remain outside `overlay/**`; this arm is packaging-neutral.

Useful practice comparisons use identical seeds/seats/opponents for all arms:

1. **L3 vs V3.1** — preserve L3's standalone reference receipt.
2. **H4+L3 vs L3** — estimate H4 incremental value after L3 removes late advancement.
3. **H4+L3 vs V3.1** — estimate stack value and interaction.

Report mean/median paired ΔM, W/T/L transitions, positive/negative cells, H4 activation count+quantity split pre/post-648 (post must be zero), L3 suppressed-step telemetry, and process/deadline failures. Reject the joint practice arm if any H4 post-648 activation/debt appears, if composition creates new failures, or if incremental H4-vs-L3 economics are non-positive on the chosen panel.

Historical standalone evidence is context, not a joint or fidelity-qualified result: Riot L3 reported +152.2 mean ΔM over 60 paired games / 3 opponents, 58/60 positive; H4 reported an independent 16/16 gate at +36.5 mean ΔM and a separate frozen 16-game panel at +97.625 mean ΔM. Re-evaluate those labels against the current SIM FIDELITY STANDARD before using them for promotion.
