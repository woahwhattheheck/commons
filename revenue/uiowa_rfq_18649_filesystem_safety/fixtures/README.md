# Screen fixtures — SYNTHETIC / FICTION

These are invented modules, not anybody's real code. Each one exists to pin one
classification the screen must produce. They are never executed by the screen —
it only parses them.

| lane | module | expected |
| --- | --- | --- |
| `lane_clean` | `tool_clean.py` | `CLEAN` — writes only through a guarded writer |
| `lane_self_scoped` | `tool_temp.py` | `SELF_SCOPED` — removes a dir it created itself |
| `lane_external` | `tool_argv.py` | `REVIEW_REQUIRED` — removes a path from `argv` / a parameter |
| `lane_external` | `test_sample_cleanup.py` | `REVIEW_REQUIRED` — a test module does **not** excuse an externally supplied target |
| `lane_opaque` | `tool_shell.py` | `UNDETERMINED` — shells out; the screen cannot see inside |
