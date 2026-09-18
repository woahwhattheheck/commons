#!/usr/bin/env python3
"""Read-only inventory of GitHub Actions launch-pressure signals."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Sequence

EVENTS = {
    "push",
    "pull_request",
    "pull_request_target",
    "schedule",
    "workflow_dispatch",
    "workflow_call",
    "merge_group",
}
RUN_EVENTS = {
    "push",
    "pull_request",
    "pull_request_target",
    "schedule",
    "merge_group",
}
MAX_WORKFLOW_BYTES = 1024 * 1024


@dataclasses.dataclass(frozen=True)
class Job:
    job_id: str
    reusable: bool
    runs_on: str | None
    self_hosted: bool
    timeout: bool
    matrix: bool
    static_matrix: int | None


@dataclasses.dataclass(frozen=True)
class Workflow:
    path: str
    sha256: str
    bytes: int
    triggers: tuple[str, ...]
    push_branch_scope: bool
    push_path_scope: bool
    pr_path_scope: bool
    schedules: int
    concurrency: bool
    cancel_in_progress: bool
    jobs: tuple[Job, ...]
    signals: tuple[str, ...]


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _blank(line: str) -> bool:
    text = line.strip()
    return not text or text.startswith("#")


def _mapping(line: str) -> tuple[str, str] | None:
    if _blank(line):
        return None

    text = line.lstrip(" ")
    if ":" not in text:
        return None

    key, tail = text.split(":", 1)
    key = key.strip().strip("\"'")

    if not key or " " in key or "\t" in key:
        return None

    return key, tail.strip()


def _end(
    lines: Sequence[str],
    start: int,
    parent: int,
) -> int:
    for index in range(start + 1, len(lines)):
        line = lines[index]

        if _blank(line):
            continue

        if _indent(line) <= parent:
            return index

    return len(lines)


def _top(
    lines: Sequence[str],
    wanted: str,
) -> int | None:
    for index, line in enumerate(lines):
        if _indent(line) != 0:
            continue

        pair = _mapping(line)
        if pair and pair[0] == wanted:
            return index

    return None


def _children(
    lines: Sequence[str],
    start: int,
    parent: int,
) -> list[tuple[int, str, str]]:
    out: list[tuple[int, str, str]] = []

    for index in range(
        start + 1,
        _end(lines, start, parent),
    ):
        line = lines[index]

        if _indent(line) != parent + 2:
            continue

        pair = _mapping(line)
        if pair:
            out.append(
                (
                    index,
                    pair[0],
                    pair[1],
                )
            )

    return out


def _inline_list(
    value: str,
) -> list[str] | None:
    value = value.strip()

    if (
        not value.startswith("[")
        or not value.endswith("]")
    ):
        return None

    body = value[1:-1].strip()

    if not body:
        return []

    if (
        "fromJSON(" in body
        or "${{" in body
    ):
        return None

    items = [
        item.strip().strip("\"'")
        for item in body.split(",")
    ]

    return (
        items
        if all(items)
        else None
    )


def _triggers(
    lines: Sequence[str],
) -> tuple[
    tuple[str, ...],
    dict[str, dict[str, bool]],
    int,
]:
    index = _top(lines, "on")

    if index is None:
        return (), {}, 0

    pair = _mapping(lines[index])

    if pair is None:
        return (), {}, 0

    tail = pair[1]

    if tail and not tail.startswith("#"):
        values = _inline_list(tail)

        if values is None:
            name = (
                tail
                .split("#", 1)[0]
                .strip()
                .strip("\"'")
            )
            return (
                (name,)
                if name in EVENTS
                else ()
            ), {}, 0

        return (
            tuple(
                name
                for name in values
                if name in EVENTS
            ),
            {},
            0,
        )

    names: list[str] = []
    props: dict[str, dict[str, bool]] = {}
    schedule_count = 0

    for event_index, name, _tail in _children(
        lines,
        index,
        0,
    ):
        if name not in EVENTS:
            continue

        names.append(name)

        row = {
            "branches": False,
            "branches-ignore": False,
            "paths": False,
            "paths-ignore": False,
        }

        for _i, key, _value in _children(
            lines,
            event_index,
            2,
        ):
            if key in row:
                row[key] = True

        props[name] = row

        if name == "schedule":
            for line in lines[
                event_index + 1 :
                _end(lines, event_index, 2)
            ]:
                if (
                    line
                    .strip()
                    .startswith("- cron:")
                ):
                    schedule_count += 1

    return (
        tuple(names),
        props,
        schedule_count,
    )


def _concurrency(
    lines: Sequence[str],
) -> tuple[bool, bool]:
    index = _top(
        lines,
        "concurrency",
    )

    if index is None:
        return False, False

    pair = _mapping(lines[index])

    if pair is None:
        return False, False

    if (
        pair[1]
        and not pair[1].startswith("#")
    ):
        return True, False

    for _i, key, value in _children(
        lines,
        index,
        0,
    ):
        if key == "cancel-in-progress":
            value = (
                value
                .split("#", 1)[0]
                .strip()
                .lower()
            )
            return (
                True,
                value == "true",
            )

    return True, False


def _jobs(
    lines: Sequence[str],
) -> tuple[Job, ...]:
    index = _top(lines, "jobs")

    if index is None:
        return ()

    out: list[Job] = []

    for job_index, job_id, _tail in _children(
        lines,
        index,
        0,
    ):
        fields = _children(
            lines,
            job_index,
            2,
        )

        values = {
            key: value
            for _i, key, value
            in fields
        }

        reusable = (
            "uses" in values
            and "runs-on" not in values
        )

        runs_on = values.get("runs-on")

        self_hosted = bool(
            runs_on
            and "self-hosted" in runs_on.lower()
            and "matrix." not in runs_on
        )

        strategy = next(
            (
                i
                for i, key, _v
                in fields
                if key == "strategy"
            ),
            None,
        )

        matrix = False
        multiplier: int | None = None

        if strategy is not None:
            strategy_fields = _children(
                lines,
                strategy,
                4,
            )

            matrix_index = next(
                (
                    i
                    for i, key, _v
                    in strategy_fields
                    if key == "matrix"
                ),
                None,
            )

            matrix_tail = next(
                (
                    value
                    for _i, key, value
                    in strategy_fields
                    if key == "matrix"
                ),
                "",
            )

            if matrix_index is not None:
                matrix = True

                if (
                    not matrix_tail
                    or matrix_tail in {
                        "{}",
                        "{ }",
                    }
                ):
                    axes: list[int] = []
                    complex_matrix = False

                    for _i, key, value in _children(
                        lines,
                        matrix_index,
                        6,
                    ):
                        if key in {
                            "include",
                            "exclude",
                        }:
                            complex_matrix = True
                            continue

                        items = _inline_list(value)

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
            Job(
                job_id=job_id,
                reusable=reusable,
                runs_on=runs_on,
                self_hosted=self_hosted,
                timeout=(
                    "timeout-minutes"
                    in values
                ),
                matrix=matrix,
                static_matrix=multiplier,
            )
        )

    return tuple(out)


def analyze(
    text: str,
    *,
    path: str,
    sha256: str,
    byte_size: int,
) -> Workflow:
    lines = text.splitlines()

    (
        triggers,
        props,
        schedules,
    ) = _triggers(lines)

    concurrency, cancel = (
        _concurrency(lines)
    )

    jobs = _jobs(lines)
    events = set(triggers)

    push = props.get("push", {})
    pr = props.get(
        "pull_request",
        {},
    )

    branch_scope = bool(
        push.get("branches")
        or push.get("branches-ignore")
    )

    push_paths = bool(
        push.get("paths")
        or push.get("paths-ignore")
    )

    pr_paths = bool(
        pr.get("paths")
        or pr.get("paths-ignore")
    )

    runners = [
        job
        for job in jobs
        if job.runs_on is not None
        and not job.reusable
    ]

    signals: list[str] = []

    if (
        {"push", "pull_request"}
        <= events
        and not branch_scope
    ):
        signals.append(
            "UNRESTRICTED_PUSH_PLUS_PR"
        )

    if (
        {"push", "pull_request"}
        <= events
        and (
            not push_paths
            or not pr_paths
        )
    ):
        signals.append(
            "BROAD_PUSH_PR_PATH_SURFACE"
        )

    if (
        events & RUN_EVENTS
        and runners
        and not concurrency
    ):
        signals.append(
            "RUN_EVENTS_WITHOUT_CONCURRENCY"
        )

    if (
        events & RUN_EVENTS
        and concurrency
        and not cancel
    ):
        signals.append(
            "CONCURRENCY_WITHOUT_CANCEL"
        )

    if (
        "schedule" in events
        and schedules
    ):
        signals.append(
            "SCHEDULED_RUNS"
        )

    if any(
        not job.timeout
        for job in runners
    ):
        signals.append(
            "RUNNER_JOB_MISSING_TIMEOUT"
        )

    if any(
        job.matrix
        for job in runners
    ):
        signals.append(
            "MATRIX_FANOUT"
        )

    if any(
        not job.self_hosted
        for job in runners
    ):
        signals.append(
            "HOSTED_OR_DYNAMIC_RUNNER_EXPOSURE"
        )

    if any(
        job.reusable
        for job in jobs
    ):
        signals.append(
            "REUSABLE_WORKFLOW_JOB"
        )

    return Workflow(
        path=path,
        sha256=sha256,
        bytes=byte_size,
        triggers=triggers,
        push_branch_scope=branch_scope,
        push_path_scope=push_paths,
        pr_path_scope=pr_paths,
        schedules=schedules,
        concurrency=concurrency,
        cancel_in_progress=cancel,
        jobs=jobs,
        signals=tuple(signals),
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
            for path in directory.glob(
                pattern
            )
            if path.is_file()
            and not path.is_symlink()
        )
    )


def analyze_file(
    path: Path,
    root: Path,
) -> Workflow:
    raw = path.read_bytes()

    if len(raw) > MAX_WORKFLOW_BYTES:
        raise ValueError(
            f"workflow too large: {path}"
        )

    text = raw.decode("utf-8")

    return analyze(
        text,
        path=str(
            path.relative_to(root)
        ),
        sha256=(
            hashlib
            .sha256(raw)
            .hexdigest()
        ),
        byte_size=len(raw),
    )


def summarize(
    root: Path,
    workflows: Sequence[Workflow],
) -> dict:
    triggers: Counter[str] = Counter()

    for workflow in workflows:
        triggers.update(
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
        and not job.reusable
    ]

    run_workflows = [
        workflow
        for workflow in workflows
        if (
            set(workflow.triggers)
            & RUN_EVENTS
        )
        and any(
            job.runs_on is not None
            and not job.reusable
            for job in workflow.jobs
        )
    ]

    return {
        "root": str(root),
        "workflow_files": len(
            workflows
        ),
        "trigger_counts": dict(
            sorted(triggers.items())
        ),
        "workflows_with_push_and_pr": sum(
            1
            for workflow in workflows
            if (
                {"push", "pull_request"}
                <= set(workflow.triggers)
            )
        ),
        "unrestricted_push_and_pr": sum(
            1
            for workflow in workflows
            if (
                "UNRESTRICTED_PUSH_PLUS_PR"
                in workflow.signals
            )
        ),
        "workflows_without_concurrency": sum(
            1
            for workflow in run_workflows
            if not workflow.concurrency
        ),
        "workflows_concurrency_without_cancel": sum(
            1
            for workflow in run_workflows
            if (
                workflow.concurrency
                and not workflow.cancel_in_progress
            )
        ),
        "scheduled_workflows": sum(
            1
            for workflow in workflows
            if "schedule"
            in workflow.triggers
        ),
        "schedule_entries": sum(
            workflow.schedules
            for workflow in workflows
        ),
        "runner_jobs": len(
            runners
        ),
        "explicit_self_hosted_jobs": sum(
            1
            for job in runners
            if job.self_hosted
        ),
        "hosted_or_dynamic_runner_jobs": sum(
            1
            for job in runners
            if not job.self_hosted
        ),
        "reusable_workflow_jobs": sum(
            1
            for job in jobs
            if job.reusable
        ),
        "jobs_missing_timeout": sum(
            1
            for job in runners
            if not job.timeout
        ),
        "matrix_jobs": sum(
            1
            for job in runners
            if job.matrix
        ),
        "known_static_matrix_runner_slots": sum(
            job.static_matrix
            for job in runners
            if job.static_matrix
            is not None
        ),
        "workflows": [
            dataclasses.asdict(workflow)
            for workflow in workflows
        ],
    }


def audit(
    root: Path,
) -> dict:
    root = root.resolve()

    return summarize(
        root,
        [
            analyze_file(path, root)
            for path in workflow_files(root)
        ],
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
        audit(root)
        for root in args.roots
    ]

    keys = (
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

    receipt = {
        "schema_version": 1,
        "mode": (
            "read_only_static_cost_surface"
        ),
        "dollar_cost_estimated": False,
        "repositories": repositories,
        "totals": {
            key: sum(
                int(repo[key])
                for repo in repositories
            )
            for key in keys
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
