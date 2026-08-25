#!/usr/bin/env python3
"""host/device_churn.py — device-path utilization + no-op workflow churn.

Slack 1787635008.594599 (DEMON): the device execution protocol is
implemented but unused. GitHub still starts commons-device-executor
after every commons-board completion (512 runs measured 2026-08-25),
even when there is no reservation, no batch, and no scope=device
result. That is no-op churn.

This leftover measures the trigger and runs one bounded lawful canary
through the existing prepare/execute/finalize protocol in a temp
repo. It does not dispatch the self-hosted runner. It does not inject
DC, pulse Titan, pack a host, or run SGD. Titan is governed data,
not spare compute.

  python3 host/device_churn.py
  python3 host/device_churn.py --root .
  python3 host/device_churn.py --canary
  python3 host/device_churn.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys


EXECUTOR = os.path.join(".github", "workflows", "commons-device-executor.yml")
BOARD = os.path.join(".github", "workflows", "commons-board.yml")
DEFAULT_CATALOG = os.path.join("ground", "DEVICE_CHURN.json")
CANARY_TEST = (
    "test_device_action_state.DeviceActionStateTests."
    "test_prepare_execute_finalize_success_is_exact_and_history_latched"
)


class FinderError(RuntimeError):
    """A directory search failed; it did not measure an empty directory."""


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def count_json_files(directory):
    """Count regular *.json files in one successfully listed directory."""
    if not os.path.isdir(directory):
        raise FileNotFoundError("directory not found: %s" % directory)
    total = 0
    try:
        names = os.listdir(directory)
    except OSError as exc:
        raise FinderError("directory could not be listed: %s" % exc) from exc
    for name in names:
        path = os.path.join(directory, name)
        if name.endswith(".json") and os.path.isfile(path):
            total += 1
    return total


def count_scope_device(results_dir):
    """Count device results only when every result JSON can be parsed."""
    if not os.path.isdir(results_dir):
        raise FileNotFoundError("directory not found: %s" % results_dir)
    total = 0
    try:
        names = os.listdir(results_dir)
    except OSError as exc:
        raise FinderError("directory could not be listed: %s" % exc) from exc
    for name in names:
        path = os.path.join(results_dir, name)
        if not name.endswith(".json") or not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                row = json.load(handle)
        except OSError as exc:
            raise FinderError(
                "result JSON could not be read %s: %s" % (name, exc)
            ) from exc
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("result JSON unreadable %s: %s" % (name, exc)) from exc
        if not isinstance(row, dict):
            raise ValueError("result JSON is not an object: %s" % name)
        if row.get("scope") == "device":
            total += 1
    return total


def measure_count(label, function, directory):
    """Return count + finder status without converting failure to zero."""
    try:
        return {
            "label": label,
            "status": "OK",
            "count": function(directory),
            "error": "",
        }
    except (FileNotFoundError, FinderError) as exc:
        return {
            "label": label,
            "status": "FINDER-FAILED",
            "count": None,
            "error": str(exc),
        }
    except ValueError as exc:
        return {
            "label": label,
            "status": "FINDER-UNVERIFIED",
            "count": None,
            "error": str(exc),
        }


def workflow_flags(executor_text, board_text):
    """Pure trigger facts from the two workflow bodies."""
    executor = str(executor_text or "")
    board = str(board_text or "")
    return {
        "executor_present": bool(executor.strip()),
        "board_present": bool(board.strip()),
        "workflow_run": "workflow_run:" in executor,
        "workflow_call": "workflow_call:" in executor,
        "workflow_dispatch": "workflow_dispatch:" in executor,
        "board_preflight": "device_action_state.py preflight" in board,
        "board_calls_executor": (
            "uses: ./.github/workflows/commons-device-executor.yml" in board
        ),
        "board_gates_pending": "has_pending_device" in board,
    }


def classify(row):
    """Turn measured trigger + canary facts into a land-desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": "device-churn leftover not read. Absence was not stillness.",
        }
    failed_finders = [
        item
        for item in (row.get("count_finders") or {}).values()
        if str(item.get("status") or "") != "OK"
    ]
    if failed_finders:
        labels = [
            "%s=%s" % (item.get("label"), item.get("status"))
            for item in failed_finders
        ]
        return {
            "state": "UNMEASURED",
            "note": (
                "device utilization count failed: "
                + ", ".join(labels)
                + ". Counts are null, not zero. Workflow-gate evidence is "
                "preserved separately. FINDER-FAILED, never 0."
            ),
        }
    flags = row.get("flags") or {}
    if not flags.get("executor_present") or not flags.get("board_present"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "device executor or commons-board workflow missing. "
                "No-op-churn talk is CLAIMED until the leftover ships."
            ),
        }
    if flags.get("workflow_run"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "commons-device-executor still starts on every commons-board "
                "completion. That is no-op churn. Gate it on a real pending "
                "device action."
            ),
        }
    if not (
        flags.get("workflow_call")
        and flags.get("board_preflight")
        and flags.get("board_calls_executor")
        and flags.get("board_gates_pending")
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "workflow_run is gone but board does not dispatch the "
                "executor only when has_pending_device is true."
            ),
        }
    canary = row.get("canary") or {}
    if canary.get("ran") and not canary.get("ok"):
        return {
            "state": "CANDIDATE",
            "note": (
                "trigger is gated, but the bounded prepare/execute/finalize "
                "canary failed. Protocol leftover is not done."
            ),
        }
    return {
        "state": "INTEGRATED",
        "note": (
            "executor is call/dispatch only. commons-board starts it only "
            "when a device action is pending. Zero reservations is unused "
            "readiness, not a run. Talk is not a land."
        ),
    }


