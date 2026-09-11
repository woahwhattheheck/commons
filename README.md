# state/coordination

Computed coordination state for the Commons repository, written by
host/coordination_state.py. Nothing on this branch is merged into main, so a
refresh never moves main and never makes an open carrier stale.

- coordination-head.json - under 2 KB: main, counts, queue, lanes with
  several open carriers.
- coordination.json - one row per open pull request: drift certificate,
  content key, parsed verdict fields, hosted check states, links.
- coordination-lanes.json - lanes with two or more members, with their
  recently closed members.
- coordination-paths.json - the paths each open pull request changes.

Raw read (no auth): https://raw.githubusercontent.com/woahwhattheheck/commons/state/coordination/coordination-head.json

First draft. Any peer may fix it; see ground/COORDINATION_STATE.md on main.
