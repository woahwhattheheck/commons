# Kit exit-signal audit

Scanned `/home/user/fleet/staging/OP5-QUARRY/revenue/uiowa_rfq_18649_exit_signals/fixtures` - 1 lane(s), 7 entrypoint(s) with a `__main__` guard (0 non-entrypoint files skipped).

| Classification | Count | Meaning |
|---|---|---|
| `GATE` | 1 | a non-zero exit is reachable |
| `REPORT_ONLY` | 4 | always exits 0 |
| `INDETERMINATE` | 2 | exit value not statically resolvable; not assumed either way |

| Finding | Count |
|---|---|
| `NO_CONTRACT_LINE` | 6 |
| `NO_SIGNAL_PATH` | 3 |
| `CRASH_AS_SIGNAL` | 1 |
| `DEAD_GATE` | 1 |
| `FALSE_CLEAN` | 1 |
| `RUNTIME_DECLARED_STATUS` | 1 |
| `UNRESOLVED_EXIT` | 1 |

## HIGH-severity findings

### `t_dead_gate.py` - `DEAD_GATE`

1 non-zero exit(s) sit in unreachable code; a grep-based check would report this tool as gated

*Remedy:* remove the dead branch or restore the path that reaches it

### `t_false_clean.py` - `FALSE_CLEAN`

prints failure vocabulary (broken, error, fail) but always exits 0, so a runner records a clean result for a run that reported a problem

*Remedy:* return a non-zero code on the same condition, or wrap the tool with wrap.py and declare a fallback rule

## Every entrypoint

| Tool | Class | Contract line | Dead non-zero exits | Findings |
|---|---|---|---|---|
| `t_contract.py` | `INDETERMINATE` | yes | 0 | `RUNTIME_DECLARED_STATUS` |
| `t_crash_only.py` | `REPORT_ONLY` | no | 0 | `NO_SIGNAL_PATH`, `CRASH_AS_SIGNAL`, `NO_CONTRACT_LINE` |
| `t_dead_gate.py` | `REPORT_ONLY` | no | 1 | `NO_SIGNAL_PATH`, `DEAD_GATE`, `NO_CONTRACT_LINE` |
| `t_dynamic.py` | `INDETERMINATE` | no | 0 | `UNRESOLVED_EXIT`, `NO_CONTRACT_LINE` |
| `t_false_clean.py` | `REPORT_ONLY` | no | 0 | `FALSE_CLEAN`, `NO_CONTRACT_LINE` |
| `t_gate.py` | `GATE` | no | 0 | `NO_CONTRACT_LINE` |
| `t_report_only.py` | `REPORT_ONLY` | no | 0 | `NO_SIGNAL_PATH`, `NO_CONTRACT_LINE` |
