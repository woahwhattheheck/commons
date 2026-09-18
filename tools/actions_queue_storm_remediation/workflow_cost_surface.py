#!/usr/bin/env python3
"""Static GitHub Actions launch-pressure inventory for checked-out repositories.

Read-only: scans .github/workflows, hashes exact bytes, and reports trigger,
concurrency, timeout, matrix, schedule, reusable-job, and runner exposure
signals. It does not estimate dollars or mutate workflows/provider state.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Sequence

_TOP_RE = re.compile(r"^(?P<key>[^:\\s]+):(?P<tail>.*)$")
_KEY_RE = re.compile(r"^(?P<indent> *)(?P<key>[^:\\s]+):(?P<tail>.*)$")
_EVENTS = {
    "push", "pull_request", "pull_request_target", "schedule",
    "workflow_dispatch", "workflow_call", "merge_group",
}
_RUN_EVENTS = {
    "push", "pull_request", "pull_request_target",
    "schedule", "merge_group",
}
MAX_WORKFLOW_BYTES = 1024 * 1024


@dataclasses.dataclass(frozen=True)
class JobSurface:
    job_id: str
    reusable_workflow: bool
    runs_on: str | None
    explicit_self_hosted: bool
    timeout_declared: bool
    matrix_declared: bool
    static_matrix_multiplier: int | None


@dataclasses.dataclass(frozen=True)
class WorkflowSurface:
    path: str
    byte_sha256: str
    byte_size: int
    triggers: tuple[str, ...]
    trigger_form: str
    push_branch_scoped: bool
    push_path_scoped: bool
    pull_request_path_scoped: bool
    schedule_entries: int
    concurrency_declared: bool
    cancel_in_progress_true: bool
    jobs: tuple[JobSurface, ...]
    signals: tuple[str, ...]


def _key(value: str) -> str:
    return value.strip("\"'")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _block_end(
    lines: Sequence[str],
    start: int,
    parent_indent: int,
) -> int:
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if _blank(line):
            continue
        if "\t" in line[: len(line) - len(line.lstrip())]:
            return index
        if _indent(line) <= parent_indent:
            return index
    return len(lines)


def _find_top(
    lines: Sequence[str],
    key: str,
) -> int | None:
    for index, line in enumerate(lines):
        if _blank(line) or _indent(line) != 0:
            continue
        match = _TOP_RE.match(line)
        if match and _key(match.group("key")) == key:
            return index
    return None


def _children(
    lines: Sequence[str],
    start: int,
    parent_indent: int,
) -> list[tuple[int, str, str]]:
    end = _block_end(lines, start, parent_indent)
    out: list[tuple[int, str, str]] = []
    for index in range(start + 1, end):
        line = lines[index]
        if _blank(line):
            continue
        match = _KEY_RE.match(line)
        if (
            match
            and len(match.group("indent")) == parent_indent + 2
        ):
            out.append(
                (
                    index,
                    _key(match.group("key")),
                    match.group("tail").strip(),
                )
            )
    return out


def _inline_list(value: str) -> list[str] | None:
    value = value.strip()
    if not (
        value.startswith("[")
        and value.endswith("]")
    ):
        return None
    body = value[1:-1].strip()
    if not body:
        return []
    if "${{" in body or "}}" in body:
        return None

    items: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False

    for char in body:
        if escaped:
            current.append(char)
            escaped = False
        elif quote:
            current.append(char)
            if char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
            current.append(char)
        elif char == ",":
            item = "".join(current).strip()
            if not item:
                return None
            items.append(item)
            current = []
        else:
            current.append(char)

    item = "".join(current).strip()
    if quote or not item:
        return None
    items.append(item)
    return items


def _triggers(
    lines: Sequence[str],
) -> tuple[
    tuple[str, ...],
    str,
    dict[str, dict[str, bool]],
    int,
]:
    index = _find_top(lines, "on")
    if index is None:
        return (), "missing", {}, 0

    match = _TOP_RE.match(lines[index])
    if match is None:
        return (), "missing", {}, 0

    tail = match.group("tail").strip()
    if tail and not tail.startswith("#"):
        inline = _inline_list(tail)
        if inline is None:
            scalar = tail.split("#", 1)[0].strip("\"' ")
            return (
                (scalar,) if scalar in _EVENTS else (),
                "inline",
                {},
                0,
            )
        return (
            tuple(
                item.strip("\"' ")
                for item in inline
                if item.strip("\"' ") in _EVENTS
            ),
            "inline",
            {},
            0,
        )

    events: list[str] = []
    props: dict[str, dict[str, bool]] = {}
    schedule_entries = 0

    for event_index, event, _tail in _children(
        lines,
        index,
        0,
    ):
        if event not in _EVENTS:
            continue

        events.append(event)
        event_props = {
            "branches": False,
            "branches-ignore": False,
            "paths": False,
            "paths-ignore": False,
        }

        for _i, child, _t in _children(
            lines,
            event_index,
            2,
        ):
            if child in event_props:
                event_props[child] = True

        props[event] = event_props

        if event == "schedule":
            end = _block_end(
                lines,
                event_index,
                2,
            )
            schedule_entries += sum(
                1
                for line in lines[
                    event_index + 1 : end
                ]
                if line.strip().startswith("- cron:")
            )

    return (
        tuple(events),
        "structured",
        props,
        schedule_entries,
    )


def _concurrency(
    lines: Sequence[str],
) -> tuple[bool, bool]:
    index = _find_top(
        lines,
        "concurrency",
    )
    if index is None:
        return False, False

    match = _TOP_RE.match(lines[index])
    if match is None:
        return False, False

    tail = match.group("tail").strip()
    if tail and not tail.startswith("#"):
        return True, False

    for _i, key, tail in _children(
        lines,
        index,
        0,
    ):
        if key != "cancel-in-progress":
            continue
        value = (
            tail
            .split("#", 1)[0]
            .strip()
            .lower()
        )
        return (
            True,
            value == "true"
            or (
                value.startswith("${{")
                and "true" in value
            ),
        )

    return True, False


def _jobs(
    lines: Sequence[str],
) -> tuple[JobSurface, ...]:
    index = _find_top(lines, "jobs")
    if index is None:
        return ()

    out: list[JobSurface] = []

    for job_index, job_id, _tail in _children(
        lines,
        index,
        0,
    ):
        direct = _children(
            lines,
            job_index,
            2,
        )
        values = {
            key: tail
            for _i, key, tail
            in direct
        }

        reusable = (
            "uses" in values
            and "runs-on" not in values
        )
        runs_on = values.get("runs-on")

        explicit_self_hosted = bool(
            runs_on
            and "self-hosted" in runs_on.lower()
            and "${{" not in runs_on
        )

        strategy = next(
            (
                i
                for i, key, _t
                in direct
                if key == "strategy"
            ),
            None,
        )
        matrix_declared = False
        multiplier: int | None = None

        if strategy is not None:
            strategy_children = _children(
                lines,
                strategy,
                4,
            )
            matrix = next(
                (
                    i
                    for i, key, _t
                    in strategy_children
                    if key == "matrix"
                ),
                None,
            )
            matrix_tail = next(
                (
                    tail
                    for _i, key, tail
                    in strategy_children
                    if key == "matrix"
                ),
                "",
            )

            if matrix is not None:
                matrix_declared = True

                if (
                    not matrix_tail
                    or matrix_tail in {"{}", "{ }"}
                ):
                    axes: list[int] = []
                    complex_matrix = False

                    for _i, key, tail in _children(
                        lines,
                        matrix,
                        6,
                    ):
                        if key in {
                            "include",
                            "exclude",
                        }:
                            complex_matrix = True
                            continue

                        items = _inline_list(tail)
                        if items is None:
                            complex_matrix = True
                        else:
                            axes.append(len(items))

                    if (
                        axes
                        and not complex_matrix
                    ):
                        multiplier = 1
                        for width in axes:
                            multiplier *= width

        out.append(
            JobSurface(
                job_id=job_id,
                reusable_workflow=reusable,
                runs_on=runs_on,
                explicit_self_hosted=(
                    explicit_self_hosted
                ),
                timeout_declared=(
                    "timeout-minutes" in values
                ),
                matrix_declared=(
                    matrix_declared
                ),
                static_matrix_multiplier=(
                    multiplier
                ),
            )
        )

    return tuple(out)


def analyze_text(
    text: str,
    *,
    path: str,
    byte_sha256: str,
    byte_size: int,
) -> WorkflowSurface:
    lines = [
        line.rstrip("\r\n")
        for line in text.splitlines()
    ]

    (
        triggers,
        trigger_form,
        props,
        schedule_entries,
    ) = _triggers(lines)

    concurrency, cancel_true = (
        _concurrency(lines)
    )
    jobs = _jobs(lines)

    push = props.get("push", {})
    pull = props.get(
        "pull_request",
        {},
    )

    push_branch_scoped = bool(
        push.get("branches")
        or push.get("branches-ignore")
    )
    push_path_scoped = bool(
        push.get("paths")
        or push.get("paths-ignore")
    )
    pull_path_scoped = bool(
        pull.get("paths")
        or pull.get("paths-ignore")
    )

    event_set = set(triggers)
    runners = [
        job
        for job in jobs
        if job.runs_on is not None
        and not job.reusable_workflow
    ]

    signals: list[str] = []

    if (
        {"push", "pull_request"}
        <= event_set
        and not push_branch_scoped
    ):
        signals.append(
            "UNRESTRICTED_PUSH_PLUS_PR"
        )

    if (
        {"push", "pull_request"}
        <= event_set
        and (
            not push_path_scoped
            or not pull_path_scoped
        )
    ):
        signals.append(
            "BROAD_PUSH_PR_PATH_SURFACE"
        )

    if (
        event_set & _RUN_EVENTS
        and runners
        and not concurrency
    ):
        signals.append(
            "RUN_EVENTS_WITHOUT_CONCURRENCY"
        )

    if (
        event_set & _RUN_EVENTS
        and concurrency
        and not cancel_true
    ):
        signals.append(
            "CONCURRENCY_WITHOUT_CANCEL"
        )

    if (
        "schedule" in event_set
        and schedule_entries
    ):
        signals.append(
            "SCHEDULED_RUNS"
        )

    if any(
        not job.timeout_declared
        for job in runners
    ):
        signals.append(
            "RUNNER_JOB_MISSING_TIMEOUT"
        )

    if any(
        job.matrix_declared
        for job in runners
    ):
        signals.append(
            "MATRIX_FANOUT"
        )

    if any(
        not job.explicit_self_hosted
        for job in runners
    ):
        signals.append(
            "HOSTED_OR_DYNAMIC_RUNNER_EXPOSURE"
        )

    if any(
        job.reusable_workflow
        for job in jobs
    ):
        signals.append(
            "REUSABLE_WORKFLOW_JOB"
        )

    return WorkflowSurface(
        path=path,
        byte_sha256=byte_sha256,
        byte_size=byte_size,
        triggers=triggers,
        trigger_form=trigger_form,
        push_branch_scoped=(
            push_branch_scoped
        ),
        push_path_scoped=(
            push_path_scoped
        ),
        pull_request_path_scoped=(
            pull_path_scoped
        ),
        schedule_entries=(
            schedule_entries
        ),
        concurrency_declared=(
            concurrency
        ),
        cancel_in_progress_true=(
            cancel_true
        ),
        jobs=jobs,
        signals=tuple(signals),
    )


def analyze_file(
    path: Path,
    root: Path,
) -> WorkflowSurface:
    if (
        path.is_symlink()
        or not path.is_file()
    ):
        raise ValueError(
            "workflow must be a regular "
            f"non-symlink file: {path}"
        )

    raw = path.read_bytes()

    if len(raw) > MAX_WORKFLOW_BYTES:
        raise ValueError(
            "workflow exceeds "
            f"{MAX_WORKFLOW_BYTES} bytes: {path}"
        )

    text = raw.decode("utf-8")

    return analyze_text(
        text,
        path=str(path.relative_to(root)),
        byte_sha256=(
            hashlib.sha256(raw).hexdigest()
        ),
        byte_size=len(raw),
    )


def workflow_files(
    root: Path,
) -> tuple[Path, ...]:
    directory = (
        root
        / ".github"
        / "workflows"
    )

    if not directory.is_dir():
        return ()

    return tuple(
        sorted(
            path
            for pattern in (
                "*.yml",
                "*.yaml",
            )
            for path in directory.glob(pattern)
            if path.is_file()
            and not path.is_symlink()
        )
    )


def summarize(
    root: Path,
    workflows: Sequence[WorkflowSurface],
) -> dict:
    trigger_counts: Counter[str] = Counter()

    for workflow in workflows:
        trigger_counts.update(
            workflow.triggers
        )

    jobs = [
        job
        for workflow in workflows
        for job in workflow.jobs
    ]
    runners = [
        job
        for job in jobs
        if job.runs_on is not None
        and not job.reusable_workflow
    ]
    run_workflows = [
        workflow
        for workflow in workflows
        if (
            set(workflow.triggers)
            & _RUN_EVENTS
        )
        and any(
            job.runs_on is not None
            and not job.reusable_workflow
            for job in workflow.jobs
        )
    ]

    return {
        "root": str(root),
        "workflow_files": len(workflows),
        "trigger_counts": dict(
            sorted(trigger_counts.items())
        ),
        "workflows_with_push_and_pr": sum(
            1
            for workflow in workflows
            if {"push", "pull_request"}
            <= set(workflow.triggers)
        ),
        "unrestricted_push_and_pr": sum(
            1
            for workflow in workflows
            if "UNRESTRICTED_PUSH_PLUS_PR"
            in workflow.signals
        ),
        "workflows_without_concurrency": sum(
            1
            for workflow in run_workflows
            if not workflow.concurrency_declared
        ),
        "workflows_concurrency_without_cancel": sum(
            1
            for workflow in run_workflows
            if workflow.concurrency_declared
            and not workflow.cancel_in_progress_true
        ),
        "scheduled_workflows": sum(
            1
            for workflow in workflows
            if "schedule" in workflow.triggers
        ),
        "schedule_entries": sum(
            workflow.schedule_entries
            for workflow in workflows
        ),
        "runner_jobs": len(runners),
        "explicit_self_hosted_jobs": sum(
            1
            for job in runners
            if job.explicit_self_hosted
        ),
        "hosted_or_dynamic_runner_jobs": sum(
            1
            for job in runners
            if not job.explicit_self_hosted
        ),
        "reusable_workflow_jobs": sum(
            1
            for job in jobs
            if job.reusable_workflow
        ),
        "jobs_missing_timeout": sum(
            1
            for job in runners
            if not job.timeout_declared
        ),
        "matrix_jobs": sum(
            1
            for job in runners
            if job.matrix_declared
        ),
        "known_static_matrix_runner_slots": sum(
            job.static_matrix_multiplier
            for job in runners
            if (
                job.static_matrix_multiplier
                is not None
            )
        ),
        "workflows": [
            dataclasses.asdict(workflow)
            for workflow in workflows
        ],
    }


def audit_root(root: Path) -> dict:
    root = root.resolve()

    workflows = [
        analyze_file(path, root)
        for path in workflow_files(root)
    ]

    return summarize(
        root,
        workflows,
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        default=[Path(".")],
    )
    parser.add_argument(
        "--output",
        type=Path,
    )
    args = parser.parse_args(argv)

    repositories = [
        audit_root(root)
        for root in args.roots
    ]

    total_keys = (
        "workflow_files",
        "workflows_with_push_and_pr",
        "unrestricted_push_and_pr",
        "workflows_without_concurrency",
        "workflows_concurrency_without_cancel",
        "scheduled_workflows",
        "schedule_entries",
        "runner_jobs",
        "explicit_self_hosted_jobs",
        "hosted_or_dynamic_runner_jobs",
        "reusable_workflow_jobs",
        "jobs_missing_timeout",
        "matrix_jobs",
        "known_static_matrix_runner_slots",
    )

    totals = {
        key: sum(
            int(repo[key])
            for repo in repositories
        )
        for key in total_keys
    }

    receipt = {
        "schema_version": 1,
        "mode": (
            "read_only_static_cost_surface"
        ),
        "dollar_cost_estimated": False,
        "billing_authority": False,
        "repositories": repositories,
        "totals": totals,
        "interpretation": {
            "hosted_or_dynamic_runner_jobs": (
                "runner jobs not explicitly pinned "
                "to a literal self-hosted label; "
                "exposure, not billing proof"
            ),
            "known_static_matrix_runner_slots": (
                "matrix slots counted only for "
                "simple inline axes with no "
                "include/exclude/dynamic form"
            ),
        },
    }

    rendered = (
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            rendered,
            encoding="utf-8",
        )

    print(
        rendered,
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
