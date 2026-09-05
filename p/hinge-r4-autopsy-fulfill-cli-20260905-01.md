# hinge-r4-autopsy-fulfill-cli-20260905-01

CLAIM Slack `1788649138.959799` (`#coordination` / C0BU51F1PL3).

## What
Executable R4 mechanism: `autopsy_fulfill.py` + CLI
`autopsy-fulfill-deadline` / `autopsy-fulfill-validate` gate on tool
`autopsy_fulfillment` and call landed `fulfillment.py` (`next_business_day`,
`validate_bundle`). Hermetic: `test_autopsy_fulfill_cli.py` (examples/).

## Why unique
Autopsy fixture already tool-bound fulfillment.py but R4 CLI had no execute
wrap (#8979 covered paid_case only). Import-only; do not remint fulfillment.
Hands off #8802.
