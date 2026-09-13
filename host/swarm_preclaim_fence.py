#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only multi-key custody fence used before a swarm source branch is bound.

The fence complements ``coordination_state.py``. It never writes GitHub or
Slack; unsafe decisions return non-zero exit codes so a caller can hard-block
branch creation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import PurePosixPath

try:
    from coordination_state import GitHub, discover_token
except ImportError:
    from host.coordination_state import GitHub, discover_token

SAFE = "SAFE_TO_BIND_BRANCH"
OWNED = "OWNED"
ABSORBED = "ALREADY_ABSORBED"
MANUAL = "NEEDS_MANUAL_DIFF"
SAFE_TO_BIND_BRANCH = SAFE
ALREADY_ABSORBED = ABSORBED
NEEDS_MANUAL_DIFF = MANUAL
EXIT_CODE = {SAFE: 0, OWNED: 20, ABSORBED: 21, MANUAL: 22}

CUSTODY_RE = re.compile(
    r"\b(?:TAKE|CLAIM(?:ED)?|CUSTODY|MERGE[- ]SUCCESSOR|SOURCE\+MERGE|I\s+OWN|OWNERSHIP)\b",
    re.I,
)
RELEASE_RE = re.compile(r"\b(?:YIELD|RELEASED?|UNCLAIMED)\b", re.I)
TARGET_RE = re.compile(
    r"^(?:https://github\.com/)?(?P<owner>[^/\s]+)/(?P<repo>[^/#\s]+)"
    r"(?:(?:/(?P<kind>pull|pulls|issue|issues)/)|#)(?P<number>\d+)/?$"
)


class EvidenceError(RuntimeError):
    pass


def parse_target(value):
    m = TARGET_RE.match(value.strip())
    if not m:
        raise ValueError("target must be a GitHub pull/issue URL or owner/repo#number")
    kind = m.group("kind")
    if kind:
        kind = "pull" if kind.startswith("pull") else "issue"
    return {"repo": f"{m.group('owner')}/{m.group('repo')}",
            "number": int(m.group("number")), "kind": kind}


def _custody(hit, exact=False):
    if hit.get("custody") is not None:
        return bool(hit["custody"])
    text = str(hit.get("text") or "")
    if RELEASE_RE.search(text):
        return False
    return bool(CUSTODY_RE.search(text)) or (exact and bool(text.strip()))


def ownership_evidence(report):
    owned = []
    slack = report.get("slack") or {}
    for bucket, exact in (("stable_id_hits", False),
                          ("exact_target_hits", True),
                          ("path_semantic_hits", False)):
        for hit in slack.get(bucket) or []:
            if _custody(hit, exact):
                item = dict(hit)
                item["evidence_bucket"] = bucket
                owned.append(item)
    return owned


def decide(report):
    if report.get("errors"):
        return MANUAL
    if ownership_evidence(report):
        return OWNED
    if (report.get("upstream") or {}).get("kind") != "pull":
        return SAFE
    comparisons = report.get("blob_comparisons") or []
    if comparisons and all(x.get("comparable") and x.get("match") for x in comparisons):
        return ABSORBED
    return MANUAL


def finalize(report):
    out = dict(report)
    out["ownership_evidence"] = ownership_evidence(report)
    out["decision"] = decide(report)
    out["branch_write_allowed"] = out["decision"] == SAFE
    out["exit_code"] = EXIT_CODE[out["decision"]]
    return out


