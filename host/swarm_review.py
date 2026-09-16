#!/usr/bin/env python3
"""Hardened Commons swarm review surface.

The underlying reviewed implementation is retained byte-for-byte in
``swarm_review_core``.  This front door closes the provider-authority splice by
binding every executable execution receipt to one live PR, the exact current
main base, the exact head, the current synthetic merge identity, and the trusted
workflow blob.  Executable heads must contain current main, so main movement
forces recomposition to a new head and therefore a fresh provider run.
"""
from __future__ import annotations

from urllib.parse import quote

try:
    from . import swarm_review_core as _core
except ImportError:
    import swarm_review_core as _core

# Preserve the established public surface without making direct-script execution
# depend on package-relative imports.
for _name in dir(_core):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_core, _name)

_core_change = _core.change
_core_review_template = _core.review_template
_core_actions_authorities = _core.actions_authorities
_core_exact_execution_pass = _core.exact_execution_pass
ACTIONS_PROVIDER = _core.ACTIONS_PROVIDER
ACTIONS_WORKFLOW_PREFIX = _core.ACTIONS_WORKFLOW_PREFIX
BOILERPLATE_ACTION_STEPS = _core.BOILERPLATE_ACTION_STEPS
SHA = _core.SHA
paths_valid = _core.paths_valid
object_at = _core.object_at
cs = _core.cs


def _pr_identity(pull, main):
    """Return one canonical live PR/base/merge identity or None."""
    if not isinstance(pull, dict) or type(pull.get("number")) is not int:
        return None
    head = (pull.get("head") or {}).get("sha")
    base = pull.get("base") or {}
    base_ref = base.get("ref")
    base_sha = base.get("sha")
    merge_commit = pull.get("merge_commit_sha")
    if (not SHA.fullmatch(head or "") or base_ref != "main"
            or not SHA.fullmatch(main or "") or base_sha != main
            or not SHA.fullmatch(merge_commit or "")):
        return None
    return {
        "pull_number": pull["number"],
        "head": head,
        "base_ref": "main",
        "base": main,
        "merge_commit": merge_commit,
    }


def _commit_pull_associations(github, head):
    root = "/repos/" + github.repo
    rows = []
    for page in range(1, 11):
        part = github.rest(root + "/commits/" + head + "/pulls",
                           {"per_page": 100, "page": page})
        if not isinstance(part, list):
            raise ValueError("malformed commit-to-PR association census")
        rows.extend(row for row in part if isinstance(row, dict))
        if len(part) < 100:
            return rows
    raise ValueError("commit-to-PR association census truncated")


def _association_matches(row, identity):
    return (type(row.get("number")) is int
            and row.get("number") == identity["pull_number"]
            and (row.get("head") or {}).get("sha") == identity["head"]
            and (row.get("base") or {}).get("ref") == identity["base_ref"]
            and (row.get("base") or {}).get("sha") == identity["base"]
            and row.get("merge_commit_sha") == identity["merge_commit"])


def _run_pr_binding_ok(run, identity):
    """GitHub sometimes returns [] here; non-empty metadata must agree exactly."""
    rows = run.get("pull_requests")
    if rows in (None, []):
        return True
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        return False
    row = rows[0]
    number = row.get("number")
    if number != identity["pull_number"]:
        return False
    head = row.get("head") or {}
    base = row.get("base") or {}
    if head.get("sha") not in (None, identity["head"]):
        return False
    if base.get("ref") not in (None, identity["base_ref"]):
        return False
    if base.get("sha") not in (None, identity["base"]):
        return False
    return True


def _workflow_blob(github, path, base):
    root = "/repos/" + github.repo
    reply = github.rest(root + "/contents/" + quote(path, safe="/"), {"ref": base})
    if (not isinstance(reply, dict) or reply.get("type") not in (None, "file")
            or not SHA.fullmatch(reply.get("sha") or "")):
        return None
    return reply["sha"]


