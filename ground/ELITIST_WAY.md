# THE ELITIST WAY

Durable operating method. Not a seat. Not a gate. Not a second ship-loop.

Thinking models choose the end result and Bryce's real constraints.
Grok owns implementation and shipping.
GitHub main is the completion ledger. Chat is not.

## The method

1. The thinking model writes a short prompt: **END RESULT**, **fresh-main context**, **BRYCE'S CONSTRAINTS**. Nothing else. Leave design to Grok.
2. Launch one fresh Grok Build or Grok Heavy execution lane for that build. Route is grok.com / SuperGrok Heavy / Grok Build — not Cursor, not Grokbot, not a plan-only chat.
3. Move immediately to the next idea. Do not babysit the lane in chat.
4. Grok implements, tests, opens a unique branch/PR, merges to current `main`, and returns exact readback. Compatible work merges by default. Only same-code semantic disagreement is conflict.
5. Revisit a lane only when official `main` proves it failed or broke.
6. Peers add their own work the same way. Possession of the link is enough. Blank `from=` lands as `UNSEATED`.

Compose with work already present. Do not mint a duplicate review, land, or grok.com skill.

- Lane launch and prompt: this card + [elitist-way skill](../.agents/skills/elitist-way/SKILL.md)
- Integration and current-main readback: [review-and-ship](../.agents/skills/review-and-ship/SKILL.md)
- grok.com connector road: [grok-web-commons](../.agents/skills/grok-web-commons/SKILL.md)
- Land law: [LAND.md](./LAND.md) · [EXECUTE.md](./EXECUTE.md)

## BRYCE'S CONSTRAINTS

Copy these. Do not invent extras. Do not invent code-style rules.

- open public participation
- no auth / account / approval / hold gates
- no fabricated completion
- no secret exposure
- no force / overwrite
- no walking on eggshells
- no code-style rules invented by GPT

## Copy-ready prompt

```
END RESULT: <one sentence naming what every Commons peer can discover, understand, and use after this lane>

Fresh main: https://github.com/woahwhattheheck/commons — start from current main. Compose with work already present; do not create a duplicate system.

BRYCE'S CONSTRAINTS:
- open public participation
- no auth/account/approval/hold gates
- no fabricated completion
- no secret exposure
- no force/overwrite
- no walking on eggshells
- no code-style rules invented by GPT

Leave design to Grok. Grok owns implementation and shipping. GitHub main is the completion ledger. Launch one fresh Grok Build or Grok Heavy lane, then move to the next idea. Revisit only when main proves the lane failed or broke. Carry it through implementation, tests appropriate to what you choose, unique branch/PR, merge to current main, and exact readback. Do not return a plan or leave an unmerged PR.
```

## Completion

A lane is done only when the intended bytes are on official current main and read back at that SHA.

`INTEGRATED — VERIFIED ON CURRENT MAIN`

An open PR, Slack thread, ntfy 200, or chat claim is `CANDIDATE` / `CARRIER_ONLY`, not completion.
