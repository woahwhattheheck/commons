# Posted paid work and procurement discovery, 2026-09-05

Three headless Claude runs on the owner PC, driven through the C1 runner (`integrations/claude_headless/claude_headless.py`), each told to find currently open, publicly posted opportunities, fetch every kept posting to confirm it is open, and write one table with an evidence URL per row plus a "Not verified" section. Tools were limited to WebSearch, WebFetch, Write and Read; MCP servers were disabled with `--strict-mcp`; nobody was contacted and nothing was sent. The tables are the children's verbatim output. A row is a lead to check, not a qualified buyer.

| Lane | File | Table rows | Session | Final run | Model | Turns | Cost | Wall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Open RFPs: LIMS / water-quality lab data management (AquaTrace fit) | [lims.md](lims.md) | 3 | `09d878c9…` | `29a84045213d4815` | claude-fable-5 | 145 | $13.82 | 1350.7 s |
| Open solicitations: small-business websites / local SEO (finished-site offer) | [sites.md](sites.md) | 8 | `03fed25d…` | `9be1783ba2824b11` | claude-fable-5 | 138 | $14.52 | 1430.9 s |
| Posted paid work: AI-agent / MCP / Claude integration (diagnostic → proof) | [ai_agent_work.md](ai_agent_work.md) | 13 | `97da070d…` | `7bc00fd86ed64b64` | claude-fable-5 | 47 | $3.53 | 423.7 s |

## Provenance and honesty notes

- The first attempt of each lane (run ids in `provenance.json`) was denied every web call because `--tools` restricts without granting and print mode cannot prompt; each child refused to fabricate and wrote nothing. The lanes were resumed on the same sessions with `--allowed-tools WebSearch,WebFetch,Write,Read --strict-mcp`.
- Due dates and values are as the fetched page stated them at fetch time; re-check before acting.
- Fit scores are the child's judgment against the offers named in the prompt (AquaTrace LIMS; $1,500–$4,000 finished sites; $199 diagnostic → $2,500 proof). They are not underwriting.
- Raw stream-json for every run is on the owner PC under `~/.claude/commons_headless/runs/<run_id>/`.

## Rerun

```
python integrations/claude_headless/claude_headless.py start "<the lane prompt>" --cwd <scratch dir> \
  --permission-mode acceptEdits --allowed-tools WebSearch,WebFetch,Write,Read,Glob,Grep --strict-mcp \
  --label discovery-<lane> --peer <you> --stdin-prompt
```
