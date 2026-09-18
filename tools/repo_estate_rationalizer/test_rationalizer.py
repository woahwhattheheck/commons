from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.repo_estate_rationalizer import rationalizer as rr

NOW = datetime(2026, 9, 18, 7, 35, 0, tzinfo=UTC)
SHA = "a" * 40
SHA2 = "b" * 40


def snapshot(*repos):
    if not repos:
        repos = (
            {"name": "public-one", "visibility": "public", "archived": False, "default_branch": "main", "default_branch_sha": None},
            {"name": "private-one", "visibility": "private", "archived": False, "default_branch": "main", "default_branch_sha": SHA},
        )
    return {
        "schema": rr.SNAPSHOT_SCHEMA,
        "owner": "woahwhattheheck",
        "captured_at": "2026-09-18T07:34:00Z",
        "repositories": list(repos),
    }


def evidence(rows=None):
    return {"schema": rr.EVIDENCE_SCHEMA, "repositories": list(rows or [])}


def ev(name="private-one", *, intent="review_public", sha=SHA, owner=True, secret="CLEAR", content="PUBLIC_RELEASE_OK", legal="CLEAR_FOR_PUBLIC_RELEASE", open_prs=0, open_issues=0, active_claims=0, consumers=0, replacement=None, replacement_verified=False, archive=False, observed="2026-09-18T07:34:00Z"):
    return {
        "repository": name,
        "default_branch_sha": sha,
        "intent": intent,
        "owner_authorized": owner,
        "owner_authority_ref": "issue:16003#owner",
        "secret_scan": {"result": secret, "commit_sha": sha, "observed_at": observed, "ref": "scan:abc"},
        "content_classification": content,
        "content_classification_ref": "review:content",
        "legal_ip_review": legal,
        "legal_ip_ref": "review:ip",
        "open_work": {"open_prs": open_prs, "open_issues": open_issues, "active_claims": active_claims, "observed_at": observed, "ref": "github:work"},
        "dependencies": {"consumer_count": consumers, "replacement_repository": replacement, "replacement_verified": replacement_verified, "observed_at": observed, "ref": "deps:graph"},
        "archive_authorized": archive,
        "archive_authority_ref": "issue:16003#archive",
    }


def compile_at(snap=None, evid=None, now=NOW):
    return rr._compile_at(snap or snapshot(), evid or evidence(), now=now)


def by_repo(packet, name):
    return next(x for x in packet["decisions"] if x["repository"] == name)


def test_live_shape_without_private_evidence_holds_and_public_is_idempotent():
    packet = compile_at()
    assert packet["estate"]["repository_count"] == 2
    assert packet["estate"]["private_repository_count"] == 1
    assert by_repo(packet, "public-one")["state"] == "PUBLIC_ALREADY"
    assert by_repo(packet, "private-one")["state"] == "HOLD"
    assert "MISSING_PUBLICATION_RETENTION_EVIDENCE" in by_repo(packet, "private-one")["reasons"]


def test_publication_review_requires_complete_current_evidence():
    packet = compile_at(evid=evidence([ev()]))
    row = by_repo(packet, "private-one")
    assert row["state"] == "PUBLICATION_REVIEW"
    assert row["reasons"] == ["EXPLICIT_PUBLICATION_REVIEW_EVIDENCE_COMPLETE"]
    assert packet["authority"]["repository_visibility_mutation_authorized"] is False
    assert packet["authority"]["publication_safety_certified"] is False


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"owner": False}, "OWNER_AUTHORITY_NOT_PROVEN"),
        ({"secret": "FINDINGS"}, "SECRET_SCAN_NOT_CURRENT_CLEAR"),
        ({"content": "PRIVATE_OR_UNKNOWN"}, "CONTENT_NOT_CLEARED_FOR_PUBLIC_RELEASE"),
        ({"legal": "UNKNOWN"}, "LEGAL_IP_NOT_CLEARED_FOR_PUBLIC_RELEASE"),
        ({"sha": SHA2}, "BRANCH_GENERATION_DRIFT"),
        ({"observed": "2026-09-01T00:00:00Z"}, "SECRET_SCAN_NOT_CURRENT_CLEAR"),
    ],
)
def test_publication_review_fail_closed_classes(kwargs, reason):
    packet = compile_at(evid=evidence([ev(**kwargs)]))
    row = by_repo(packet, "private-one")
    assert row["state"] == "HOLD"
    assert reason in row["reasons"]


def test_keep_private_never_requires_public_release_classification():
    row = ev(intent="keep_private", secret="FINDINGS", content="PRIVATE", legal="PRIVATE", owner=True)
    packet = compile_at(evid=evidence([row]))
    assert by_repo(packet, "private-one")["state"] == "KEEP_PRIVATE"
    assert by_repo(packet, "private-one")["reasons"] == ["OWNER_KEEP_PRIVATE"]


