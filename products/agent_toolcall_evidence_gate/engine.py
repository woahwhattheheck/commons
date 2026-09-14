"""Deterministic preflight gate for side-effecting agent tool calls.

The gate never performs a tool call. It validates one request against a closed
policy and an append-only allow ledger, returning EXECUTE_ALLOWED or HOLD plus
an evidence-bound receipt. Only EXECUTE_ALLOWED appends to the ledger.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable

SCHEMA_VERSION = 1
DECISION_ALLOW = "EXECUTE_ALLOWED"
DECISION_HOLD = "HOLD"
AUTHORITY = "TOOLCALL_PREFLIGHT_ONLY_NO_PROVIDER_MUTATION_AUTHORITY"

REASON_AGENT_VERSION = "AGENT_VERSION_NOT_ALLOWED"
REASON_TOOL_ACTION = "TOOL_ACTION_NOT_ALLOWED"
REASON_ROLE_RESOURCE = "ROLE_RESOURCE_MISMATCH"
REASON_RESTRICTED_DATA = "RESTRICTED_DATA_EXPOSURE"
REASON_APPROVAL = "HUMAN_APPROVAL_REQUIRED"
REASON_BUDGET_RATE = "BUDGET_OR_RATE_LIMIT"
REASON_REPLAY = "IDEMPOTENCY_REPLAY"
REASON_TRACE = "TRACE_INCOMPLETE"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,190}$")
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
DATA_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class GateError(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(raw: bytes | str) -> dict[str, Any]:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise GateError("input must be strict UTF-8") from exc
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_pairs,
            parse_float=lambda token: (_ for _ in ()).throw(GateError("floats forbidden")),
            parse_constant=lambda token: (_ for _ in ()).throw(GateError("non-finite numbers forbidden")),
        )
    except GateError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise GateError(f"invalid JSON: {exc}") from exc
    if type(value) is not dict:
        raise GateError("top-level input must be object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def sha256(value: Any) -> str:
    data = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(data).hexdigest()


def _exact(obj: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise GateError(f"{where} must be object")
    actual = set(obj)
    if actual != keys:
        raise GateError(f"{where} keys mismatch missing={sorted(keys-actual)} extra={sorted(actual-keys)}")
    return obj


def _id(value: Any, where: str) -> str:
    if type(value) is not str or ID_RE.fullmatch(value) is None:
        raise GateError(f"{where} must be bounded ASCII identifier")
    return value


def _version(value: Any, where: str) -> str:
    if type(value) is not str or VERSION_RE.fullmatch(value) is None:
        raise GateError(f"{where} must be bounded version token")
    return value


def _sha(value: Any, where: str) -> str:
    if type(value) is not str or SHA_RE.fullmatch(value) is None:
        raise GateError(f"{where} must be lowercase sha256")
    return value


def _int(value: Any, where: str, low: int, high: int) -> int:
    if isinstance(value, bool) or type(value) is not int or not low <= value <= high:
        raise GateError(f"{where} must be integer in [{low},{high}]")
    return value


def _string_list(value: Any, where: str, *, pattern: re.Pattern[str] = ID_RE) -> tuple[str, ...]:
    if type(value) is not list or not value:
        raise GateError(f"{where} must be non-empty list")
    if any(type(x) is not str or pattern.fullmatch(x) is None for x in value):
        raise GateError(f"{where} contains invalid token")
    if len(set(value)) != len(value):
        raise GateError(f"{where} contains duplicates")
    return tuple(value)


@dataclass(frozen=True)
class Rule:
    tool: str
    action: str
    resource_prefix: str
    allowed_roles: tuple[str, ...]
    allowed_data_classes: tuple[str, ...]
    require_human_approval: bool
    approval_roles: tuple[str, ...]
    max_request_budget_cents: int
    max_window_budget_cents: int
    max_calls_per_window: int

    @property
    def key(self) -> str:
        return f"{self.tool}:{self.action}"


@dataclass(frozen=True)
class Policy:
    policy_id: str
    revision: int
    agents: dict[str, tuple[str, ...]]
    restricted_data_classes: tuple[str, ...]
    rules: dict[str, Rule]
    digest: str

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> "Policy":
        raw = deepcopy(raw)
        _exact(raw, {"schema_version", "policy_id", "revision", "agents", "restricted_data_classes", "rules"}, "policy")
        if raw["schema_version"] != SCHEMA_VERSION:
            raise GateError("policy.schema_version must be 1")
        policy_id = _id(raw["policy_id"], "policy.policy_id")
        revision = _int(raw["revision"], "policy.revision", 1, 2_147_483_647)
        if type(raw["agents"]) is not list or not raw["agents"]:
            raise GateError("policy.agents must be non-empty list")
        agents: dict[str, tuple[str, ...]] = {}
        for i, item in enumerate(raw["agents"]):
            item = _exact(item, {"agent_id", "versions"}, f"policy.agents[{i}]")
            agent_id = _id(item["agent_id"], f"policy.agents[{i}].agent_id")
            if agent_id in agents:
                raise GateError("duplicate agent_id")
            agents[agent_id] = _string_list(item["versions"], f"policy.agents[{i}].versions", pattern=VERSION_RE)
        restricted = _string_list(raw["restricted_data_classes"], "policy.restricted_data_classes", pattern=DATA_RE)
        if type(raw["rules"]) is not list or not raw["rules"]:
            raise GateError("policy.rules must be non-empty list")
        rules: dict[str, Rule] = {}
        for i, item in enumerate(raw["rules"]):
            item = _exact(
                item,
                {"tool", "action", "resource_prefix", "allowed_roles", "allowed_data_classes", "require_human_approval", "approval_roles", "max_request_budget_cents", "max_window_budget_cents", "max_calls_per_window"},
                f"policy.rules[{i}]",
            )
            tool = _id(item["tool"], f"policy.rules[{i}].tool")
            action = _id(item["action"], f"policy.rules[{i}].action")
            prefix = _id(item["resource_prefix"], f"policy.rules[{i}].resource_prefix")
            roles = _string_list(item["allowed_roles"], f"policy.rules[{i}].allowed_roles")
            classes = _string_list(item["allowed_data_classes"], f"policy.rules[{i}].allowed_data_classes", pattern=DATA_RE)
            require_approval = item["require_human_approval"]
            if type(require_approval) is not bool:
                raise GateError("require_human_approval must be boolean")
            approval_roles = _string_list(item["approval_roles"], f"policy.rules[{i}].approval_roles")
            if not require_approval and approval_roles != ("none",):
                raise GateError("non-approval rule must use exact approval_roles=['none']")
            rule = Rule(
                tool=tool,
                action=action,
                resource_prefix=prefix,
                allowed_roles=roles,
                allowed_data_classes=classes,
                require_human_approval=require_approval,
                approval_roles=approval_roles,
                max_request_budget_cents=_int(item["max_request_budget_cents"], f"policy.rules[{i}].max_request_budget_cents", 0, 10**15),
                max_window_budget_cents=_int(item["max_window_budget_cents"], f"policy.rules[{i}].max_window_budget_cents", 0, 10**15),
                max_calls_per_window=_int(item["max_calls_per_window"], f"policy.rules[{i}].max_calls_per_window", 1, 10**9),
            )
            if rule.key in rules:
                raise GateError("duplicate tool/action rule")
            rules[rule.key] = rule
        return cls(policy_id, revision, agents, restricted, rules, sha256(raw))


def empty_ledger(policy: Policy) -> dict[str, Any]:
    ledger = {"schema_version": 1, "policy_id": policy.policy_id, "policy_revision": policy.revision, "entries": []}
    ledger["ledger_sha256"] = sha256(ledger)
    return ledger


def _parse_ledger(raw: dict[str, Any], policy: Policy) -> tuple[list[dict[str, Any]], str]:
    raw = deepcopy(raw)
    _exact(raw, {"schema_version", "policy_id", "policy_revision", "entries", "ledger_sha256"}, "ledger")
    if raw["schema_version"] != 1 or raw["policy_id"] != policy.policy_id or raw["policy_revision"] != policy.revision:
        raise GateError("LEDGER_POLICY_MISMATCH")
    ledger_digest = _sha(raw["ledger_sha256"], "ledger.ledger_sha256")
    core = {k: raw[k] for k in ("schema_version", "policy_id", "policy_revision", "entries")}
    if sha256(core) != ledger_digest:
        raise GateError("LEDGER_DIGEST_MISMATCH")
    if type(raw["entries"]) is not list:
        raise GateError("ledger.entries must be list")
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for i, entry in enumerate(raw["entries"]):
        entry = _exact(entry, {"sequence", "request_id", "request_sha256", "idempotency_sha256", "rule_key", "window_id", "budget_cents", "receipt_sha256"}, f"ledger.entries[{i}]")
        if entry["sequence"] != i + 1:
            raise GateError("ledger sequence gap")
        request_id = _id(entry["request_id"], f"ledger.entries[{i}].request_id")
        if request_id in seen_ids:
            raise GateError("duplicate request_id in ledger")
        seen_ids.add(request_id)
        _sha(entry["request_sha256"], f"ledger.entries[{i}].request_sha256")
        _sha(entry["idempotency_sha256"], f"ledger.entries[{i}].idempotency_sha256")
        _id(entry["rule_key"], f"ledger.entries[{i}].rule_key")
        _id(entry["window_id"], f"ledger.entries[{i}].window_id")
        _int(entry["budget_cents"], f"ledger.entries[{i}].budget_cents", 0, 10**15)
        _sha(entry["receipt_sha256"], f"ledger.entries[{i}].receipt_sha256")
        entries.append(entry)
    return entries, ledger_digest


def approval_intent_sha256(request: dict[str, Any]) -> str:
    """Digest the exact side-effect intent a human approval must authorize.

    Approval evidence itself is excluded to avoid a circular digest. The binding
    includes request identity, agent/version, actor/role, tool/action/resource/data
    class, idempotency, budget, trusted window identity and trace evidence.
    """
    intent = {
        "schema_version": request["schema_version"],
        "request_id": request["request_id"],
        "agent": request["agent"],
        "actor": request["actor"],
        "tool_call": request["tool_call"],
        "idempotency_key": request["idempotency_key"],
        "budget_cents": request["budget_cents"],
        "window_id": request["window_id"],
        "trace": request["trace"],
    }
    return sha256(intent)


def _parse_request(raw: dict[str, Any]) -> dict[str, Any]:
    raw = deepcopy(raw)
    _exact(raw, {"schema_version", "request_id", "agent", "actor", "tool_call", "approval", "idempotency_key", "budget_cents", "window_id", "trace"}, "request")
    if raw["schema_version"] != 1:
        raise GateError("request.schema_version must be 1")
    _id(raw["request_id"], "request.request_id")
    agent = _exact(raw["agent"], {"agent_id", "version"}, "request.agent")
    _id(agent["agent_id"], "request.agent.agent_id")
    _version(agent["version"], "request.agent.version")
    actor = _exact(raw["actor"], {"actor_id", "role"}, "request.actor")
    _id(actor["actor_id"], "request.actor.actor_id")
    _id(actor["role"], "request.actor.role")
    call = _exact(raw["tool_call"], {"tool", "action", "target_resource", "data_class"}, "request.tool_call")
    _id(call["tool"], "request.tool_call.tool")
    _id(call["action"], "request.tool_call.action")
    _id(call["target_resource"], "request.tool_call.target_resource")
    if type(call["data_class"]) is not str or DATA_RE.fullmatch(call["data_class"]) is None:
        raise GateError("request.tool_call.data_class invalid")
    approval = raw["approval"]
    if approval is not None:
        approval = _exact(approval, {"approval_id", "approver_role", "evidence_sha256", "intent_sha256"}, "request.approval")
        _id(approval["approval_id"], "request.approval.approval_id")
        _id(approval["approver_role"], "request.approval.approver_role")
        _sha(approval["evidence_sha256"], "request.approval.evidence_sha256")
        _sha(approval["intent_sha256"], "request.approval.intent_sha256")
    _id(raw["idempotency_key"], "request.idempotency_key")
    _int(raw["budget_cents"], "request.budget_cents", 0, 10**15)
    _id(raw["window_id"], "request.window_id")
    trace = _exact(raw["trace"], {"trace_id", "parent_trace_id", "evidence_sha256"}, "request.trace")
    _id(trace["trace_id"], "request.trace.trace_id")
    if trace["parent_trace_id"] is not None:
        _id(trace["parent_trace_id"], "request.trace.parent_trace_id")
    _sha(trace["evidence_sha256"], "request.trace.evidence_sha256")
    return raw


def _receipt_core(policy: Policy, request: dict[str, Any], ledger_sha: str, decision: str, reasons: list[str], rule_key: str | None) -> dict[str, Any]:
    req_sha = sha256(request)
    return {
        "receipt_schema_version": 1,
        "product": "AgentToolCallEvidenceGate",
        "decision": decision,
        "reason_codes": sorted(reasons),
        "policy_id": policy.policy_id,
        "policy_revision": policy.revision,
        "rule_key": rule_key,
        "request_id": request["request_id"],
        "request_sha256": req_sha,
        "prior_ledger_sha256": ledger_sha,
        "evidence_manifest": {
            "policy_sha256": policy.digest,
            "request_sha256": req_sha,
            "prior_ledger_sha256": ledger_sha,
            "trace_evidence_sha256": request["trace"]["evidence_sha256"],
            "approval_evidence_sha256": None if request["approval"] is None else request["approval"]["evidence_sha256"],
        },
        "authority": AUTHORITY,
    }


def evaluate(policy_raw: dict[str, Any], request_raw: dict[str, Any], ledger_raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    policy = Policy.parse(policy_raw)
    request = _parse_request(request_raw)
    entries, ledger_sha = _parse_ledger(ledger_raw, policy)
    reasons: set[str] = set()

    versions = policy.agents.get(request["agent"]["agent_id"])
    if versions is None or request["agent"]["version"] not in versions:
        reasons.add(REASON_AGENT_VERSION)

    call = request["tool_call"]
    key = f"{call['tool']}:{call['action']}"
    rule = policy.rules.get(key)
    if rule is None:
        reasons.add(REASON_TOOL_ACTION)
    else:
        if request["actor"]["role"] not in rule.allowed_roles or not call["target_resource"].startswith(rule.resource_prefix):
            reasons.add(REASON_ROLE_RESOURCE)
        if call["data_class"] in policy.restricted_data_classes or call["data_class"] not in rule.allowed_data_classes:
            reasons.add(REASON_RESTRICTED_DATA)
        if rule.require_human_approval:
            approval = request["approval"]
            if approval is None or approval["approver_role"] not in rule.approval_roles or approval["intent_sha256"] != approval_intent_sha256(request):
                reasons.add(REASON_APPROVAL)
        budget_used = sum(e["budget_cents"] for e in entries if e["rule_key"] == key and e["window_id"] == request["window_id"])
        calls_used = sum(1 for e in entries if e["rule_key"] == key and e["window_id"] == request["window_id"])
        if request["budget_cents"] > rule.max_request_budget_cents or budget_used + request["budget_cents"] > rule.max_window_budget_cents or calls_used + 1 > rule.max_calls_per_window:
            reasons.add(REASON_BUDGET_RATE)

    idem_sha = sha256(request["idempotency_key"].encode("utf-8"))
    if any(e["idempotency_sha256"] == idem_sha or e["request_id"] == request["request_id"] for e in entries):
        reasons.add(REASON_REPLAY)

    trace = request["trace"]
    if not trace["trace_id"] or trace["evidence_sha256"] == "0" * 64:
        reasons.add(REASON_TRACE)

    decision = DECISION_ALLOW if not reasons else DECISION_HOLD
    receipt = _receipt_core(policy, request, ledger_sha, decision, sorted(reasons), key if rule else None)
    receipt["receipt_sha256"] = sha256(receipt)

    if decision == DECISION_HOLD:
        return receipt, deepcopy(ledger_raw)

    entry = {
        "sequence": len(entries) + 1,
        "request_id": request["request_id"],
        "request_sha256": receipt["request_sha256"],
        "idempotency_sha256": idem_sha,
        "rule_key": key,
        "window_id": request["window_id"],
        "budget_cents": request["budget_cents"],
        "receipt_sha256": receipt["receipt_sha256"],
    }
    new_core = {"schema_version": 1, "policy_id": policy.policy_id, "policy_revision": policy.revision, "entries": entries + [entry]}
    new_ledger = {**new_core, "ledger_sha256": sha256(new_core)}
    return receipt, new_ledger


def verify_transition(policy_raw: dict[str, Any], request_raw: dict[str, Any], prior_ledger: dict[str, Any], receipt: dict[str, Any], next_ledger: dict[str, Any]) -> bool:
    try:
        expected_receipt, expected_ledger = evaluate(policy_raw, request_raw, prior_ledger)
        return canonical_bytes(expected_receipt) == canonical_bytes(receipt) and canonical_bytes(expected_ledger) == canonical_bytes(next_ledger)
    except (GateError, TypeError, ValueError, OverflowError):
        return False
