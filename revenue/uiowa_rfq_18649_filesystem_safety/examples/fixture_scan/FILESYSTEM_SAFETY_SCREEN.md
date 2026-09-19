# Filesystem-safety screen

> This is a SCREEN, not a proof. CLEAN means the screen found nothing it could see -- it does not mean the module is safe. Dynamic dispatch, getattr, C extensions and anything inside a subprocess are invisible to an AST. No safety score is produced and no lane is marked compliant.

Scanned: `/home/user/fleet/staging/OP5-MARROW/revenue/uiowa_rfq_18649_filesystem_safety/fixtures`

- modules scanned: **5** across **4** lanes
- findings: **8**
- `REVIEW_REQUIRED`: **4**
- `UNDETERMINED`: **1**

`REVIEW_REQUIRED` means exactly one thing here: **this tool can remove, move, rename or truncate a path the caller names.** Writing where you asked it to write is reported separately.

## Module status counts

| status | modules |
| --- | --- |
| `REVIEW_REQUIRED` | 2 |
| `SELF_SCOPED` | 2 |
| `UNDETERMINED` | 1 |

`UNPARSEABLE` is listed separately and is never counted as CLEAN: a module the screen could not read is not a module it cleared.

## Lanes needing a human look

| lane | worst status |
| --- | --- |
| `lane_external` | `REVIEW_REQUIRED` |
| `lane_opaque` | `UNDETERMINED` |

## REVIEW_REQUIRED - the target comes from outside the module

Each of these removes, moves or overwrites a path chosen by the caller, by argv, by the environment, or by a config value. That is not automatically wrong -- it is what a human has to confirm is intended.

| lane | module:line | call | target | why |
| --- | --- | --- | --- | --- |
| `lane_external` | `lane_external/test_sample_cleanup.py:12` | `shutil.rmtree` | `supplied_path` | target is the function parameter 'supplied_path' -- the caller chooses what gets removed |
| `lane_external` | `lane_external/tool_argv.py:13` | `shutil.rmtree` | `workspace` | target is the function parameter 'workspace' -- the caller chooses what gets removed |
| `lane_external` | `lane_external/tool_argv.py:17` | `shutil.rmtree` | `sys.argv[1]` | target comes from sys.argv, which is external input |
| `lane_external` | `lane_external/tool_argv.py:21` | `os.remove` | `os.path.join(root, name)` | path is joined from externally controlled parts |

## UNDETERMINED - the screen could not trace the target

Reported as its own class on purpose. A screen that cannot tell does not get to report clean.

| lane | module:line | call | target | why |
| --- | --- | --- | --- | --- |
| `lane_opaque` | `lane_opaque/tool_shell.py:6` | `subprocess.run` | `['python3', '-m', 'unittest', 'discover']` | shells out; what runs inside is not visible to this screen |

## WRITE_TO_CALLER_PATH - writes where the caller pointed it

Normal for every CLI here: they all take an output option. Listed so an operator can confirm none of them can be aimed at evidence that must be kept. These do not delete anything.

None.

## TEST_CONTEXT - inside a test module

Test suites legitimately create and remove their own temp trees. Listed for completeness, not as a concern.

| lane | module:line | call | target | why |
| --- | --- | --- | --- | --- |
| `lane_external` | `lane_external/test_sample_cleanup.py:17` | `shutil.rmtree` | `scratch` | in a test module; 'scratch' is assigned from module-local values |

## SELF_SCOPED - the module created the path it removes

A verifier cleaning up its own scratch copy lands here. This is the shape you want.

| lane | module:line | call | target | why |
| --- | --- | --- | --- | --- |
| `lane_clean` | `lane_clean/tool_clean.py:11` | `open(mode='w')` | `target` | write target is caller-supplied, but the function resolves the path and raises on one outside its directory (heuristic) |
| `lane_self_scoped` | `lane_self_scoped/tool_temp.py:11` | `shutil.rmtree` | `scratch` | 'scratch' is assigned from module-local values |

## Modules the screen could not read

None.

