
def _completion_merge_is_ancestor(merge_sha):
    """Fail-closed proof that a retained merge commit is in checked-out HEAD."""
    try:
        landed = _git(
            ["merge-base", "--is-ancestor", str(merge_sha or ""), "HEAD"],
            git_env(),
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    return landed.returncode == 0


def _completion_canonical_issue(number):
    """Read the exact issue identity; stale event bodies never control state."""
    if type(number) is not int or number < 1:
        return None
    api_url = "https://api.github.com/repos/woahwhattheheck/commons/issues/%s" % number
    try:
        issue = _gh_api(api_url)
    except (OSError, ValueError):
        return None
    if not isinstance(issue, dict) or type(issue.get("number")) is not int:
        return None
    if issue["number"] != number or issue.get("state") not in ("open", "closed"):
        return None
    expected_urls = {api_url, "https://github.com/woahwhattheheck/commons/issues/%s" % number}
    urls = [issue.get(key) for key in ("url", "html_url") if issue.get(key) is not None]
    if not urls or any(type(url) is not str or url not in expected_urls for url in urls):
        return None
    return issue


def _completion_issue_timeline(number):
    """Return rows and explicit completeness; at most ten 100-event pages.

    The provider's page-number road is exhausted only by a short page. A full
    tenth page, failed later read, or malformed page is not a complete timeline.
    Keep the first-page URL compatible with the existing provider fixture.
    """
    url = "https://api.github.com/repos/woahwhattheheck/commons/issues/%s/timeline?per_page=100" % number
    events = []
    for page in range(1, 11):
        try:
            rows = _gh_api(url if page == 1 else url + "&page=%s" % page)
        except (OSError, ValueError):
            rows = None
        if not isinstance(rows, list) or len(rows) > 100:
            return {"events": events, "complete": False, "pages": page,
                    "reason": "timeline_read_unavailable_or_malformed"}
        events.extend(rows)
        if len(rows) < 100:
            return {"events": events, "complete": True, "pages": page, "reason": ""}
    return {"events": events, "complete": False, "pages": 10,
            "reason": "timeline_page_budget_exhausted"}


def _completion_marker_for_closed_issue(issue):
    """Return strongest same-repo main-merge evidence, or None when unproven."""
    if not isinstance(issue, dict):
        return None
    number = issue.get("number")
    issue = _completion_canonical_issue(number)
    if issue is None:
        return None
    if issue.get("state") != "closed" or issue.get("state_reason") != "completed":
        return None
    operation_id = completion_projection.stable_operation_id_from_issue(issue)
    if not operation_id:
        return None
    timeline = _completion_issue_timeline(number)
    if timeline["complete"] is not True:
        print("COMPLETION_HOLD issue=%s reason=%s pages=%s events=%s" % (
            number, timeline["reason"], timeline["pages"], len(timeline["events"])
        ), flush=True)
        return None
    candidates, seen_prs = [], set()
    for event in timeline["events"]:
        if not isinstance(event, dict) or event.get("event") != "cross-referenced":
            continue
        source = event.get("source")
        if not isinstance(source, dict):
            continue
        source_issue = source.get("issue")
        if not isinstance(source_issue, dict) or not source_issue.get("pull_request"):
            continue
        if source_issue.get("repository_url") != (
            "https://api.github.com/repos/woahwhattheheck/commons"
        ):
            continue
        pr_number = source_issue.get("number")
        if type(pr_number) is not int or pr_number < 1 or pr_number in seen_prs:
            continue
        seen_prs.add(pr_number)
        try:
            pr = _gh_api(
                "https://api.github.com/repos/woahwhattheheck/commons/pulls/%s" % pr_number
            )
        except (OSError, ValueError):
            continue
        if not isinstance(pr, dict) or type(pr.get("number")) is not int or pr["number"] != pr_number:
            continue
        try:
            marker = completion_projection.build_marker(ROOT, operation_id, issue, pr)
        except completion_projection.CompletionEvidenceError:
            continue
        merge_sha = marker["merge"]["merge_commit_sha"]
        if _completion_merge_is_ancestor(merge_sha) is not True:
            continue
        candidates.append(marker)
    if not candidates:
        return None
    candidates.sort(key=lambda row: (
        completion_projection.parse_timestamp(row["merge"]["merged_at"]),
        row["merge"]["pr_number"],
    ))
    return candidates[-1]

def _handle_completion_issue_event(ev):
    """Project close/reopen state without re-ingesting the issue as a post."""
    action = str(ev.get("action") or "")
    issue = ev.get("issue") or {}
    number = issue.get("number") if isinstance(issue, dict) else None
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        print("COMPLETION_HOLD reason=missing_issue_number", flush=True)
        return 0
    if action == "reopened":
        canonical = _completion_canonical_issue(number)
        if canonical is None or canonical.get("state") != "open" or canonical.get("closed_at") is not None:
            print("COMPLETION_HOLD issue=%s reason=reopen_not_currently_open" % number, flush=True)
            return 0
        removed = completion_projection.remove_markers_for_issue(ROOT, number)
        print(
            "COMPLETION_REOPEN issue=%s removed=%s ids=%s"
            % (number, len(removed), ",".join(removed)),
            flush=True,
        )
        return 0
    if action != "closed":
        return 0
    marker = _completion_marker_for_closed_issue(issue)
    if marker is None:
        print(
            "COMPLETION_HOLD issue=%s reason=no_verified_main_merge_or_identity"
            % number,
            flush=True,
        )
        return 0
    operation_id = marker["operation_id"]
    try:
        state = completion_projection.write_marker(
            ROOT, marker, _completion_merge_is_ancestor
        )
    except completion_projection.CompletionEvidenceError as exc:
        print(
            "COMPLETION_HOLD id=%s issue=%s reason=%s"
            % (operation_id, number, str(exc)),
            flush=True,
        )
        return 0
    print(
        "COMPLETION_%s id=%s issue=%s pr=%s merge=%s"
        % (
            state.upper(),
            operation_id,
            number,
            marker["merge"]["pr_number"],
            marker["merge"]["merge_commit_sha"],
        ),
        flush=True,
    )
    return 0


def ingest_github_event():
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path or not os.path.isfile(path):
        return 0
    try:
        ev = json.loads(_read(path))
    except json.JSONDecodeError:
        return 0
    action = str(ev.get("action") or "opened")
    if action in ("closed", "reopened"):
        return _handle_completion_issue_event(ev)
    if action != "opened":
        return 0
    issue = ev.get("issue") or {}
    src, dest, mid, text, extra = _issue_post_fields(issue)
    # Suppress a no-information duplicate on both webhook and sweep roads. The
    # run log is the trace, and ISSUE_TOUCHED stays empty so record_landed does
    # not report the duplicate as a new landing.
    if _is_echo_of_landed_post(issue.get("body") or "", mid):
        print(
            "ECHO_SKIP id=%s issue=%s — no envelope, id already landed; not a post"
            % (mid, issue.get("number")),
            flush=True,
        )
        return 0
    # order 036: the ordinary issue road also stamps carrier_ts from the issue's
    # own created_at, not ingest wall-clock — same clock policy as the sweep
    created = str(issue.get("created_at") or "")
    source_ts = str(extra.pop("ts", "") or created)
    if created:
        extra = dict(extra)
        extra["carrier_ts"] = extra.get("carrier_ts") or created
