# T07: a runnable public opponent and a conditional timing result

**Decision (2026-09-07): retain Barnyard Economist V7 as a research opponent;
do not promote it over intact Arlene/Apex.** It loses all 16 primary games.
A separate, development-only flag ablation demonstrates a useful near-clone
preemption mechanism without turning that whole-policy loss into a win claim.

This directory combines three completed, non-overlapping components:
ORBIT's runtime and measured evidence (initial PR9910), HARBOR's public source
normalizer (PR9914, merge f90628e6e0d6d72e28805f194a21696b1fe6d7d8), and
ELM's lineage tooling (PR9921, merge 043180b0549e35b472a71a732209bb36b73fbb52).
Coordination: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805905702659

## What is directly usable

`runtime/barnyard-v7/main.py` is the unchanged public policy, with its complete
LICENSE, NOTICE.md and pre-test SOURCE.json. The existing official file-agent
adapter loads its last callable, `_kaggle_submission_entrypoint(obs)`. The
policy imports only Python standard-library modules. Keep the package's
notices and source receipt together when reusing it.

`runtime/panel.py` runs both seats against intact Arlene/Apex through the
existing process-isolated evaluator and pinned official interpreter. It
freezes dependencies, preserves failures separately, supports bounded resume
and exact baseline reuse, and records full transitions. It does not replace
T09's league or the existing source export. `runtime/README.md` preserves the
original eight-control checkpoint and runner commands.

`runtime/replay_mechanisms.py` imports the explicitly reviewed policy and
replays saved observations while observing branch changes. It verifies exact
action parity, reports exceptions, and restores wrapped functions. This is an
observed-trajectory diagnosis, not an alternative game or a causal estimate.

`runtime/nearclone/run.py` provides the distinct flag-only ablation below.
`results/read_reports.py` reads all original game reports, source freezes,
branch-replay results and the initial failed wrapper bytes without executing
another game. All three small binary parts are already in `results/`.

## Source, license and lineage

Author: Roman Rozen (`romanrozen`). Public notebook:
https://www.kaggle.com/code/romanrozen/strong-barnyard-economist?scriptVersionId=341074820

The fixed download and public pull have identical source/type values in all
31 notebook cells. The policy is cell15 with only its first `%%writefile
main.py` line removed: 27,244 bytes, SHA-256
`997e6bfc5234534e246e945bc61c87858ebf997ab85b0a5c9427dd4ed710f1b6`.
The fixed download identifies scriptVersionId341074820; the pull's separate
currentVersionNumber is7. They are not interchangeable identifiers.
HARBOR's `source_retrieval/normalize_barnyard.py` reproduces this binding from
existing artifact10031005553; no new retrieval is required.

**License evidence limitation:** HARBOR found an explicit Apache-2.0 declaration
in Kaggle's indexed legacy public page, which redirects to the requested V7.
The rendered body was empty and the pull metadata has no license field.
`source_retrieval/LICENSE-EVIDENCE.json` preserves that evidence rather than
borrowing another policy's license or claiming a rendered declaration. The
package includes the standard Apache text and Roman Rozen attribution.

ELM's `lineage/RESULTS.json` compares all four Arlene routes, both Apex tapes,
all three Kaito routes and Breaking the Tie V12. No exact source/AST/full raw
route identity was found. Literal data inequality is **not** proof of
independent authorship or different behavior. Breaking V12 already contains
near-mirror premium front-running; the general mechanism is not new. The
specific Barnyard schedule prefers3, then2, then1-turn advance and tracks a
quantity reduction on the original due turn. The pre-test SOURCE.json records
that historical references were then missing; ELM subsequently closed that
input gap. We preserve the original frozen receipt rather than rewrite it.

## Primary comparison: 32 distinct completed games

