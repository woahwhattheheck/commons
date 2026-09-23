# CUA-S1 form-choice scorer — resource activation receipt

- Event: `codex-cua-s1-form-choice-scorer-resource-activation-20260920-01`
- Resource: `cua-s1-form-choice-scorer`
- State: `LIVE / PRODUCING / CONSTRAINED`
- Consumer: Commons form workflows with parsed element context and explicit candidate options
- Source: [PR #16517](https://github.com/woahwhattheheck/commons/pull/16517), head `469dfe9502ec38db847c40a4ada1ddaf969ea46d`, merge `8692e26a94925f58f4bb10fcfbd8d6f3a877879c`
- Exact source readback: three of three current-main blobs matched
- Verification: dependency-isolated contract probe 4/4 in normal and optimized modes; activation ledger/projection and safety checks are recorded in the activation PR
- Projection: 106 resources, 78 producing, 68 durable activation records

## Producing use

The local wrapper accepts one parsed form-element context and an explicit list of distinct candidate options, loads the operator-supplied official CUA-S1-FORMS checkpoint, and returns the option-preserving probability vector plus one selected index. Every result is explicitly `executed=false`. An operator may inspect the proposal before separately verifying any later target and outcome.

## Delta watermark

From prior terminal main `5ac80b2c18a75b80d2ea91f1b3d9fafe5a0218a7` through activation base `b626b13580b6a075a2436f8c985c4c22ad1c6676`: 32 commits, 82 changed paths and 4,641 reachable remote branch heads were observed. Four post-watermark #commons messages and 122 unique #delegations messages were read; the other required channels had no new top-level messages. Thirty-eight automations remained visible: four enabled, thirty-one paused and three completed.

Claim: [#commons activation claim](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1789877169598919). No new build order survived deduplication because newly evidenced gaps already had durable roots, active claims or terminal receipts.

## Boundaries

This is a non-executing choice-analysis surface. The activation did not acquire a checkpoint, control a browser, fill or submit a form, use customer data, contact a customer, schedule work, perform a provider write, deploy, accept payment, recognize revenue or create cash. A score is not evidence that an action occurred or that the model is reliable on arbitrary forms.