def test_keep_private_without_owner_authority_holds():
    packet = compile_at(evid=evidence([ev(intent="keep_private", owner=False)]))
    row = by_repo(packet, "private-one")
    assert row["state"] == "HOLD"
    assert row["reasons"] == ["OWNER_AUTHORITY_NOT_PROVEN"]


def test_archive_review_requires_explicit_authority_and_no_work_or_consumers():
    good = ev(intent="review_archive", archive=True, replacement="public-one", replacement_verified=True)
    assert by_repo(compile_at(evid=evidence([good])), "private-one")["state"] == "ARCHIVE_REVIEW"

    bad = ev(intent="review_archive", archive=False, open_prs=1, consumers=2, replacement="public-one", replacement_verified=False)
    row = by_repo(compile_at(evid=evidence([bad])), "private-one")
    assert row["state"] == "HOLD"
    assert set(row["reasons"]) >= {"ARCHIVE_AUTHORITY_NOT_PROVEN", "OPEN_WORK_BLOCKS_ARCHIVE", "ACTIVE_CONSUMERS_BLOCK_ARCHIVE", "REPLACEMENT_RELATION_UNVERIFIED"}


def test_archive_open_issue_and_active_claim_each_block():
    for kw in ({"open_issues": 1}, {"active_claims": 1}):
        row = ev(intent="review_archive", archive=True, **kw)
        assert "OPEN_WORK_BLOCKS_ARCHIVE" in by_repo(compile_at(evid=evidence([row])), "private-one")["reasons"]


def test_missing_private_branch_sha_cannot_positive_recommend():
    s = snapshot({"name": "private-one", "visibility": "private", "archived": False, "default_branch": "main", "default_branch_sha": None})
    packet = rr._compile_at(s, evidence([ev()]), now=NOW)
    row = by_repo(packet, "private-one")
    assert row["state"] == "HOLD"
    assert "MISSING_CURRENT_BRANCH_SHA" in row["reasons"]


def test_case_alias_repo_identity_is_rejected_in_snapshot_and_evidence():
    s = snapshot(
        {"name": "Repo", "visibility": "private", "archived": False, "default_branch": "main", "default_branch_sha": SHA},
        {"name": "repo", "visibility": "private", "archived": False, "default_branch": "main", "default_branch_sha": SHA2},
    )
    with pytest.raises(rr.EstateError, match="case-aliased"):
        rr.validate_snapshot(s)

    e = evidence([ev("private-one"), ev("PRIVATE-ONE")])
    with pytest.raises(rr.EstateError, match="case-aliased"):
        rr._compile_at(snapshot(), e, now=NOW)


def test_unknown_evidence_repo_is_rejected():
    with pytest.raises(rr.EstateError, match="absent from snapshot"):
        compile_at(evid=evidence([ev("missing-repo")]))


def test_bool_int_aliases_reject():
    row = ev()
    row["open_work"]["open_prs"] = True
    with pytest.raises(rr.EstateError):
        compile_at(evid=evidence([row]))
    s = snapshot()
    s["repositories"][1]["archived"] = 1
    with pytest.raises(rr.EstateError):
        rr.validate_snapshot(s)


def test_duplicate_json_and_nonfinite_reject():
    with pytest.raises(rr.EstateError, match="duplicate JSON key"):
        rr.loads_strict('{"schema":"x","schema":"y"}')
    with pytest.raises(rr.EstateError, match="non-finite"):
        rr.loads_strict('{"x": NaN}')


def test_input_order_independent_and_receipt_stable():
    rows = [
        {"name": "private-one", "visibility": "private", "archived": False, "default_branch": "main", "default_branch_sha": SHA},
        {"name": "public-one", "visibility": "public", "archived": False, "default_branch": "main", "default_branch_sha": SHA2},
    ]
    a = rr._compile_at(snapshot(*rows), evidence([ev()]), now=NOW)
    b = rr._compile_at(snapshot(*reversed(rows)), evidence([ev()]), now=NOW)
    assert a == b


def test_packet_receipt_tamper_detected(monkeypatch):
    packet = compile_at(evid=evidence([ev()]))
    packet["estate"]["private_repository_count"] = 999
    monkeypatch.setattr(rr, "datetime", type("Clock", (datetime,), {"now": classmethod(lambda cls, tz=None: NOW if tz is None else NOW.astimezone(tz))}))
    assert rr.verify_packet(packet, snapshot(), evidence([ev()])) is False


def test_verify_recompiles_exact_sources(monkeypatch):
    packet = compile_at(evid=evidence([ev()]))
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is None else NOW.astimezone(tz)
    monkeypatch.setattr(rr, "datetime", Clock)
    assert rr.verify_packet(packet, snapshot(), evidence([ev()])) is True
    drift = snapshot()
    drift["repositories"][1]["default_branch_sha"] = SHA2
    assert rr.verify_packet(packet, drift, evidence([ev()])) is False


