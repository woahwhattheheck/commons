"""Fail-closed xTech|Search 10 cross-asset evidence down-selector.

This module organizes owner evidence. It does not predict sponsor scores, determine
legal eligibility, reserve a submission slot, obtain the sponsor template, or
authorize registration/submission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Iterable

PORTFOLIO_VERSION = "xtech.search10.portfolio/v1"
REPORT_VERSION = "xtech.search10.downselect.report/v1"
MAX_FILE_BYTES = 1_000_000
MAX_CANDIDATES = 16
MAX_CLAIMS_PER_CRITERION = 32
MAX_JSON_NODES = 20_000
MAX_JSON_DEPTH = 48
SAFE_INT = (1 << 53) - 1
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

CRITERIA_WEIGHTS = {
    "introduction": 5,
    "armyBenefits": 25,
    "technicalApproach": 40,
    "commercialPotential": 25,
    "proposalQuality": 5,
}
CLAIM_STATES = {"EVIDENCED", "PROPOSED", "OWNER_REQUIRED", "FORBIDDEN"}
EXTERNAL_TRACTION_KINDS = {
    "CUSTOMER_PAYMENT",
    "CUSTOMER_CONTRACT",
    "CUSTOMER_PILOT",
    "CUSTOMER_DEPLOYMENT",
    "CUSTOMER_LOI",
    "EXTERNAL_ADOPTION",
}
INTERNAL_ONLY_TRACTION_KINDS = {
    "REPO_ACTIVITY",
    "GITHUB_STARS",
    "RELEASE_DOWNLOADS",
    "INTERNAL_DEMO",
    "INTERNAL_TESTS",
    "COMMIT_COUNT",
}
PRIORITY_AREAS = {
    "ALL_ARMS_MANEUVER",
    "C2_COUNTER_C2_NETWORKS",
    "FORMATION_BASED_LAYERED_PROTECTION",
    "ADAPTIVE_SUSTAINMENT",
    "CROSS_DOMAIN_FIRES",
    "OTHER_VALID_ARMY_NEED",
}
GLOBAL_FACT_STATES = {"UNKNOWN", "CONFIRMED_TRUE", "CONFIRMED_FALSE"}
SUPPORT_STATES = {"UNKNOWN", "CLEAR", "BLOCKED"}
SLOT_STATES = {"UNKNOWN", "AVAILABLE", "CONSUMED_OR_RESERVED"}
TEMPLATE_STATES = {"UNKNOWN", "BOUND", "MISMATCH"}
OVERLAP_STATES = {"UNKNOWN", "NONE", "POTENTIALLY_SAME", "SUBSTANTIALLY_SAME"}

# Hard-coded from the current official competition announcement/RFI and kept
# separate from any candidate-controlled packet.
OFFICIAL_CONSTRAINTS = {
    "deadlineUtc": "2026-10-19T21:00:00Z",
    "oneSubmissionPerEligibleEntity": True,
    "whitePaperPages": 3,
    "mandatoryTemplate": True,
    "weights": CRITERIA_WEIGHTS,
    "priorityAreas": sorted(PRIORITY_AREAS - {"OTHER_VALID_ARMY_NEED"}),
}


class ContractError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else f"{code}:{detail}")


@dataclass(frozen=True)
class CandidateProjection:
    candidateId: str
    readinessBasisPoints: int
    criterionBasisPoints: dict[str, int]
    hardBlockers: list[str]
    externalTractionEvidenceCount: int


def _pairs_no_duplicates(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError("JSON_DUPLICATE_KEY", key)
        out[key] = value
    return out


def _reject_float(value: str) -> None:
    raise ContractError("JSON_FLOAT_FORBIDDEN", value)


def _parse_int(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > 16:
        raise ContractError("UNSAFE_INTEGER")
    number = int(value)
    if abs(number) > SAFE_INT:
        raise ContractError("UNSAFE_INTEGER")
    return number


def parse_json_strict(raw: bytes | str) -> Any:
    if isinstance(raw, bytes):
        if len(raw) > MAX_FILE_BYTES:
            raise ContractError("JSON_TOO_LARGE")
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise ContractError("JSON_NOT_UTF8") from exc
    elif isinstance(raw, str):
        try:
            encoded = raw.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise ContractError("JSON_NOT_UTF8") from exc
        if len(encoded) > MAX_FILE_BYTES:
            raise ContractError("JSON_TOO_LARGE")
        text = raw
    else:
        raise TypeError("parse_json_strict accepts bytes or str")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=_reject_float,
            parse_int=_parse_int,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ContractError("JSON_NONFINITE", value)
            ),
        )
    except ContractError:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ContractError("JSON_INVALID") from exc
    _bound_structure(value)
    return value


def _bound_structure(value: Any) -> None:
    stack: list[tuple[Any, int]] = [(value, 0)]
    nodes = 0
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise ContractError("JSON_TOO_MANY_NODES")
        if depth > MAX_JSON_DEPTH:
            raise ContractError("JSON_TOO_DEEP")
        if isinstance(node, str):
            try:
                node.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise ContractError("JSON_NOT_UTF8") from exc
        elif isinstance(node, list):
            stack.extend((item, depth + 1) for item in node)
        elif type(node) is dict:
            for key, item in node.items():
                if not isinstance(key, str):
                    raise ContractError("JSON_KEY_NOT_STRING")
                stack.append((key, depth + 1))
                stack.append((item, depth + 1))
        elif node is None or isinstance(node, (bool, int)):
            continue
        else:
            raise ContractError("JSON_TYPE_FORBIDDEN", type(node).__name__)


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("NOT_CANONICALIZABLE") from exc


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_regular_json(path: str | os.PathLike[str]) -> Any:
    supplied = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        before_lstat = supplied.lstat()
    except OSError as exc:
        raise ContractError("INPUT_STAT_FAILED", type(exc).__name__) from exc
    if stat.S_ISLNK(before_lstat.st_mode):
        raise ContractError("INPUT_SYMLINK_FORBIDDEN")
    try:
        fd = os.open(supplied, flags)
    except OSError as exc:
        raise ContractError("INPUT_OPEN_FAILED", type(exc).__name__) from exc
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise ContractError("INPUT_NOT_REGULAR")
        if opened.st_size > MAX_FILE_BYTES:
            raise ContractError("INPUT_TOO_LARGE")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                raise ContractError("INPUT_TOO_LARGE")
            chunks.append(chunk)
        after = os.fstat(fd)
        if (
            (opened.st_dev, opened.st_ino) != (after.st_dev, after.st_ino)
            or opened.st_size != after.st_size
            or getattr(opened, "st_mtime_ns", int(opened.st_mtime * 1e9))
            != getattr(after, "st_mtime_ns", int(after.st_mtime * 1e9))
        ):
            raise ContractError("INPUT_CHANGED_DURING_READ")
        return parse_json_strict(b"".join(chunks))
    finally:
        os.close(fd)


def _exact(value: Any, keys: set[str], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError("EXPECTED_OBJECT", path)
    got = set(value)
    if got != keys:
        raise ContractError(
            "OBJECT_SHAPE",
            f"{path}:missing={sorted(keys-got)},extra={sorted(got-keys)}",
        )
    return value


def _id(value: Any, path: str) -> str:
    if not isinstance(value, str) or ID_RE.fullmatch(value) is None:
        raise ContractError("INVALID_ID", path)
    return value


def _evidence_ref(value: Any, path: str) -> str:
    if not isinstance(value, str) or not (1 <= len(value) <= 512):
        raise ContractError("INVALID_EVIDENCE_REF", path)
    if any(ord(ch) < 0x20 for ch in value):
        raise ContractError("INVALID_EVIDENCE_REF", path)
    return value


def _fact(value: Any, path: str) -> tuple[str, str | None]:
    obj = _exact(value, {"state", "evidenceRef"}, path)
    state = obj["state"]
    if state not in GLOBAL_FACT_STATES:
        raise ContractError("INVALID_FACT_STATE", path)
    evidence = obj["evidenceRef"]
    if state == "UNKNOWN":
        if evidence is not None:
            raise ContractError("UNKNOWN_WITH_EVIDENCE", path)
    else:
        evidence = _evidence_ref(evidence, path + ".evidenceRef")
    return state, evidence


def _enum_fact(
    value: Any, path: str, allowed: set[str], *, ready: str
) -> tuple[str, str | None, bool]:
    obj = _exact(value, {"state", "evidenceRef"}, path)
    state = obj["state"]
    if state not in allowed:
        raise ContractError("INVALID_GATE_STATE", path)
    evidence = obj["evidenceRef"]
    if state == "UNKNOWN":
        if evidence is not None:
            raise ContractError("UNKNOWN_WITH_EVIDENCE", path)
    else:
        evidence = _evidence_ref(evidence, path + ".evidenceRef")
    return state, evidence, state == ready


def _criterion_projection(items: Any, path: str) -> tuple[int, list[str]]:
    if not isinstance(items, list) or not items or len(items) > MAX_CLAIMS_PER_CRITERION:
        raise ContractError("INVALID_CLAIM_LIST", path)
    evidenced = 0
    blockers: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(items):
        item_path = f"{path}[{index}]"
        item = _exact(raw, {"claimId", "state", "evidenceRef"}, item_path)
        claim_id = _id(item["claimId"], item_path + ".claimId")
        if claim_id in seen:
            raise ContractError("DUPLICATE_CLAIM_ID", claim_id)
        seen.add(claim_id)
        state = item["state"]
        if state not in CLAIM_STATES:
            raise ContractError("INVALID_CLAIM_STATE", item_path)
        evidence = item["evidenceRef"]
        if state == "EVIDENCED":
            _evidence_ref(evidence, item_path + ".evidenceRef")
            evidenced += 1
        else:
            if evidence is not None:
                raise ContractError("UNEVIDENCED_CLAIM_HAS_REF", item_path)
            if state in {"OWNER_REQUIRED", "FORBIDDEN"}:
                blockers.append(f"claim:{claim_id}:{state}")
    return (evidenced * 10_000) // len(items), blockers


def _candidate(raw: Any, index: int) -> CandidateProjection:
    path = f"$.candidates[{index}]"
    obj = _exact(
        raw,
        {
            "candidateId",
            "source",
            "priorityArea",
            "usamrdcExclusive",
            "federalSupportOverlap",
            "criteria",
            "traction",
        },
        path,
    )
    candidate_id = _id(obj["candidateId"], path + ".candidateId")
    source = _exact(obj["source"], {"repo", "commit", "path"}, path + ".source")
    repo = _evidence_ref(source["repo"], path + ".source.repo")
    commit = source["commit"]
    if not isinstance(commit, str) or SHA40_RE.fullmatch(commit) is None:
        raise ContractError("INVALID_SOURCE_COMMIT", candidate_id)
    _evidence_ref(source["path"], path + ".source.path")
    if repo.count("/") != 1:
        raise ContractError("INVALID_SOURCE_REPO", candidate_id)

    priority = obj["priorityArea"]
    if priority not in PRIORITY_AREAS:
        raise ContractError("INVALID_PRIORITY_AREA", candidate_id)
    if type(obj["usamrdcExclusive"]) is not bool:
        raise ContractError("INVALID_USAMRDC_FLAG", candidate_id)
    overlap = obj["federalSupportOverlap"]
    if overlap not in OVERLAP_STATES:
        raise ContractError("INVALID_SUPPORT_OVERLAP", candidate_id)

    criteria = _exact(obj["criteria"], set(CRITERIA_WEIGHTS), path + ".criteria")
    criterion_bp: dict[str, int] = {}
    blockers: list[str] = []
    total_bp = 0
    for criterion, weight in CRITERIA_WEIGHTS.items():
        coverage_bp, claim_blockers = _criterion_projection(
            criteria[criterion], f"{path}.criteria.{criterion}"
        )
        weighted_bp = (coverage_bp * weight) // 100
        criterion_bp[criterion] = weighted_bp
        total_bp += weighted_bp
        blockers.extend(claim_blockers)

    traction = obj["traction"]
    if not isinstance(traction, list) or len(traction) > 32:
        raise ContractError("INVALID_TRACTION_LIST", candidate_id)
    external_count = 0
    traction_ids: set[str] = set()
    for tindex, raw_traction in enumerate(traction):
        tpath = f"{path}.traction[{tindex}]"
        row = _exact(raw_traction, {"evidenceId", "kind", "evidenceRef"}, tpath)
        evidence_id = _id(row["evidenceId"], tpath + ".evidenceId")
        if evidence_id in traction_ids:
            raise ContractError("DUPLICATE_TRACTION_ID", evidence_id)
        traction_ids.add(evidence_id)
        kind = row["kind"]
        if kind in INTERNAL_ONLY_TRACTION_KINDS:
            blockers.append(f"fake_traction:{evidence_id}:{kind}")
            continue
        if kind not in EXTERNAL_TRACTION_KINDS:
            raise ContractError("UNKNOWN_TRACTION_KIND", str(kind))
        _evidence_ref(row["evidenceRef"], tpath + ".evidenceRef")
        external_count += 1

    if external_count == 0:
        blockers.append("commercial_traction:missing_external_evidence")
    if overlap != "NONE":
        blockers.append(f"federal_support_overlap:{overlap}")
    if obj["usamrdcExclusive"]:
        blockers.append("scope:USAMRDC_EXCLUSIVE")
    return CandidateProjection(
        candidateId=candidate_id,
        readinessBasisPoints=total_bp,
        criterionBasisPoints=criterion_bp,
        hardBlockers=sorted(set(blockers)),
        externalTractionEvidenceCount=external_count,
    )


def compile_portfolio(packet: Any) -> dict[str, Any]:
    root = _exact(
        packet,
        {
            "version",
            "entityId",
            "globalGates",
            "candidates",
        },
        "$",
    )
    if root["version"] != PORTFOLIO_VERSION:
        raise ContractError("UNSUPPORTED_VERSION")
    entity_id = _id(root["entityId"], "$.entityId")
    gates = _exact(
        root["globalGates"],
        {
            "forProfitIndependentUsSmallBusiness",
            "ownershipControlEligible",
            "employeeCeilingMet",
            "sbirSmallBusinessRequirementsMet",
            "federalSupportCensus",
            "oneSubmissionSlot",
            "officialTemplate",
        },
        "$.globalGates",
    )

    global_blockers: list[str] = []
    for name in (
        "forProfitIndependentUsSmallBusiness",
        "ownershipControlEligible",
        "employeeCeilingMet",
        "sbirSmallBusinessRequirementsMet",
    ):
        state, _ = _fact(gates[name], f"$.globalGates.{name}")
        if state != "CONFIRMED_TRUE":
            global_blockers.append(f"global:{name}:{state}")

    support_state, _, support_ready = _enum_fact(
        gates["federalSupportCensus"],
        "$.globalGates.federalSupportCensus",
        SUPPORT_STATES,
        ready="CLEAR",
    )
    if not support_ready:
        global_blockers.append(f"global:federalSupportCensus:{support_state}")

    slot_state, _, slot_ready = _enum_fact(
        gates["oneSubmissionSlot"],
        "$.globalGates.oneSubmissionSlot",
        SLOT_STATES,
        ready="AVAILABLE",
    )
    if not slot_ready:
        global_blockers.append(f"global:oneSubmissionSlot:{slot_state}")

    template_state, _, template_ready = _enum_fact(
        gates["officialTemplate"],
        "$.globalGates.officialTemplate",
        TEMPLATE_STATES,
        ready="BOUND",
    )
    if not template_ready:
        global_blockers.append(f"global:officialTemplate:{template_state}")

    candidates_raw = root["candidates"]
    if (
        not isinstance(candidates_raw, list)
        or len(candidates_raw) < 2
        or len(candidates_raw) > MAX_CANDIDATES
    ):
        raise ContractError("CANDIDATE_COUNT")

    projections = [_candidate(row, i) for i, row in enumerate(candidates_raw)]
    ids = [row.candidateId for row in projections]
    if len(ids) != len(set(ids)):
        raise ContractError("DUPLICATE_CANDIDATE_ID")

    viable = [row for row in projections if not row.hardBlockers]
    selected: str | None = None
    state = "HOLD"
    hold_reason = "GLOBAL_GATES"
    if global_blockers:
        pass
    elif not viable:
        hold_reason = "NO_CANDIDATE_PASSES_HARD_GATES"
    else:
        best = max(row.readinessBasisPoints for row in viable)
        leaders = [row for row in viable if row.readinessBasisPoints == best]
        if len(leaders) != 1:
            hold_reason = "TOP_READINESS_TIE"
        else:
            selected = leaders[0].candidateId
            state = "SELECTED"
            hold_reason = ""

    report = {
        "version": REPORT_VERSION,
        "entityId": entity_id,
        "state": state,
        "selectedCandidateId": selected,
        "holdReason": hold_reason or None,
        "globalBlockers": sorted(global_blockers),
        "projections": [asdict(row) for row in sorted(projections, key=lambda row: row.candidateId)],
        "officialConstraintSnapshot": OFFICIAL_CONSTRAINTS,
        "readinessMetricMeaning": (
            "internal evidence-coverage basis points using published criterion weights; "
            "not an Army score, ranking, selection prediction, or outcome probability"
        ),
        "authority": {
            "armyEligibilityDetermined": False,
            "officialTemplateObtainedByCompiler": False,
            "registrationAuthorized": False,
            "submissionAuthorized": False,
            "entitySlotConsumed": False,
            "awardOrPrizeClaimed": False,
        },
    }
    report["receiptSha256"] = sha256_json(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="xTech Search 10 evidence-only portfolio down-selector")
    parser.add_argument("packet")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = compile_portfolio(read_regular_json(args.packet))
    except ContractError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "detail": exc.detail}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
