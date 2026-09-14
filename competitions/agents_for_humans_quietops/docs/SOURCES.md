# Source / provenance ledger

Checked 2026-09-13 EDT. These are design inputs, not proof of registration, eligibility, deployment, judging, or prize status.

## Competition

- Agents for Humans Hackathon: https://agentsforhumans.devpost.com/
  - Deadline shown: Sep 14, 2026 @ 5:00 PM PDT.
  - $40,000 total cash prizes across Everyday, Professional, and Good Neighbor tracks.
  - Project must use Strands Agents SDK.
  - Submission requires text description, public source repository with setup instructions and MIT/Apache license, architecture diagram, <=5 minute demo video, and AWS Builder ID.
  - AgentCore deployment is optional and described as strengthening Technical Implementation.
  - AWS Builder post can earn bonus points if published before the deadline under the competition rules.

**Eligibility is not asserted by this repository.** The controlling Devpost rules and the entrant's facts must be checked before registration/submission.

## Strands Agents SDK

- Python quickstart: https://strandsagents.com/docs/user-guide/quickstart/python/
  - package: `strands-agents`
- Agent API: https://strandsagents.com/docs/api/python/strands.agent.agent/
  - `Agent` accepts explicit tools, name and description.
  - decorated `@strands.tool` functions and Agent instances are supported tools.
- Agents as tools: https://strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/
- Tool decorator API: https://strandsagents.com/docs/api/python/strands.tools.decorator/
- AgentCore + Strands memory integration: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/strands-sdk-memory.html

The local verification environment used for this carrier did not have `strands-agents` installed and had no package-network access. Therefore the deterministic core, HTTP product demo, tests, compile checks, and benchmark are locally executed; **live model/provider execution is not claimed**. Strands wiring is written against the current official API documentation above.