class SlackSearch:
    """Read-only Slack ``search.messages`` client with full-tail paging."""

    def __init__(self, token):
        self.token = token.strip()

    def search(self, query, limit=1000):
        if not self.token:
            raise EvidenceError(
                "Slack search token missing; set SLACK_USER_TOKEN/SLACK_TOKEN "
                "or pass --slack-evidence"
            )
        out, page = [], 1
        while len(out) < limit:
            params = urllib.parse.urlencode({
                "query": query, "count": min(100, limit - len(out)), "page": page,
            })
            req = urllib.request.Request(
                "https://slack.com/api/search.messages?" + params,
                headers={"Authorization": "Bearer " + self.token,
                         "User-Agent": "commons-swarm-preclaim-fence"},
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                raise EvidenceError(f"Slack search failed for {query!r}: {exc}") from exc
            if not payload.get("ok"):
                raise EvidenceError(
                    f"Slack search failed for {query!r}: {payload.get('error', 'unknown_error')}"
                )
            messages = payload.get("messages") or {}
            matches = messages.get("matches") or []
            for match in matches:
                channel = match.get("channel") or {}
                out.append({
                    "query": query, "ts": match.get("ts"),
                    "channel": channel.get("name") or channel.get("id"),
                    "username": match.get("username"),
                    "permalink": match.get("permalink"),
                    "text": match.get("text") or "",
                })
                if len(out) >= limit:
                    break
            pages = int((messages.get("paging") or {}).get("pages") or 1)
            if not matches or page >= pages:
                break
            page += 1
        return out


def _dedupe(hits):
    seen, out = set(), []
    for hit in hits:
        key = (hit.get("channel"), hit.get("ts"), hit.get("text"))
        if key not in seen:
            seen.add(key)
            out.append(hit)
    return out


def _semantic_queries(paths, tokens):
    values = []
    for path in paths:
        values.append(path)
        stem = PurePosixPath(path).stem
        if len(stem) >= 6:
            values.append(stem)
    values.extend(tokens)
    return list(dict.fromkeys(x for x in values if x))


def collect_slack(searcher, target, stable_id, candidate_paths, semantic_tokens):
    stable, exact, semantic = [], [], []
    if stable_id:
        stable += searcher.search(stable_id)
    short = target["repo"].split("/", 1)[1]
    n = target["number"]
    for query in (f'"{target["repo"]}#{n}"', f'"{short}#{n}"', f'"{short}" "#{n}"'):
        exact += searcher.search(query)
    for query in _semantic_queries(candidate_paths, semantic_tokens):
        semantic += searcher.search(f'"{query}"')
    return {"stable_id_hits": _dedupe(stable),
            "exact_target_hits": _dedupe(exact),
            "path_semantic_hits": _dedupe(semantic)}


def _owner_snapshot(github, repo):
    meta = github.rest(f"/repos/{repo}")
    branch = meta.get("default_branch") or "main"
    b = github.rest(f"/repos/{repo}/branches/{urllib.parse.quote(branch, safe='')}")
    commit = b.get("commit") or {}
    head = commit.get("sha")
    tree_sha = ((commit.get("commit") or {}).get("tree") or {}).get("sha")
    if not head or not tree_sha:
        raise EvidenceError(f"owner branch snapshot missing head/tree for {repo}:{branch}")
    tree = github.rest(f"/repos/{repo}/git/trees/{tree_sha}", {"recursive": "1"})
    if tree.get("truncated"):
        raise EvidenceError(f"owner tree for {repo}:{branch} was truncated")
    blobs = {x["path"]: x["sha"] for x in tree.get("tree") or []
             if x.get("type") == "blob" and x.get("path") and x.get("sha")}
    return ({"repo": repo, "default_branch": branch, "head_sha": head,
             "tree_sha": tree_sha, "tree_blob_count": len(blobs)}, blobs)


def _pull(github, repo, number):
    pr = github.rest(f"/repos/{repo}/pulls/{number}")
    files, page = [], 1
    while True:
        batch = github.rest(f"/repos/{repo}/pulls/{number}/files",
                            {"per_page": 100, "page": page})
        files += [{"path": x.get("filename"),
                   "previous_path": x.get("previous_filename"),
                   "status": x.get("status"), "blob_oid": x.get("sha")}
                  for x in batch]
        if len(batch) < 100:
            break
        page += 1
    return {"kind": "pull", "repo": repo, "number": number,
            "state": pr.get("state"), "title": pr.get("title"),
            "html_url": pr.get("html_url"),
            "head_sha": (pr.get("head") or {}).get("sha"),
            "base_sha": (pr.get("base") or {}).get("sha"),
            "changed_files": files}


def _issue(github, repo, number):
    issue = github.rest(f"/repos/{repo}/issues/{number}")
    return {"kind": "issue", "repo": repo, "number": number,
            "state": issue.get("state"), "title": issue.get("title"),
            "html_url": issue.get("html_url"), "head_sha": None,
            "changed_files": []}


def collect_github(github, owner_fork, target, candidate_paths):
    owner, owner_blobs = _owner_snapshot(github, owner_fork)
    if target.get("kind") == "pull":
        upstream = _pull(github, target["repo"], target["number"])
    elif target.get("kind") == "issue":
        upstream = _issue(github, target["repo"], target["number"])
    else:
        try:
            upstream = _pull(github, target["repo"], target["number"])
        except Exception as pull_error:
            try:
                upstream = _issue(github, target["repo"], target["number"])
            except Exception as issue_error:
                raise EvidenceError(
                    f"target could not be read as pull ({pull_error}) or issue ({issue_error})"
                ) from issue_error

    comparisons = []
    if upstream["kind"] == "pull":
        wanted = set(candidate_paths)
        changed = upstream.get("changed_files") or []
        relevant = [x for x in changed if not wanted or x.get("path") in wanted]
        if wanted:
            present = {x.get("path") for x in relevant}
            for path in sorted(wanted - present):
                comparisons.append({
                    "path": path, "upstream_status": "not_in_pr",
                    "upstream_blob_oid": None, "owner_blob_oid": owner_blobs.get(path),
                    "comparable": False, "match": False,
                    "reason": "candidate path is not in upstream PR changed files",
                })
        for item in relevant:
            path, status = item.get("path"), item.get("status")
            owner_oid = owner_blobs.get(path)
            donor_oid = None if status == "removed" else item.get("blob_oid")
            match = owner_oid is None if status == "removed" else bool(donor_oid) and donor_oid == owner_oid
            comparisons.append({
                "path": path, "upstream_status": status,
                "upstream_blob_oid": donor_oid, "owner_blob_oid": owner_oid,
                "comparable": status == "removed" or bool(donor_oid), "match": bool(match),
            })
    return owner, upstream, comparisons


def collect_report(owner_fork, target_value, stable_id, candidate_paths,
                   semantic_tokens, github, slack_searcher):
    target = parse_target(target_value)
    errors = []
    slack = {"stable_id_hits": [], "exact_target_hits": [], "path_semantic_hits": []}
    owner, upstream, comparisons = {}, {"kind": None, "repo": target["repo"],
                                        "number": target["number"]}, []
    try:
        slack = collect_slack(slack_searcher, target, stable_id,
                              candidate_paths, semantic_tokens)
    except Exception as exc:
        errors.append(f"slack: {exc.__class__.__name__}: {exc}")
    try:
        owner, upstream, comparisons = collect_github(
            github, owner_fork, target, candidate_paths)
    except Exception as exc:
        errors.append(f"github: {exc.__class__.__name__}: {exc}")
    return finalize({
        "input": {"owner_fork": owner_fork, "upstream_pr_or_issue": target_value,
                  "stable_id": stable_id, "candidate_paths": list(candidate_paths),
                  "semantic_tokens": list(semantic_tokens)},
        "slack": slack, "owner": owner, "upstream": upstream,
        "blob_comparisons": comparisons, "errors": errors,
    })


def render_text(report):
    lines = [f"Decision: {report['decision']}",
             "Branch writes allowed: " + ("YES" if report["branch_write_allowed"] else "NO"),
             f"Exit code: {report['exit_code']}"]
    if report.get("errors"):
        lines += ["Evidence errors:"] + [f"  - {x}" for x in report["errors"]]
    lines.append("Slack evidence:")
    for bucket in ("stable_id_hits", "exact_target_hits", "path_semantic_hits"):
        hits = (report.get("slack") or {}).get(bucket) or []
        lines.append(f"  {bucket}: {len(hits)}")
        for hit in hits[:10]:
            parts = [hit.get("channel"), hit.get("ts"), hit.get("text")]
            lines.append("    - " + " | ".join(str(x) for x in parts if x)[:500])
    owner, upstream = report.get("owner") or {}, report.get("upstream") or {}
    lines.append("Owner snapshot: " +
                 (f"{owner.get('repo')} {owner.get('default_branch')}@{owner.get('head_sha')} "
                  f"tree={owner.get('tree_sha')}" if owner else "unavailable"))
    lines.append(f"Upstream snapshot: {upstream.get('kind')} {upstream.get('repo')}#"
                 f"{upstream.get('number')} head={upstream.get('head_sha')} "
                 f"changed={len(upstream.get('changed_files') or [])}")
    lines.append("Blob comparisons:")
    for item in report.get("blob_comparisons") or []:
        lines.append(f"  {item.get('path')}: owner={item.get('owner_blob_oid')} "
                     f"upstream={item.get('upstream_blob_oid')} status={item.get('upstream_status')} "
                     f"match={item.get('match')} comparable={item.get('comparable')}")
    if not report.get("blob_comparisons"):
        lines.append("  (none)")
    return "\n".join(lines)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner-fork")
    p.add_argument("--target")
    p.add_argument("--stable-id")
    p.add_argument("--candidate-path", action="append", default=[])
    p.add_argument("--semantic-token", action="append", default=[])
    p.add_argument("--slack-token", default="")
    p.add_argument("--slack-evidence",
                   help="JSON mapping Slack query strings to normalized read-only hits")
    p.add_argument("--offline-report", help="evaluate a collected report without network access")
    p.add_argument("--json", action="store_true", dest="json_output")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.offline_report:
        with open(args.offline_report, encoding="utf-8") as fh:
            report = finalize(json.load(fh))
    else:
        if not args.owner_fork or not args.target:
            raise SystemExit("--owner-fork and --target are required unless --offline-report is used")
        bits = args.owner_fork.strip("/").split("/")
        if len(bits) != 2 or not all(bits):
            raise SystemExit("--owner-fork must be owner/repo")
        github = GitHub(repo=args.owner_fork, token=discover_token())
        if args.slack_evidence:
            with open(args.slack_evidence, encoding="utf-8") as fh:
                evidence = json.load(fh)
            class OfflineSlack:
                def search(self, query, limit=1000):
                    return list(evidence.get(query, []))
            slack = OfflineSlack()
        else:
            token = (args.slack_token or os.environ.get("SLACK_USER_TOKEN", "")
                     or os.environ.get("SLACK_TOKEN", ""))
            slack = SlackSearch(token)
        report = collect_report(args.owner_fork, args.target, args.stable_id,
                                args.candidate_path, args.semantic_token, github, slack)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json_output else render_text(report))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