def actions_authorities(github, pull, main=None):
    """Re-read successful jobs bound to one exact live PR/current-base context.

    The two-argument form is retained only for the established pure unit-test/API
    surface.  Live integration always passes the pull object and current main.
    """
    if isinstance(pull, str) and main is None:
        return _core_actions_authorities(github, pull)
    identity = _pr_identity(pull, main)
    if identity is None:
        return []
    associations = _commit_pull_associations(github, identity["head"])
    # Fail closed on head reuse: one exact head must identify one and only one PR.
    if len(associations) != 1 or not _association_matches(associations[0], identity):
        return []

    root = "/repos/" + github.repo
    runs = []
    for page in range(1, 11):
        reply = github.rest(root + "/actions/runs", {
            "head_sha": identity["head"], "event": "pull_request",
            "per_page": 100, "page": page})
        part = reply.get("workflow_runs") or []
        if not isinstance(part, list):
            raise ValueError("malformed GitHub Actions run census")
        runs.extend(row for row in part if isinstance(row, dict))
        if len(part) < 100:
            break
    else:
        raise ValueError("exact-head GitHub Actions run census truncated")

    result = []
    workflow_blobs = {}
    for run in runs:
        path = run.get("path")
        run_id = run.get("id")
        if (run.get("head_sha") != identity["head"] or run.get("event") != "pull_request"
                or run.get("status") != "completed" or run.get("conclusion") != "success"
                or type(run_id) is not int or not isinstance(path, str)
                or not path.startswith(ACTIONS_WORKFLOW_PREFIX) or not paths_valid([path])
                or not _run_pr_binding_ok(run, identity)):
            continue
        if path not in workflow_blobs:
            workflow_blobs[path] = _workflow_blob(github, path, identity["base"])
        workflow_blob = workflow_blobs[path]
        if not workflow_blob:
            continue
        jobs = []
        for page in range(1, 11):
            reply = github.rest(root + "/actions/runs/" + str(run_id) + "/jobs",
                                {"filter": "latest", "per_page": 100, "page": page})
            part = reply.get("jobs") or []
            if not isinstance(part, list):
                raise ValueError("malformed GitHub Actions job census")
            jobs.extend(row for row in part if isinstance(row, dict))
            if len(part) < 100:
                break
        else:
            raise ValueError("exact-head GitHub Actions job census truncated")
        for job in jobs:
            job_id = job.get("id")
            if (type(job_id) is not int or job.get("status") != "completed"
                    or job.get("conclusion") != "success"
                    or not isinstance(job.get("name"), str) or not job["name"].strip()):
                continue
            steps = {}
            for step in job.get("steps") or []:
                if (isinstance(step, dict) and isinstance(step.get("name"), str)
                        and step["name"] not in BOILERPLATE_ACTION_STEPS):
                    steps[step["name"]] = step.get("conclusion")
            successful = sorted(name for name, conclusion in steps.items()
                                if conclusion == "success")
            if not successful:
                continue
            result.append({
                "provider": ACTIONS_PROVIDER,
                **identity,
                "run_id": run_id,
                "job_id": job_id,
                "job_name": job["name"],
                "workflow_path": path,
                "workflow_blob": workflow_blob,
                "reference": run.get("html_url") or run.get("url") or "",
                "steps": successful,
            })
    return result


