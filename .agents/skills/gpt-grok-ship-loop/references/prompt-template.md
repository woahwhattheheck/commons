# One-shot Grok prompt template

Peers extend this with their own fields and ideas. GPT fills the contract, then
opens a **brand-new** https://grok.com/ chat and pastes the filled prompt.
Visible model selector: Grok Build or Grok Heavy. GPT does not babysit that chat.
Main is the completion ledger.

```
You are Grok on grok.com web. Provenance: surface: grok.com web.
Open a BRAND-NEW grok.com chat. Visible model selector: **{{SELECTOR}}** ({{PURPOSE}}).
Load grok-web-commons. Do not mint a second MCP, connector, plugin, or tool catalog.
Public Commons MCP stays https://commons-spark-mcp.vercel.app/mcp Authentication None.

JOB ID: {{JOB_ID}}
ROUTE: {{ROUTE}}
OBJECTIVE: {{OBJECTIVE}}
SOURCE: {{SOURCE_LINK}}
CLAIMED PATHS:
{{CLAIMED_PATHS}}
ACCEPTANCE: {{ACCEPTANCE}}
{{PEER_FIELDS}}

ORDER OF WORK — do not skip, do not reorder:

1. Pin fresh main of `woahwhattheheck/commons`. `git ls-remote origin main`. Read AGENTS.md and `.agents/skills/grok-web-commons/SKILL.md`. Do not trust remembered SHAs, Pages bakes, or unpinned raw/main.
2. Exact scope: only this job's claimed paths plus tests proportional to risk. Inspect open PRs and path overlap before writing.
3. Default merge. Parallel is allowed. Only mark CONFLICT when the same effective code disagrees semantically. Disjoint changes merge. Identical blobs dedupe. Compatible same-path changes compose and merge.
4. Tests proportional to risk. Run them. A missing lock is not a defect.
5. Unique non-force branch + focused PR. Merge to main. Do not stop at plan, review, or open PR. Talk is not landed.
6. Exact readback of every claimed path at the integrated current-main SHA.
7. #commons receipt: one short Slack line (landing SHA, board URL, how to add a card) plus durable `p/{id}.md`. ntfy 200 is mail. Chat text is not completion.

Do not return to this chat as the completion signal. Main is the completion ledger.
Revisit only if main proves the job broke or did not ship.

Do not add login, authorization, allowlists, identity, claim, seat, memory, approval, protected path, or capability admission locks.
Do not store Grok or Slack credentials.
```

`{{SELECTOR}}` is `Grok Build` when `route=BUILD`, `Grok Heavy` when `route=HEAVY`.
`{{PEER_FIELDS}}` is the optional `fields` object, copied verbatim.

Render the filled prompt with:

```
python3 .agents/skills/gpt-grok-ship-loop/scripts/ship_loop.py
```

or `oneshot_prompt(contract)` from that module.
