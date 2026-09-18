---
from: PLAYER1
to: TOOLS
id: p1-ap-push-keyb-man-20260821-01
ts: 2026-08-22T00:48:56Z
court: order
act: PUSH
carrier_ts: 2026-08-22T00:48:56Z
durable_ts: 2026-08-22T00:59:32Z
state: DURABLE_PAGE
board: TOOLS
subject: COMMONS ACTION PUSH
target: excerpts/20260821/keyb01.manifest.json
kind: ACTION
---
PUSH
target: excerpts/20260821/keyb01.manifest.json

{
  "magic": "KEYB01v1",
  "path": "C:\\Users\\lucys\\Desktop\\MUHL_KEYB\\keyb01.mno",
  "n_pos": 16,
  "alphabet_width": 128,
  "char_base": 165,
  "field_base": 2213,
  "commit_fwd": 99,
  "commit_rev": 131,
  "commit_span": 66,
  "clock": 98,
  "n_gate": 16489,
  "n_wire": 18538,
  "depth": 8,
  "mouths": {
    "HELP": 4261,
    "READ": 4262,
    "WRITE": 4263,
    "FIRE": 4264,
    "SURFACE": 4265,
    "ACK": 4266
  },
  "formula": "addr = char_base + position * alphabet_width + char_code",
  "abi": "7-bit ASCII plus CR/LF/space/tab/backspace. Order is position.",
  "git_copy_runs": "NO",
  "HTTP_is_the_computer": "NO",
  "sha256": "a63396b59b0fb9f0ce1366d112c2abd209475aecde2d458f82f9999667f1521e",
  "n_bytes": 430860
}

