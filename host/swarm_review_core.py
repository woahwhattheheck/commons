#!/usr/bin/env python3
"""GPT review packets and merge decisions for the existing Commons command center.

No model calls, scheduler, PR-code execution, or new queue. GitHub reviews are
semantic receipts; exact-head execution authority is re-read from GitHub Actions.
State/coordination is the derived view. Family is attested, not authenticated:
shared GitHub credentials cannot establish model identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    from . import coordination_state as cs
except ImportError:
    import coordination_state as cs

SCHEMA = "commons-gpt-review/v1"
POLICY = "ground/SWARM_ORDER.md"
RELIABILITY = "ground/SWARM_RELIABILITY.json"
GPT = "gpt"
SHA = re.compile(r"^[0-9a-f]{40}$")
DOC_ONLY_SUFFIXES = frozenset({".md", ".rst", ".adoc"})
DOC_ONLY_FILE_MODES = frozenset({"100644"})
ACTIONS_PROVIDER = "github-actions"
ACTIONS_WORKFLOW_PREFIX = ".github/workflows/"
BOILERPLATE_ACTION_STEPS = frozenset({"Set up job", "Complete job"})


def block(text, fence):
    hits = re.findall(r"(?m)^```" + re.escape(fence) + r"\s*\n(.*?)\n```\s*$",
                      text or "", re.S)
    if len(hits) != 1:
        return None
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        value = json.loads(hits[0], object_pairs_hook=unique)
        return value if isinstance(value, dict) else None
    except (ValueError, TypeError):
        return None


def paths_valid(paths):
    return (isinstance(paths, list) and bool(paths) and len(paths) <= 2000
            and all(isinstance(p, str) and p and not p.startswith(("/", "-"))
                    and "\\" not in p and all(x not in ("", ".", "..")
                                              for x in p.split("/")) for p in paths))


def overlap(left, right):
    return any(a == b or a.startswith(b + "/") or b.startswith(a + "/")
               for a in left for b in right)


def risk(paths):
    control = {"AGENTS.md", "CLAUDE.md", "DIRECTIVES.md", "START.md", POLICY,
               RELIABILITY, "host/swarm_review.py", "host/coordination_state.py"}
    if any(p in control or p.startswith((".github/", ".cursor/", ".claude/"))
           or re.search(r"(^|/)(runtime|promotion-gate|champion-ratchet|exports)(/|$)", p)
           or re.search(r"(^|/)(build[^/]*\.py|.*CONFIG.*|.*CANONICAL.*|.*CURRENT.*)$", p)
           for p in paths):
        return "critical"
    return "standard"


def object_at(git, ref, path):
    if not SHA.fullmatch(ref or "") or not paths_valid([path]):
        raise ValueError("invalid read-set subject")
    result = git.run("rev-parse", "--verify", ref + ":" + path, check=False)
    return result.stdout.strip() if result.returncode == 0 else "ABSENT"


def evidence_pass(items):
    return (isinstance(items, list) and bool(items)
            and all(isinstance(e, dict) and e.get("result") == "PASS"
                    and isinstance(e.get("reference"), str) and e["reference"].strip()
                    for e in items))


def execution_required(changes):
    """Only inert non-executable documentation changes may omit execution evidence."""
    paths = [change[1] for change in changes if len(change) > 1]
    if not paths or risk(paths) == "critical":
        return True
    for change in changes:
        if len(change) < 4:
            return True
        _, path, old_mode, new_mode = change[:4]
        if Path(path).suffix.lower() not in DOC_ONLY_SUFFIXES:
            return True
        for mode in (old_mode, new_mode):
            if mode != "000000" and mode not in DOC_ONLY_FILE_MODES:
                return True
    return False


def actions_authorities(github, head):
    """Re-read exact-head successful PR jobs from GitHub, never from review prose."""
    if not SHA.fullmatch(head or ""):
        raise ValueError("invalid execution head")
    root = "/repos/" + github.repo
    runs = []
    for page in range(1, 11):
        reply = github.rest(root + "/actions/runs", {
            "head_sha": head, "event": "pull_request", "per_page": 100, "page": page})
        part = reply.get("workflow_runs") or []
        if not isinstance(part, list):
            raise ValueError("malformed GitHub Actions run census")
        runs.extend(r for r in part if isinstance(r, dict))
        if len(part) < 100:
            break
    else:
        raise ValueError("exact-head GitHub Actions run census truncated")

    result = []
    for run in runs:
        path = run.get("path")
        run_id = run.get("id")
        if (run.get("head_sha") != head or run.get("event") != "pull_request"
                or run.get("status") != "completed" or run.get("conclusion") != "success"
                or type(run_id) is not int or not isinstance(path, str)
                or not path.startswith(ACTIONS_WORKFLOW_PREFIX) or not paths_valid([path])):
            continue
        jobs = []
        for page in range(1, 11):
            reply = github.rest(root + "/actions/runs/" + str(run_id) + "/jobs",
                                {"filter": "latest", "per_page": 100, "page": page})
            part = reply.get("jobs") or []
            if not isinstance(part, list):
                raise ValueError("malformed GitHub Actions job census")
            jobs.extend(j for j in part if isinstance(j, dict))
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
                "head": head,
                "run_id": run_id,
                "job_id": job_id,
                "job_name": job["name"],
                "workflow_path": path,
                "reference": run.get("html_url") or run.get("url") or "",
                "steps": successful,
            })
    return result


def exact_execution_pass(git, items, subject, base):
    """Require a review pointer to an independently re-read exact-head provider job."""
    if not SHA.fullmatch(subject.get("head") or "") or not SHA.fullmatch(base or ""):
        return False
    authorities = subject.get("execution_authority")
    if not isinstance(authorities, list):
        return False
    for evidence in items if isinstance(items, list) else ():
        if (not isinstance(evidence, dict) or evidence.get("result") != "PASS"
                or evidence.get("kind") != "execution"
                or evidence.get("provider") != ACTIONS_PROVIDER
                or evidence.get("head") != subject["head"]
                or type(evidence.get("run_id")) is not int
                or type(evidence.get("job_id")) is not int
                or not isinstance(evidence.get("workflow_path"), str)
                or not isinstance(evidence.get("workflow_blob"), str)
                or not isinstance(evidence.get("steps"), list)
                or not evidence["steps"]
                or not all(isinstance(step, str) and step.strip() for step in evidence["steps"])
                or not isinstance(evidence.get("reference"), str) or not evidence["reference"].strip()):
            continue
        path = evidence["workflow_path"]
        if (not paths_valid([path]) or not path.startswith(ACTIONS_WORKFLOW_PREFIX)
                or path in subject["paths"] or not SHA.fullmatch(evidence["workflow_blob"])):
            continue
        if (object_at(git, base, path) != evidence["workflow_blob"]
                or object_at(git, subject["main"], path) != evidence["workflow_blob"]):
            continue
        wanted_steps = set(evidence["steps"])
        for authority in authorities:
            if (isinstance(authority, dict)
                    and authority.get("provider") == ACTIONS_PROVIDER
                    and authority.get("head") == subject["head"]
                    and authority.get("run_id") == evidence["run_id"]
                    and authority.get("job_id") == evidence["job_id"]
                    and authority.get("workflow_path") == path
                    and authority.get("reference") == evidence["reference"]
                    and wanted_steps.issubset(set(authority.get("steps") or []))):
                return True
    return False


def change(git, main, pull):
    head = pull.get("headRefOid") or (pull.get("head") or {}).get("sha")
    base_ref = pull.get("baseRefName") or (pull.get("base") or {}).get("ref")
    if not SHA.fullmatch(head or "") or base_ref != "main":
        raise ValueError("expected an exact PR head targeting main")
    base = git.merge_base(main, head)
    if base is None:
        raise ValueError("merge base unavailable; fetch history before review")
    changes = git.diff_tree(base, head)
    paths = sorted(c[1] for c in changes)
    metadata = block(pull.get("body"), "commons-work") or {}
    reads = metadata.get("read_paths", [])
    if not isinstance(reads, list) or (reads and not paths_valid(reads)):
        raise ValueError("invalid declared dependencies")
    reads = sorted(set(paths + reads + [POLICY, "AGENTS.md"]))
    authority = pull.get("_execution_authority", [])
    if not isinstance(authority, list) or not all(isinstance(row, dict) for row in authority):
        raise ValueError("malformed provider execution authority")
    key = cs.content_key(changes)
    return {
        "number": pull["number"], "head": head, "main": main, "merge_base": base,
        "content_key": key, "paths": paths, "risk": risk(paths), "work": metadata,
        "execution_required": execution_required(changes),
        "execution_authority": authority,
        "read_set": {p: object_at(git, main, p) for p in reads},
        "base_ref": base_ref,
        "draft": bool(pull.get("isDraft", pull.get("draft", False))),
        "overlap": sorted(set(paths) & git.changed_paths(base, main)),
    }


def review_template(subject):
    return {"schema": SCHEMA, "decision": "PENDING", "head": subject["head"],
            "reviewed_base": subject["main"], "content_key": subject["content_key"],
            "author_seat": subject["work"].get("seat"),
            "operation": subject["work"].get("operation"),
            "work_sha256": work_digest(subject["work"]),
            "risk": subject["risk"], "read_set": subject["read_set"],
            "execution_required": subject["execution_required"],
            "execution_authority": subject["execution_authority"],
            "reviewer": {"seat": "", "family": GPT, "session_ref": ""},
            "summary": "", "evidence": []}


def work_digest(work):
    return hashlib.sha256(json.dumps(work, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def review_nodes(pull):
    reviews = pull.get("reviews") or []
    return reviews.get("nodes", []) if isinstance(reviews, dict) else reviews


def decision(git, subject, reviews):
    def result(state, why, receipt=None):
        return {"state": state, "reason": why, "receipt": receipt}
    work = subject["work"]
    if not subject["paths"]:
        return result("ALREADY_PRESENT", "no unlanded change")
    if subject["draft"]:
        return result("BUILDING", "draft: continue isolated work")
    if not all(isinstance(work.get(k), str) and work[k].strip()
               for k in ("seat", "family", "operation")):
        return result("NEEDS_PACKET", "declare seat, family and stable operation in commons-work")
    if not evidence_pass(work.get("evidence")):
        return result("NEEDS_EVIDENCE", "supply applicable passing evidence before GPT review")
    if subject["overlap"]:
        return result("COMPOSE", "main changed the same paths; compose and recheck first")
    current = []
    for review in reviews:
        commit = (review.get("commit") or {}).get("oid") or review.get("commit_id")
        if commit != subject["head"] or review.get("state") == "DISMISSED":
            continue
        value = block(review.get("body"), "commons-gpt-review")
        if value or review.get("state") == "CHANGES_REQUESTED":
            current.append((review.get("submittedAt") or review.get("submitted_at") or "",
                            str(review.get("databaseId") or review.get("id") or ""),
                            value, review))
    if not current:
        return result("WAIT_GPT", "no GPT receipt for these exact bytes")
    _, _, receipt, record = max(current, key=lambda x: (x[0], x[1]))
    if not receipt or record.get("state") == "CHANGES_REQUESTED":
        return result("HOLD", "latest review requests changes")
    if receipt.get("decision") != "PASS":
        return result("HOLD", "latest explicit GPT decision is not PASS")
    reviewer = receipt.get("reviewer") or {}
    if (receipt.get("schema") != SCHEMA or reviewer.get("family") != GPT
            or not reviewer.get("seat") or not reviewer.get("session_ref")
            or not isinstance(receipt.get("summary"), str) or not receipt["summary"].strip()):
        return result("HOLD", "incomplete GPT session attestation")
    if work["family"].lower() != GPT and reviewer["seat"].casefold() == work["seat"].casefold():
        return result("HOLD", "non-GPT author cannot attest its own GPT review")
    for field, expected in (("head", subject["head"]), ("content_key", subject["content_key"]),
                            ("author_seat", work["seat"]), ("operation", work["operation"]),
                            ("work_sha256", work_digest(work)),
                            ("risk", subject["risk"])):
        if receipt.get(field) != expected:
            return result("HOLD", "review subject changed: " + field)
    if not evidence_pass(receipt.get("evidence")):
        return result("HOLD", "GPT receipt lacks passing verification evidence")
    needs_execution = subject["execution_required"]
    if receipt.get("execution_required", needs_execution) != needs_execution:
        return result("HOLD", "review execution requirement does not match changed objects")
    base = receipt.get("reviewed_base")
    if not SHA.fullmatch(base or "") or git.merge_base(base, subject["main"]) != base:
        return result("HOLD", "reviewed base is not an ancestor of current main")
    if needs_execution and not exact_execution_pass(
            git, receipt.get("evidence"), subject, base):
        return result("HOLD", "non-document change lacks provider-verified exact-head execution")
    tier = scrutiny(work["seat"], read_outcomes(git, subject["main"]))
    if tier == "individual":
        preflight = receipt.get("preflight") or {}
        if (not preflight.get("seat") or preflight["seat"].casefold() == work["seat"].casefold()
                or not evidence_pass(preflight.get("evidence"))
                or (needs_execution and not exact_execution_pass(
                    git, preflight.get("evidence"), subject, base))):
            return result("HOLD", "recent evidenced regression requires independent preflight")
    reads = receipt.get("read_set")
    if not isinstance(reads, dict) or not paths_valid(list(reads)):
        return result("HOLD", "missing or malformed dependency read set")
    if not set(subject["read_set"]).issubset(reads):
        return result("HOLD", "review omitted a changed path or declared dependency")
    for path, oid in reads.items():
        if oid != object_at(git, base, path) or oid != object_at(git, subject["main"], path):
            return result("WAIT_GPT", "review dependency changed: " + path)
    return result("READY", "GPT reviewed these bytes; provider execution and base dependencies are current",
                  {"id": record.get("databaseId") or record.get("id"),
                   "url": record.get("url") or record.get("html_url"),
                   "reviewer": reviewer["seat"]})


def read_outcomes(git, main):
    raw = git.run("show", main + ":" + RELIABILITY, check=False)
    if raw.returncode != 0:
        if object_at(git, main, RELIABILITY) == "ABSENT":
            return []
        raise ValueError("reliability observations unavailable; fetch the pinned file")
    value = json.loads(raw.stdout)
    if not isinstance(value, dict) or not isinstance(value.get("outcomes"), list):
        raise ValueError("malformed reliability observations")
    return value["outcomes"]


def scrutiny(seat, outcomes):
    rows = [r for r in outcomes if r.get("seat") == seat and r.get("source_url")
            and r.get("observed_at") and r.get("outcome") in ("accepted", "regression")]
    unique = {}
    for row in sorted(rows, key=lambda r: r["observed_at"]):
        unique[row["source_url"]] = row
    rows = sorted(unique.values(), key=lambda r: r["observed_at"], reverse=True)[:20]
    if any(r["outcome"] == "regression" for r in rows):
        return "individual"
    return "established" if len(rows) >= 10 else "new"


def batches(rows, outcomes=(), capacity=None):
    """Plan only; capacity is available review batches, not inferred token quota."""
    if capacity is not None and (type(capacity) is not int or capacity < 0):
        raise ValueError("capacity must be a nonnegative count or unknown")
    waiting = sorted((r for r in rows if r.get("review", {}).get("state") == "WAIT_GPT"),
                     key=lambda r: (r.get("risk") != "critical", r.get("created_at") or "9999", r["number"]))
    result = []
    for row in waiting:
        tier = scrutiny((row.get("work") or {}).get("seat"), outcomes)
        limit = 1 if row.get("risk") == "critical" or tier == "individual" else (10 if tier == "established" else 3)
        read_paths = list((row.get("work") or {}).get("read_paths", [])) + row.get("paths", [])
        for group in result:
            if (len(group["prs"]) < min(group["limit"], limit)
                    and not overlap(group["paths"], read_paths)
                    and not overlap(group["reads"], row.get("paths", []))):
                group["prs"].append(row["number"])
                group["paths"].extend(row.get("paths", []))
                group["reads"].extend(read_paths)
                group["limit"] = min(group["limit"], limit)
                break
        else:
            result.append({"prs": [row["number"]], "limit": limit,
                           "paths": list(row.get("paths", [])),
                           "reads": read_paths,
                           "independent_preflight": tier == "individual"})
    for i, group in enumerate(result):
        group.pop("paths")
        group.pop("reads")
        group["dispatch"] = "UNKNOWN_CAPACITY" if capacity is None else (
            "REVIEW_NOW" if i < capacity else "STAGED")
    return result


def annotate(git, main, pull):
    work = block(pull.get("body"), "commons-work") or {}
    if not all(work.get(k) for k in ("seat", "family", "operation")):
        return {"work": {}, "risk": "unknown", "review": {
            "state": "NEEDS_PACKET", "reason": "declare seat, family and operation before integration"}}
    try:
        subject = change(git, main, pull)
        verdict = decision(git, subject, review_nodes(pull))
        return {"work": subject["work"], "risk": subject["risk"], "review": verdict}
    except (ValueError, cs.GitError) as exc:
        return {"work": {}, "risk": "unknown", "review": {"state": "UNKNOWN", "reason": str(exc)[:200]}}


def live_pull(github, number):
    root = "/repos/" + github.repo + "/pulls/" + str(int(number))
    pull = github.rest(root)
    reviews = []
    for page in range(1, 21):
        part = github.rest(root + "/reviews", {"per_page": 100, "page": page})
        reviews.extend(part)
        if len(part) < 100:
            break
    else:
        raise ValueError("review history truncated; cannot authorize integration")
    pull["reviews"] = reviews
    head = (pull.get("head") or {}).get("sha")
    pull["_execution_authority"] = actions_authorities(github, head)
    return pull


def verify_live(git, github, number):
    pull = live_pull(github, number)
    if pull.get("state") != "open" or pull.get("merged"):
        raise ValueError("PR is no longer open")
    main = cs.fetch_main(github)["sha"]
    bases = [r.get("reviewed_base") for r in
             (block(x.get("body"), "commons-gpt-review") or {} for x in pull["reviews"])]
    git.fetch([main, pull["head"]["sha"]] + [b for b in bases if SHA.fullmatch(b or "")])
    subject = change(git, main, pull)
    return subject, decision(git, subject, pull["reviews"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=cs.DEFAULT_REPO)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    packet = sub.add_parser("packet")
    packet.add_argument("--prs", required=True)
    packet.add_argument("--out", required=True)
    check = sub.add_parser("check")
    check.add_argument("--pr", type=int, required=True)
    merge = sub.add_parser("merge")
    merge.add_argument("--pr", type=int, required=True)
    args = parser.parse_args(argv)
    git = cs.Git(str(Path(args.root).resolve()))
    github = cs.GitHub(args.repo, cs.discover_token())
    try:
        if args.command == "packet":
            numbers = list(dict.fromkeys(int(n) for n in args.prs.split(",")))
            if not 1 <= len(numbers) <= 10:
                raise ValueError("one packet holds 1–10 PRs")
            entries = []
            for number in numbers:
                subject, verdict = verify_live(git, github, number)
                diff = git.out("diff", "--no-ext-diff", "--no-textconv",
                               subject["merge_base"], subject["head"], "--", *subject["paths"])
                entries.append({**subject, "review": verdict,
                                "diff": diff[:60000], "diff_truncated": len(diff) > 60000,
                                "review_template": review_template(subject)})
            output = {"schema": "commons-review-packet/v1", "observed_at": cs._iso(cs._now()),
                      "prs": entries, "note": "GPT must read omitted diff content before approving; no automatic approval."}
            Path(args.out).write_text(json.dumps(output, indent=2) + "\n")
            print(json.dumps({"written": args.out, "prs": numbers}))
            return 0
        subject, verdict = verify_live(git, github, args.pr)
        if verdict["state"] != "READY":
            print(json.dumps(verdict))
            return 1
        if args.command == "merge":
            # Re-read immediately before mutation. GitHub also checks head SHA.
            subject, verdict = verify_live(git, github, args.pr)
            if verdict["state"] != "READY":
                print(json.dumps(verdict))
                return 1
            # Publish a merge commit with the reviewed main as its first parent.
            # A normal fast-forward push rejects a concurrent main advance;
            # REST /pulls/N/merge checks head but cannot compare-and-swap base.
            changes = git.diff_tree(subject["merge_base"], subject["head"])
            tree = git.compose(subject["main"], changes)
            commit = git.out("commit-tree", tree, "-p", subject["main"], "-p", subject["head"],
                             "-m", "Merge reviewed Commons PR #" + str(args.pr),
                             env=cs._commit_env()).strip()
            pushed = git.run("push", "origin", commit + ":refs/heads/main", check=False)
            print(json.dumps({"merged": pushed.returncode == 0, "sha": commit,
                              "reviewed_head": subject["head"], "reviewed_base": subject["main"],
                              "reason": "landed" if pushed.returncode == 0 else
                              "push rejected; re-read main and recompute, never force"}))
            return 0 if pushed.returncode == 0 else 1
        print(json.dumps(verdict))
        return 0
    except (ValueError, cs.GitError, cs.GitHubError) as exc:
        print(json.dumps({"state": "UNKNOWN", "reason": str(exc)[:300]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
