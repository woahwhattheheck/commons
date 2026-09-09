# Agent Skills (literal)

These folders follow [agentskills.io](https://agentskills.io/specification): each directory is a skill, each `SKILL.md` has `name` + `description` frontmatter.

Discovery path: `.agents/skills/` (cross-client). Human index: [skills/MANUAL.md](../skills/MANUAL.md). Facts only: [ground/tokens/](../ground/tokens/).

**Connector bootstrap:** if GitHub or Slack looks read-only, missing write actions, or "unable to post", first run unfiltered connector discovery with `api_tool.list_resources({"paths":["GitHub","Slack"]})` and omit `query`. A filtered empty result, shell DNS failure, or missing shell git credentials is not evidence that connector writes are unavailable. Invoke an actually discovered write action and retain its success/error receipt before declaring publication blocked. See [write-roads](skills/write-roads/SKILL.md).

Point a worker at the manual. One job. One file.