def exact_execution_pass(git, items, subject, base):
    """Require exact provider identity + trusted workflow bytes + current-base composition.

    Subjects manufactured directly by legacy unit helpers have no live execution
    context; preserve that pure-function test surface.  The mutation path always
    comes through ``verify_live`` and therefore always carries provider context.
    """
    if not subject.get("execution_context"):
        return _core_exact_execution_pass(git, items, subject, base)
    if (not SHA.fullmatch(subject.get("head") or "") or not SHA.fullmatch(base or "")
            or subject.get("merge_base") != subject.get("main")):
        return False
    context = subject.get("execution_context")
    if not isinstance(context, dict):
        return False
    expected_context = {
        "pull_number": subject.get("number"), "head": subject.get("head"),
        "base_ref": "main", "base": subject.get("main"),
        "merge_commit": context.get("merge_commit"),
    }
    if context != expected_context or not SHA.fullmatch(context.get("merge_commit") or ""):
        return False
    authorities = subject.get("execution_authority")
    if not isinstance(authorities, list):
        return False
    for evidence in items if isinstance(items, list) else ():
        if (not isinstance(evidence, dict) or evidence.get("result") != "PASS"
                or evidence.get("kind") != "execution"
                or evidence.get("provider") != ACTIONS_PROVIDER
                or any(evidence.get(k) != v for k, v in expected_context.items())
                or type(evidence.get("run_id")) is not int
                or type(evidence.get("job_id")) is not int
                or not isinstance(evidence.get("workflow_path"), str)
                or not SHA.fullmatch(evidence.get("workflow_blob") or "")
                or not isinstance(evidence.get("steps"), list) or not evidence["steps"]
                or not all(isinstance(step, str) and step.strip() for step in evidence["steps"])
                or not isinstance(evidence.get("reference"), str)
                or not evidence["reference"].strip()):
            continue
        path = evidence["workflow_path"]
        if (not paths_valid([path]) or not path.startswith(ACTIONS_WORKFLOW_PREFIX)
                or path in subject["paths"]):
            continue
        blob = evidence["workflow_blob"]
        if (object_at(git, base, path) != blob
                or object_at(git, subject["main"], path) != blob
                or object_at(git, subject["head"], path) != blob):
            continue
        wanted_steps = set(evidence["steps"])
        for authority in authorities:
            if (isinstance(authority, dict)
                    and all(authority.get(k) == v for k, v in expected_context.items())
                    and authority.get("provider") == ACTIONS_PROVIDER
                    and authority.get("run_id") == evidence["run_id"]
                    and authority.get("job_id") == evidence["job_id"]
                    and authority.get("workflow_path") == path
                    and authority.get("workflow_blob") == blob
                    and authority.get("reference") == evidence["reference"]
                    and wanted_steps.issubset(set(authority.get("steps") or []))):
                return True
    return False


def change(git, main, pull):
    subject = _core_change(git, main, pull)
    context = pull.get("_execution_context") or {}
    if not isinstance(context, dict):
        raise ValueError("malformed exact PR/base/merge execution context")
    if subject.get("execution_required") and context and subject.get("merge_base") != main:
        raise ValueError("executable PR head must contain current main; recompose and rerun provider checks")
    subject["execution_context"] = context
    return subject


def review_template(subject):
    value = _core_review_template(subject)
    value["execution_context"] = subject.get("execution_context")
    return value


def live_pull(github, number, main=None):
    root = "/repos/" + github.repo + "/pulls/" + str(int(number))
    pull = github.rest(root)
    reviews = []
    for page in range(1, 21):
        part = github.rest(root + "/reviews", {"per_page": 100, "page": page})
        if not isinstance(part, list):
            raise ValueError("malformed review history")
        reviews.extend(part)
        if len(part) < 100:
            break
    else:
        raise ValueError("review history truncated; cannot authorize integration")
    pull["reviews"] = reviews
    if main is None:
        main = cs.fetch_main(github)["sha"]
    identity = _pr_identity(pull, main)
    pull["_execution_context"] = identity or {}
    pull["_execution_authority"] = actions_authorities(github, pull, main)
    return pull


def verify_live(git, github, number):
    main = cs.fetch_main(github)["sha"]
    pull = live_pull(github, number, main)
    if pull.get("state") != "open" or pull.get("merged"):
        raise ValueError("PR is no longer open")
    bases = [r.get("reviewed_base") for r in
             (_core.block(x.get("body"), "commons-gpt-review") or {} for x in pull["reviews"])]
    git.fetch([main, pull["head"]["sha"]] + [b for b in bases if SHA.fullmatch(b or "")])
    subject = change(git, main, pull)
    return subject, _core.decision(git, subject, pull["reviews"])


# Patch the retained core module so its decision/CLI paths call the hardened gates.
_core.actions_authorities = actions_authorities
_core.exact_execution_pass = exact_execution_pass
_core.change = change
_core.review_template = review_template
_core.live_pull = live_pull
_core.verify_live = verify_live

# Re-export the patched entry point explicitly (star import happened before monkey patching).
main = _core.main

if __name__ == "__main__":
    raise SystemExit(main())
