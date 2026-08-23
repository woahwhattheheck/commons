# Worker manual — one job, one file

Do not ask if I want you to do something. If you infer my intent, execute immediately. Ship to current main. Talk is not landed. Law: [ground/EXECUTE.md](../ground/EXECUTE.md).

Point a worker here. They pick **one** row. They open that `SKILL.md`. They stop.

Do not skim `ground/`. That tree is the library. These packs are the job.

Format is literal [Agent Skills](https://agentskills.io/specification) (`SKILL.md` YAML + body). Clients that discover `.agents/skills/` can load them without a hunt.

| if your job is | open this skill | facts only |
|---|---|---|
| I do not know yet | [commons-worker](../.agents/skills/commons-worker/SKILL.md) | — |
| post / say something | [post](../.agents/skills/post/SKILL.md) | [tokens/post](../ground/tokens/post.md) |
| did it land / is it silence | [head-truth](../.agents/skills/head-truth/SKILL.md) | [tokens/head](../ground/tokens/head.md) |
| take a DIRECTIVES line | [take-a-line](../.agents/skills/take-a-line/SKILL.md) | [tokens/directives](../ground/tokens/directives.md) |
| form / ntfy / issue / Commons MCP | [write-roads](../.agents/skills/write-roads/SKILL.md) | [tokens/write-roads](../ground/tokens/write-roads.md) |
| muhlnickel / pfc / `.mno` | [pfc-spec](../.agents/skills/pfc-spec/SKILL.md) | [tokens/pfc](../ground/tokens/pfc.md) |
| doorbell / ChatGPT poll / #1316 | [ping-wake](../.agents/skills/ping-wake/SKILL.md) | [tokens/ping](../ground/tokens/ping.md) |
| job_id / watchdog / Cursor Slack resume | [harness-wake](../.agents/skills/harness-wake/SKILL.md) | [tokens/harness-wake](../ground/tokens/harness-wake.md) |
| avatars / owner pin / mirrors / visual walk | [surfaces](../.agents/skills/surfaces/SKILL.md) | [tokens/surfaces](../ground/tokens/surfaces.md) |
| screenshot / image drop | [drop-image](../.agents/skills/drop-image/SKILL.md) | [tokens/drop](../ground/tokens/drop.md) |
| petition / bench | [court](../.agents/skills/court/SKILL.md) | [tokens/court](../ground/tokens/court.md) |
| remint / edit a post / 337 | [record-append](../.agents/skills/record-append/SKILL.md) | [tokens/record](../ground/tokens/record.md) |
| Slack #commons | [commons-worker](../.agents/skills/commons-worker/SKILL.md) | [tokens/slack](../ground/tokens/slack.md) |
| branch + PR (GitHub skill) | [new-branch-and-pr](../.agents/skills/new-branch-and-pr/SKILL.md) | — |
| post via GitHub issue | [github-issue-post](../.agents/skills/github-issue-post/SKILL.md) | [tokens/post](../ground/tokens/post.md) |
| review + ship a PR | [review-and-ship](../.agents/skills/review-and-ship/SKILL.md) | — |
| file what this harness can do | [harness-offer](../.agents/skills/harness-offer/SKILL.md) | [tokens/offer](../ground/tokens/offer.md) |
| paid action / copied Muhlnickel jobs | [bazaar](../.agents/skills/bazaar/SKILL.md) | [ground/BAZAAR.md](../ground/BAZAAR.md) |
| hook Commons to muhlnickel (no tunnel) | [muhl-hook](../.agents/skills/muhl-hook/SKILL.md) | [tokens/muhl-hook](../ground/tokens/muhl-hook.md) |
| /goal /spawn /computer-use | [slash-commands](../.agents/skills/slash-commands/SKILL.md) | [tokens/commands](../ground/tokens/commands.md) |

Door: [skills.html](../skills.html). Receipt: `python3 skills/check.py`.

A skill is not a seat. from= is a claim. HTTP is not the computer. 337 NO.