def test_snapshot_stale_or_future_rejected():
    stale = snapshot(); stale["captured_at"] = "2026-09-01T00:00:00Z"
    with pytest.raises(rr.EstateError, match="stale"):
        rr._compile_at(stale, evidence(), now=NOW)
    future = snapshot(); future["captured_at"] = "2026-09-19T00:00:00Z"
    with pytest.raises(rr.EstateError, match="future"):
        rr._compile_at(future, evidence(), now=NOW)


def test_render_is_advisory_and_contains_no_mutation_authority():
    text = rr.render_markdown(compile_at())
    assert "advisory decision support only" in text
    assert "does not authorize repository visibility" in text
    assert "private-one" in text


def test_create_exclusive_and_symlink_refusal(tmp_path):
    out = tmp_path / "out.json"
    rr._write_exclusive(out, "x")
    with pytest.raises(rr.EstateError):
        rr._write_exclusive(out, "y")
    target = tmp_path / "target"; target.write_text("x")
    link = tmp_path / "link"; link.symlink_to(target)
    with pytest.raises(rr.EstateError):
        rr._read_regular(link)


def test_archive_replacement_can_be_none_when_no_consumers():
    row = ev(intent="review_archive", archive=True, replacement=None, replacement_verified=False)
    packet = compile_at(evid=evidence([row]))
    assert by_repo(packet, "private-one")["state"] == "ARCHIVE_REVIEW"


def test_visibility_state_drift_recompile_changes_decision(monkeypatch):
    packet = compile_at(evid=evidence([ev()]))
    drift = snapshot()
    drift["repositories"][1]["visibility"] = "public"
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is None else NOW.astimezone(tz)
    monkeypatch.setattr(rr, "datetime", Clock)
    assert rr.verify_packet(packet, drift, evidence([ev()])) is False
    rebuilt = rr._compile_at(drift, evidence([ev()]), now=NOW)
    assert by_repo(rebuilt, "private-one")["state"] == "PUBLIC_ALREADY"


def test_fixture_counts_match_declared_live_estate():
    fixture = Path(__file__).with_name("fixtures") / "account_snapshot_20260918.json"
    snap = rr.validate_snapshot(json.loads(fixture.read_text()))
    assert len(snap["repositories"]) == 43
    assert sum(x["visibility"] == "private" for x in snap["repositories"]) == 15
    private = {x["name"] for x in snap["repositories"] if x["visibility"] == "private"}
    assert {"LocalDeviceAgent", "aquatrace-lims", "deathstar", "whitebox-estimation", "muhlnickel"} <= private


def _optimized_smoke():
    packet = compile_at()
    if packet["estate"]["repository_count"] != 2:
        raise RuntimeError("optimized smoke: repository count")
    if by_repo(packet, "public-one")["state"] != "PUBLIC_ALREADY":
        raise RuntimeError("optimized smoke: public idempotence")
    if by_repo(packet, "private-one")["state"] != "HOLD":
        raise RuntimeError("optimized smoke: private no-evidence hold")

    published = compile_at(evid=evidence([ev()]))
    if by_repo(published, "private-one")["state"] != "PUBLICATION_REVIEW":
        raise RuntimeError("optimized smoke: positive evidence review")
    if published["authority"]["repository_visibility_mutation_authorized"] is not False:
        raise RuntimeError("optimized smoke: authority ceiling")

    unsafe = compile_at(evid=evidence([ev(secret="FINDINGS")]))
    if by_repo(unsafe, "private-one")["state"] != "HOLD":
        raise RuntimeError("optimized smoke: secret finding must hold")

    try:
        rr.validate_snapshot(snapshot(
            {"name": "Repo", "visibility": "private", "archived": False, "default_branch": "main", "default_branch_sha": SHA},
            {"name": "repo", "visibility": "private", "archived": False, "default_branch": "main", "default_branch_sha": SHA2},
        ))
    except rr.EstateError:
        pass
    else:
        raise RuntimeError("optimized smoke: case alias accepted")

    fixture = Path(__file__).with_name("fixtures") / "account_snapshot_20260918.json"
    snap = rr.validate_snapshot(json.loads(fixture.read_text()))
    if len(snap["repositories"]) != 43:
        raise RuntimeError("optimized smoke: live fixture count")
    if sum(x["visibility"] == "private" for x in snap["repositories"]) != 15:
        raise RuntimeError("optimized smoke: live private count")
    print("OPTIMIZED_REPO_ESTATE_SMOKE_PASS")


if __name__ == "__main__":
    _optimized_smoke()
