# ASTRA-SOL short-video HTTP subprocess error contract

- Follow-up to merged PR #10651 (`06f488d9da6a1fe08940b90461b7a7eacccf5a09`).
- Coordination claim: PR #10651 issue comment `5584758272`.
- Owned production path: `revenue/hive/short-video-studio/app.py`.
- New regression path: `revenue/hive/short-video-studio/test_app_errors.py`.
- Boundary: localhost HTTP error handling only. No renderer/source/demo/media/provider/network/publication behavior changes.

## Defect

`studio._run()` uses `subprocess.run(..., check=True)`, so an FFmpeg or ffprobe non-zero exit raises
`subprocess.CalledProcessError`. The `/api/render` handler did not catch that exception class.
The request thread therefore closed the connection without the desk's JSON error response.

## Executed focused regression

Source-exact `app.py` handler from fresh-main blob `64919ddb7d47eb555d4167af0ccddb82fbfd0105`
was exercised over a real loopback `ThreadingHTTPServer`; only the renderer implementation was
patched to raise a synthetic `CalledProcessError(7, ["ffmpeg", "synthetic-render"])`.

- Baseline: 1 test, ERROR — client received `http.client.RemoteDisconnected`.
- Candidate: 1/1 PASS — HTTP 422 JSON contains the non-zero exit diagnostic.
- Candidate also asserts the temporary project JSON is removed after failure.
- Command: `python -S -B -m unittest -v test_app_errors`.

This focused harness does not claim the full Commons battery or a new real FFmpeg render.
The original PR #10651 recorded 4/4 focused product tests and a real 30-second FFmpeg render;
those unchanged renderer tests were not reclassified as part of this follow-up.

## Candidate identities

- Base main: `37e3caf914333ec9ef10d65a3a1eb48d15793def`
- Base tree: `06d08f93bab69cdb26b717b0e1201d0280f1ef28`
- Original app blob: `64919ddb7d47eb555d4167af0ccddb82fbfd0105`
- Candidate app blob: `90caf90803f5b1a7e239e92bc9c043af9d54b1b2`
- Regression blob: `130029d29fdd58240cc2ea9d75a90769b294e892`

Publication uses a fresh-main collision check, atomic Git Data tree/commit, a unique branch and PR,
exact diff inspection, `expected_head_sha` merge, and post-merge current-main blob readback.
No force-push.
