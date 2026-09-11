# TITAN V3.1 fleet convergence ledger

Status: **integration routing / decision custody**. This file does not itself enable gameplay, change `TITAN-CONFIG`, rebuild a package, or authorize a Kaggle submission.

Last coordinated: 2026-09-11 05:22 EDT.

## One integration line

Frozen acceptance base: `titan/v3.1-20260911@508b342fc46fa91e3d7cdc3f0b7e44934a187c14`.

Current convergence root: PR #12432 exact head `d6746b923af8afc383ce7331fe44a6c971aa0fbe`, which composes the reviewed #12392 immutable-canonical/package-integrity stack with the reviewed reachability guard and executes both on one head.

Every fleet lane must end in exactly one durable disposition:

- `CONVERGENCE_READY`: source/economics/custody gates needed for its claimed authority are terminal and the lane publishes a current-root child or exact-byte handoff for integration.
- `HOLD`: useful source/evidence exists, but a named blocker remains. Preserve the exact head and blocker; do not promote.
- `REJECT`: preserve the negative result so the fleet does not spend the same lane again.

A positive experiment that remains only on a sibling branch is not finished. A rejected experiment whose evidence is not preserved is also not finished.

## Integration order

1. **Custody first** — #12392 + #12432 package-integrity/materialized-reachability stack.
2. **Correctness and evidence infrastructure** — consume current-base correctness/tooling carriers only after their exact-head gates pass. This includes E20 executable-prefix parity (#12405), official-receipt validation (#12388 and any strict-type successor), seat-aware delta normalization (#12402 successor), and the D3 externality gate (#12425 successor).
3. **Gameplay candidates** — compose only candidates with paired competitive `DeltaM`, exact opponent identity, exact seed/seat cells, and package/interpreter custody. Strongest mature candidate is H4 (#12419), intentionally **without L3**.
4. **Interaction gate** — after each gameplay addition, rerun representative opponents and the externality gate on the combined stack. Do not infer composition safety from singleton wins.
5. **Promotion wiring** — only after the combined current-root head is green should a distinct integration step alter shipped overlay/config/package inputs. Experiments under `experiments/**` are evidence, not production wiring.

## Current lane routing

### Root / infrastructure

- **#12432 materialized reachability x frozen canonical** — `HOLD` until exact-head review plus dedicated reachability, package-integrity, and generic workflows are terminal green. Exact head: `d6746b923af8afc383ce7331fe44a6c971aa0fbe`. This is the current convergence root.
- **#12405 E20 executable-prefix parity** — `HOLD` for exact-head rereview/checks; correctness carrier, not a strategy experiment. If green, recompose onto the convergence root rather than leaving it as a sibling of 508b.
- **#12388 official-gate receipt validator** — `HOLD` while strict metadata/type predecessors are being closed. Its job is to stop practice receipts from masquerading as official evidence.
- **#12402 delta normalization / #12425 D3 externality gate** — `HOLD` pending the inherited evidence-family/seat-normalization repair identified by review. D3 is mandatory before gameplay promotion because positive own score can hide rival-fattening/shared-market harm.
- **#12431 fast-clone exact-head proof** — `HOLD` pending exact-head hosted proof. Throughput optimization only; no gameplay-policy authority. Consume only if equality + fallback killers + speed threshold hold on exact custody.

### Gameplay candidates with positive evidence

- **H4 strawberry top-up #12419** — `HOLD`, first promotion candidate after root custody. Exact head `0ac88a0c210c0c52ef9da53de85dd1c0528d8eae`. Evidence carried from reviewed H4: frozen panel 16/16 positive, mean paired DeltaM +97.625; independent panel 16/16 positive, mean +40.125; additive 41-recorded-game result reported +32.6 margin/game over V3.1 on the same games. L3 is intentionally absent. Required: terminal exact-head H4 workflow + root custody/reachability + combined-stack externality check.
- **C1 intertemporal MR SELL cap** — `HOLD / PUBLICATION REQUIRED`. Latest coordinated Arlene screen: 14 positive / 2 zero / 0 negative, mean paired DeltaM +53, median +55. Do not lose this in chat: publisher must create an experiment/evidence PR and, if wider gate survives, a current-root convergence child.
- **H3b max-held-aware sheep harvest #12435** — `HOLD`. Source carrier exists. Latest coordinated small Arlene screen reported 6 positive / 2 zero / 0 negative, mean paired DeltaM +134 with bounded hour-23 overflow harvest behavior. Economics/custody must be committed and widened before promotion.
- **B5 CARROT fertilizer #12420** — `HOLD`. Mechanism screen 16/16 positive vs frozen Arlene, mean +89.125, but that screen is not the full 1:1 promotion gate; strict materialization and opponent-diverse unilateral DeltaM are required.
- **B5 JIT PASS->FERTILIZE #12428** — `HOLD`. Practice evidence 10 positive / 6 zero / 0 negative, mean +41.0 with one causal activation in positive cells; exact-head/materialized official gate and source-predecessor review remain required.

### Measurement / conditional successors

- **L3 default-on #12377** — `HOLD / DO NOT PROMOTE`. Positive Arlene evidence is real, but direct exact-V3.1 competition reverses sign (raw-score custody preserved by #12390/#12421). The old `riot/v3.1-l3-merge-ready` branch is provenance only, not current merge authority.
- **L3 public supply gate #12418** — `HOLD`. Source lower-bound idea is useful, but strict input/fresh-lookback fail-closed repairs and wider exact-package economics are required.
- **L3 public tape-regime measurement #12429** — `HOLD`. `gate_ready=false` by design until the 41-game public classifier confusion matrix / earliest stable label is measured. No gameplay wiring before that.
- **B11 public structural mirror horizon #12438** — `HOLD`. Designed to retain horizon-10 only in a strict public mirror regime after unconditional horizon-10 rejection. Must prove it stays horizon-8-identical in Arlene-like loss regimes while retaining material mirror benefit.
- **E7 post-town-tick sale timing #12430** — `HOLD`. Source-safe experiment; needs exact paired activation/economics and all negative cells.
- **E5 terminal floor liquidation #12424** — `HOLD / CHEAP ACTIVATION CENSUS FIRST`. Earlier broad E5 evidence showed zero activations; do not spend a wide gate until this exact bounded arm proves nonzero realized terminal monetization.

### Rejected / consumed lanes

- **H13 fixed sale horizon 10 #12415** — `REJECT` as an unconditional policy. Large self-play gain but 0+/8-/0= vs exact Arlene, mean paired DeltaM -662; every cell lowered TITAN and raised rival.
- **H10B unilateral sale deferral #12403** — `REJECT` for promotion. Ownership repair can be source-correct while unilateral exact-V3.1 competition is negative (-170/-220 on the diagnostic seeds); shared-market free-riding is the failure mode.
- **H9** — `REJECT`; 4/4 massively negative against exact V3.1/Arlene in the coordinated screen. No wider spend.
- **Generic D5 tight-game risk dial** — `REJECT / NO-LANE`; terminal reward is farm money and the proposed additive margin dial has no treatment-effect mechanism by itself.
- **Generic D6 wool regime detector** — `REJECT / DUPLICATE`; equivalent regime logic already exists in V233.
- **Broad D4 strawberry timing** — `REJECT / DUPLICATE AS STATED`; current R04/E184/evening-flush already consumes most of the proposed surface. Only a genuinely distinct, measured temporal seam should continue.
- **M1 generic plan-aware wrapper** — `REJECT / NARROW`; current route/plan machinery already encodes much of the premise. Only route-regeneration or a proven missing policy seam justifies a successor.

## Fleet collision rules

- Search the exact lane marker and PR before claiming work. Earlier owner wins.
- A5, B7, and D5 have already shown duplicate-claim churn; prefer reviewing/running/composing an existing lane over creating another sibling.
- Do not call queued/null Actions green.
- Do not inherit economics across a changed gameplay stack without rerunning the paired gate.
- Do not use self-play alone as promotion evidence after the L3/H13/H10B opponent-externality failures.
- Keep opponent bytes, interpreter/package identity, seed/seat cells, own/rival score deltas, DeltaM, activation telemetry, and every negative transition in the handoff.

## Immediate convergence queue

1. Terminalize #12432 review/workflows.
2. Terminalize H4 #12419 exact-head workflow and compose H4 onto the current convergence root if green.
3. Recompose green correctness/tooling carriers (#12405 and repaired evidence gates) onto the same root.
4. Publish C1 evidence so its current positive screen cannot disappear in Slack history.
5. Bind H3b economics to exact head and widen representative opponents.
6. Run B5 CARROT adversarial/unilateral check before spending a wider gate.
7. Consume Muse high-impact A1/A3/A6 lanes only through the same READY/HOLD/REJECT handoff and current-root composition rule.
