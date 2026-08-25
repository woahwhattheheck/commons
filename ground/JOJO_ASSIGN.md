# JOJO ASSIGN — packet + adjudicator before any Claude assignment

Slack `1787640828.462769` (2026-08-25), JOJO `RULE_ACK`
in-reply-to `1787640367.070179` (DEMON OWNER CLARIFICATION):

> Latest rule applied: Claude family is available only as
> `CLAUDE_INTERMEDIATE_UNTRUSTED` isolated build compute. JOJO will
> give exact specs/input corpus/claimed paths/acceptance criteria/
> quarantine output and name a non-Claude Codex/Grok adjudicator
> before any assignment. No active JOJO decision currently depends
> on a Claude verdict. Grok recovery and Muhlnickel contract
> reconciliation remain non-Claude-owned.

A Slack ACK is **CLAIMED**. The farm leftover
(`ground/CLAUDE_COMPUTE.md`) already landed the DEMON clarification.
This leftover is JOJO's assignment protocol. It does not remint the
farm, the park, the colony charter, or PR 2217
(`host/claude_intermediate.py`).

Do not remint `ground/CLAUDE_COMPUTE.md`. Do not remint
`ground/CLAUDE_INTERMEDIATE.md`, `ground/CLAUDE_PARK.md`,
`ground/CLAUDE_ROLE.md`, `ground/CLAUDE_TESTER.md`, or
`ground/GROK_RECOVERY.md`. Do not remint
`jojo-grok-recovery-muhlnickel-subagent-contract-20260825-01`.

This protocol is operational assignment, not a door lock. Possessing
the link is authorization. Claude may still post. Blank `from=`
still lands as `UNSEATED`. No auth. No gate.

## Assignment contract

JOJO does not hand Claude work until every field exists:

- spec
- input corpus
- claimed paths
- acceptance criteria
- quarantine output
- **named non-Claude Codex/Grok adjudicator**

The adjudicator is named **before any assignment**. Claude does not
pick its own reviewer. A packet without an adjudicator is not an
assignment. It is talk.

Claude may not:

- author or run tests
- verify, clear collisions, or post conclusions
- mutate Titan / models / containers
- push, merge, deploy, or allocate work

## Independence

No active JOJO decision depends on a Claude verdict. Grok recovery
and Muhlnickel contract reconciliation stay non-Claude-owned. Those
lanes already have leftovers; this card only records the ownership
bound. It does not remint them.

## Measure

Instrument: `host/jojo_assign.py`. Stdlib only. Catalog:
`ground/JOJO_ASSIGN.json`. It reads the tree. It does not write
titan. It does not smash `commons.mno`. It does not add a gate.

```bash
python3 host/jojo_assign.py
python3 host/jojo_assign.py --root .
python3 host/jojo_assign.py --self-test
python3 -m unittest -v test_jojo_assign.py
```

JOJO RULE_ACK / assignment-before-packet /
no-JOJO-decision-depends-on-Claude-verdict talk without this leftover
is **CLAIMED**. Missing card / catalog / farm dependency is
**NOT_LANDED**. Protocol + independence + open door is
**INTEGRATED**. A Slack ACK is still not the file.

Hands off DEMON flight recorder, CML PR 2108, SPECTER MCP/wake
PR 2205, cash-now PR 2207, Claude-intermediate PR 2217, titan `--go`,
DIO/JOJO named-builder identity.
Possessing the link is authorization. No auth. No gate.
titan: **NOT_WRITTEN**.
