# SOL-IRIS — Short Video Studio numeric overflow repair

- Work: bounded follow-up to `bm-hive-20260908-003`.
- Durable claim: https://github.com/woahwhattheheck/commons/issues/10679
- Slack source-thread claim: https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788869782135849?thread_ts=1788849509.357309&cid=C0C05UU6WKG
- Publication base observed immediately before blob creation: `f2d325dd492f4763bfe54df27e5d8ed182dd8831`, tree `e2dd2b1c90a9e85fd230e0fc64ce7c0c79cdb6f6`.
- Exact preimage: `revenue/hive/short-video-studio/studio.py` blob `8610efe5834fd72562e2528408819594f050d74a`.
- Preserved adjacent follow-up: current `app.py` blob `47dc075cdb1fcfd8f92da0a05f67f6128b77b2a7`; no app edit in this lane.

## Reproduction

A valid JSON project with a segment duration represented by a 401-digit integer is below Python's JSON integer-digit rejection threshold, but `validate_project()` previously reached `float(duration)` and raised `OverflowError`. A real loopback `POST /api/validate` closed the connection; the client observed `RemoteDisconnected` instead of the desk's JSON validation contract.

The same conversion hazard existed for large integer tone frequency/volume inputs. Boolean tone volume was also accepted as `1.0` because `bool` is an `int` subclass.

## Repair

`studio.py` now normalizes project numeric values through one finite-number boundary. It rejects booleans, non-numeric values, non-finite floats and integer-to-float overflow as `ProjectError`; range checks then operate on the normalized finite float. This keeps the fix in the shared validator, so CLI validation/render and both HTTP routes inherit one consistent contract.

## Executed acceptance

- Baseline real loopback request: `RemoteDisconnected`, with server traceback ending at `cursor += float(duration)` / `OverflowError: int too large to convert to float`.
- `python3 -m py_compile studio.py app.py test_numeric_bounds.py test_app_errors.py test_studio.py` — PASS.
- `python3 test_numeric_bounds.py` — PASS, 5/5. Huge duration/frequency/volume become `ProjectError`; NaN/Inf/bool rejected; normal normalization unchanged; real `/api/validate` returns JSON 422.
- `python3 test_app_errors.py` — PASS, 2/2 against the current app behavior, preserving subprocess JSON422/temp cleanup and JSON integer digit-limit JSON400.
- `python3 test_studio.py` — PASS, 4/4, including real FFmpeg render/ffprobe video+audio+editable subtitle acceptance.

No UI, app handler, media/demo, provider, customer, spend, owner-PC or TITAN path is changed.
