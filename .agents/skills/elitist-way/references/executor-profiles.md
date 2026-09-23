# Executor profiles

This file is the model/provider-specific adapter for **THE ELITIST WAY**. The stable workflow contract stays in `../SKILL.md` and `ground/ELITIST_WAY.md`: one END RESULT, fresh-main context, Bryce's constraints, implementation through merge, and exact current-main readback.

Change this profile when a provider, model selector, or launch surface changes. Do not rewrite the stable task contract for selector churn.

## `grok-web`

Current compatibility profile for the existing workflow.

- surface: `grok.com` web
- `BUILD`: Grok Build — implementation and shipping
- `HEAVY`: Grok Heavy — broad synthesis and integration
- connector guidance: `.agents/skills/grok-web-commons/SKILL.md`
- existing loop machinery: `.agents/skills/gpt-grok-ship-loop/SKILL.md`
- launch rule: one brand-new chat for each build; do not use Cursor, Grokbot, or a plan-only chat as this profile
- handoff: leave design to the execution lane; it carries the stable contract through implementation, appropriately scoped checks, unique non-force branch/PR, merge to current `main`, and exact readback

Profile injection for a BUILD lane:

```text
EXECUTOR PROFILE: grok-web / BUILD
Launch one brand-new grok.com chat with Grok Build. Load grok-web-commons. Carry the stable END RESULT + fresh-main context + BRYCE'S CONSTRAINTS contract through implementation and shipping. Do not stop at a plan or open PR.
```

Profile injection for a HEAVY lane:

```text
EXECUTOR PROFILE: grok-web / HEAVY
Launch one brand-new grok.com chat with Grok Heavy. Load grok-web-commons. Carry the stable END RESULT + fresh-main context + BRYCE'S CONSTRAINTS contract through synthesis, integration, merge, and exact current-main readback. Do not stop at a plan or open PR.
```

## Representative migrated task

`FEED-WORKFLOW-PORTABILITY-0923` uses the same stable contract regardless of selector changes:

```text
END RESULT: model/provider selector changes no longer require rewriting the shared elitist-way task contract.

Fresh main: https://github.com/woahwhattheheck/commons — start from current main and compose with the existing elitist-way and ship-loop paths.

BRYCE'S CONSTRAINTS:
- open public participation
- no auth/account/approval/hold gates
- no fabricated completion
- no secret exposure
- no force/overwrite
- no walking on eggshells
- no code-style rules invented by GPT
```

For the current route, append only one of the `grok-web` profile injections above. A future executor profile should replace that small injection rather than editing the END RESULT, fresh-main contract, constraints, completion rule, or collision law.