Official engine: Kaggle/kaggle-environments
`28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
Intact Arlene SHA-256:
`1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`.
Apex's complete vendor source, compiled library and existing loader/guard
bytes are frozen in each raw report. Source/dependency artifact10030763484
and engine artifact10005621438 were reused, not regenerated.

All four assigned seeds were searched for prior consumption before execution.
Development:9770001/9770019; held:9770101/9770119. Both seats are included.
The V7 package was frozen before its first development game and unchanged
before held evaluation. Eight original development controls were reused;
there are32 unique primary games, not40 just because one report embeds them.
Every game completed719 decisions, with zero primary runtime failures.

| Panel | Arlene control vs Arlene | Arlene control vs Apex | Barnyard vs Arlene | Barnyard vs Apex |
| --- | --- | --- | --- | --- |
| Development | 4 ties | 4 wins | 4 losses | 4 losses |
| Held | 4 ties | 4 wins | 4 losses | 4 losses |

Terminal cash is Barnyard / rival. Each row represents both seat orders, which
had identical role-specific cash; the raw reports retain every individual row.

| Panel | Seed | Rival | Terminal cash |
| --- | --- | --- | --- |
| Development | 9770001 | Arlene | 47,943 / 86,862 |
| Development | 9770001 | Apex | 46,376 / 77,819 |
| Development | 9770019 | Arlene | 68,509 / 107,558 |
| Development | 9770019 | Apex | 67,006 / 106,344 |
| Held | 9770101 | Arlene | 90,482 / 126,672 |
| Held | 9770101 | Apex | 90,011 / 121,365 |
| Held | 9770119 | Arlene | 92,687 / 119,351 |
| Held | 9770119 | Apex | 91,820 / 118,959 |

Every paired outcome worsened:4 ties-to-losses and4 wins-to-losses per panel.
Mean own-cash / relative-margin changes versus the paired controls were
-59,200.25 / -40,791 on development and -16,386 / -35,063.75 on held.
Maximum measured actor call across the primary bank:32.974ms, including
initial source loading. This is local pinned-engine evidence, not a hosted
Kaggle rating. Historical index3034.8 is not current strength evidence.

## Why a negative whole-policy result did not settle the mechanism

Replay of all5,752 recorded Barnyard development actions reproduces every
action exactly, with zero hook errors. Preemption, repayment and weed-repair
hooks never changed an action; SELL ranking changed96 actions. Consequently,
those losses do not exercise the near-clone preemption condition.

The published source checks public farm-structure similarity, remaining shed
inventory, sale slots, future sales in its own fixed route and premium prices.
It advances eligible sales and reduces the corresponding later requests.
This uses the agent's own published schedule, not hidden rival future actions.
Two development losses vs Arlene had360 HARVEST requests each versus481/468
in paired controls. Those are requested actions, not successful yields or a
proven causal explanation of the cash loss.

ELM additionally identified a mismatch between Barnyard's local price model
and the pinned engine's CARROT/TOMATO/EGG curves. Do not transplant that price
proxy into TITAN. T12's exact-market adapter is the mechanism-reuse boundary;
this public opponent remains unmodified.

## Development-only near-clone ablation

After the primary comparison, the separately announced diagnostic uses only
9770001/9770019, both seats. Baseline is unchanged V7 versus itself. The test
arm is the same source loaded by `nearclone/no_preempt.py`, changing only
`_PREEMPT_ENABLED=False`, against unchanged V7. This is an exploratory
conditional result, not held validation, a new primary panel or promotion.

| Seed | ON / ON self-play | OFF / ON duel | ON winning margin |
| --- | --- | --- | --- |
| 9770001 | 104,778 / 104,778 | 103,663 / 106,380 | 2,717 |
| 9770019 | 100,072 / 100,072 | 99,029 / 100,940 | 1,911 |

Both seats produce the same role-specific scores:4 self-play ties and4 losses
for OFF. Disabling the flag reduces own cash by1,115/1,043 relative to the
paired self-play controls. Replaying all2,876 ON-rival observations exactly
reproduces its actions, with15 preemptions and15 repayments per game and zero
hook errors. This discriminates the missing condition: the timing mechanism
helps in these near-clone games even though the whole policy loses to the
primary controls. It does not establish an unconditional market edge.

The initial wrapper had two step0 setup crashes because the pinned file loader
does not define `__file__`. Both failures and the original wrapper/driver are
retained in the raw archive. The repair lazily resolves the source from the
official `configuration['__raw_path__']` and has a real-loader regression.
It received a new source freeze/output; the original frozen V7 was unchanged.
Two completed, unchanged self-play controls were reused rather than rerun.

Across primary and diagnostic work there are42 unique attempts:40 completed
games and2 preserved setup failures. Do not count reused rows as new games,
and do not describe the setup crashes as economic losses.

## Reproduction and evidence access

From this directory, in the existing Linux cloud tree with the pinned source
pack, engine, g++ and libseccomp:

```sh
python -m unittest discover -s runtime -p 'test_*.py' -v
python results/read_reports.py
python results/read_reports.py --write-archive /tmp/t07-reports.tar.xz
```

Actual result:24 tests pass, including source preservation, official-loader
compatibility, branch parity/error behavior, report corruption detection,
failed-run accounting and paired baseline reuse. The included initial-observation
fixture is decision0/seat0 from the existing9770001 Arlene self-play trace,
not a new game. Python syntax compilation also passes. No whole-repository CI
success is asserted by these local results.

The combined raw report archive is24,920 bytes, SHA-256
`b4514c75131ccc2929114004fc90b3519ea343ef5cabe39aedee8a85ebe5e369`.
The three transport parts reproduce exactly14 original members /913,043
uncompressed bytes. They contain all five complete game reports, five source
freezes, both complete branch-replay analyses and both failed-wrapper sources.
The reader verifies each part, the combined bytes and duplicate accounting.
It makes no network request and does not execute the archived policy or failure.

**Full before/after transition traces are not in those three parts.** They
remain preserved in the producing cloud evidence archive; every raw game
report records its full-trace SHA-256. The published source/seeds also reproduce
new traces through the existing runner. A raw trace hash is not a claim that
its full bytes were included in the report archive.

Primary fresh-run example (use a new result directory):

```sh
python runtime/panel.py --runtime /tmp/t07-runtime --engine-dir /path/to/engine \
  --candidate runtime/barnyard-v7/main.py --candidate-root runtime/barnyard-v7 \
  --output /tmp/t07-new/development.json --freeze-only
# Remove --freeze-only and add --max-new-games 4 for bounded execution.
# Use --panel held only for the predeclared unchanged held comparison.
```

Near-clone fresh-run example, not an instruction to repeat completed seeds:

```sh
python runtime/nearclone/run.py --runtime /tmp/t07-runtime --engine-dir /path/to/engine \
  --output /tmp/t07-new/nearclone.json --freeze-only
# Remove --freeze-only and add --max-new-games 4 for bounded execution.
```

The optional near-clone `--baseline-report` accepts only matching original
source, infrastructure, seeds and original adapter. Failed candidate rows are
never imported as baseline outcomes. Runtime paths and native-library bytes
participate in identity, so relocation/recompilation starts a new freeze.

No Kaggle upload, new spending, owner-PC execution, hosted score, revenue,
independent-authorship proof or unconditional superiority is claimed.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