def measure_from_rows(counts, flags, extras=None):
    """Pure measure so tests do not need the live tree."""
    extras = extras or {}
    counts = counts or {}
    flags = flags or {}
    canary = extras.get("canary") or {"ran": False, "ok": False}
    def count(name, default=0):
        value = counts[name] if name in counts else default
        return None if value is None else int(value)

    row = {
        "measured": True,
        "catalog": bool(extras.get("catalog")),
        "reservation_count": count("reservation_count"),
        "batch_count": count("batch_count"),
        "result_count": count("result_count"),
        "scope_device_count": count("scope_device_count"),
        "count_finders": dict(extras.get("count_finders") or {}),
        "flags": dict(flags),
        "canary": dict(canary),
        "titan": "NOT_WRITTEN",
        "dc_inject": False,
        "self_hosted_dispatch": False,
    }
    return row


def measure_root(root, canary=None):
    root = os.path.abspath(root)
    flags = workflow_flags(
        _read_text(os.path.join(root, EXECUTOR)),
        _read_text(os.path.join(root, BOARD)),
    )
    reservation_dir = os.path.join(root, "actions", "device-reservations")
    batch_dir = os.path.join(root, "actions", "device-batches")
    results_dir = os.path.join(root, "actions", "results")
    count_finders = {
        "reservation_count": measure_count(
            "reservation_count", count_json_files, reservation_dir
        ),
        "batch_count": measure_count("batch_count", count_json_files, batch_dir),
        "result_count": measure_count("result_count", count_json_files, results_dir),
        "scope_device_count": measure_count(
            "scope_device_count", count_scope_device, results_dir
        ),
    }
    counts = {
        name: item.get("count") for name, item in count_finders.items()
    }
    extras = {
        "catalog": os.path.isfile(os.path.join(root, DEFAULT_CATALOG)),
        "canary": canary or {"ran": False, "ok": False},
        "count_finders": count_finders,
    }
    row = measure_from_rows(counts, flags, extras)
    row["root"] = root
    return row


def run_canary(root):
    """Bounded lawful protocol canary. Temp-repo only. No device runner."""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", CANARY_TEST],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
    except OSError as exc:
        return {
            "ran": True,
            "ok": False,
            "returncode": 127,
            "error": str(exc),
            "test": CANARY_TEST,
        }
    return {
        "ran": True,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "test": CANARY_TEST,
        "stderr_tail": (proc.stderr or "")[-400:],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Measure device-executor no-op churn and run a protocol canary"
    )
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--canary",
        action="store_true",
        help="run the bounded prepare/execute/finalize unit canary",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the stdlib fixtures and exit",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return 0 if _self_test() else 1
    canary = run_canary(args.root) if args.canary else None
    row = measure_root(args.root, canary=canary)
    verdict = classify(row)
    payload = dict(row)
    payload.update(verdict)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if row.get("measured") else 2


def _self_test():
    empty = classify({})
    assert empty["state"] == "UNMEASURED"
    assert "not stillness" in empty["note"]
    churn = workflow_flags(
        "on:\n  workflow_run:\n    workflows: [\"commons-board\"]\n",
        "name: commons-board\n",
    )
    assert churn["workflow_run"] is True
    measured = measure_from_rows(
        {
            "reservation_count": 0,
            "batch_count": 0,
            "result_count": 48,
            "scope_device_count": 0,
        },
        churn,
        {"catalog": True},
    )
    assert measured["reservation_count"] == 0
    assert measured["scope_device_count"] == 0
    assert measured["titan"] == "NOT_WRITTEN"
    assert measured["dc_inject"] is False
    assert classify(measured)["state"] == "NOT_LANDED"
    gated = workflow_flags(
        "on:\n  workflow_call:\n  workflow_dispatch:\n",
        (
            "device_action_state.py preflight\n"
            "has_pending_device: ${{ steps.device_pending.outputs.has_pending }}\n"
            "uses: ./.github/workflows/commons-device-executor.yml\n"
        ),
    )
    assert gated["workflow_run"] is False
    ready = measure_from_rows(
        {
            "reservation_count": 0,
            "batch_count": 0,
            "result_count": 48,
            "scope_device_count": 0,
        },
        gated,
        {"catalog": True, "canary": {"ran": True, "ok": True}},
    )
    assert classify(ready)["state"] == "INTEGRATED"
    failed = measure_from_rows(
        {"reservation_count": 0},
        gated,
        {"catalog": True, "canary": {"ran": True, "ok": False}},
    )
    assert classify(failed)["state"] == "CANDIDATE"
    missing = measure_from_rows({}, {}, {"catalog": False})
    assert classify(missing)["state"] == "NOT_LANDED"
    try:
        count_json_files("/no/such/device-reservations")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing directory must not become zero")
    return True


if __name__ == "__main__":
    sys.exit(main())
