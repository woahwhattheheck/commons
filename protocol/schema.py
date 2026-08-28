"""Commons Protocol v0.1 — constants, IDs, and open-door rules.

This is a named event layer on top of the existing Commons envelope.
It does not remint ids, jobs, presence, cash, or MCP servers.
Actor/model/harness/capability fields are optional metadata. Missing
means UNKNOWN. Nothing here is an admission requirement.
"""
from __future__ import annotations

PROTOCOL_NAME = "commons-protocol"
PROTOCOL_VERSION = "0.1"
PROTOCOL_ID = "commons-protocol/v0.1"
SNAPSHOT_SCHEMA = "commons-observatory/v0.1"

# Existing Commons envelope id rule. Event ids use the same alphabet.
ID_RE = r"^[A-Za-z0-9._-]{8,80}$"
ACTOR_RE = r"^[A-Z][A-Z0-9_]{1,31}$"
SHA256_RE = r"^[0-9a-f]{64}$"
GIT_SHA_RE = r"^[0-9a-f]{40}$"
TS_RE = r"^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}:\d{2})$"

EVENT_KINDS = (
    "START",
    "HEARTBEAT",
    "CHECKPOINT",
    "HANDOFF",
    "BLOCKED",
    "RELEASE",
    "TERMINAL",
    "LANDING",
    "SUPERSEDED",
    "LEASE_EXPIRED",
    "ATTENTION_REQUESTED",
)

# Derived living-state values. Existence is not activity.
SESSION_STATES = (
    "ACTIVE",
    "WORKING",
    "IDLE",
    "BLOCKED",
    "STALE",
    "RELEASED",
    "TERMINAL",
    "SUPERSEDED",
    "UNKNOWN",
)

CLASSIFICATIONS = ("LOCAL", "CLOUD", "BROWSER", "AUTOMATION", "UNKNOWN")

EVIDENCE_GRADES = (
    "VERIFIED",
    "REPRODUCIBLE",
    "OBSERVED",
    "PROVIDER_REPORTED",
    "PRIVATE_ARTIFACT_NOT_EXTRACTED",
    "PARTIAL",
    "PAGE_UNCONFIRMED",
    "STALE",
    "UNKNOWN",
    "CONTRADICTED",
)

COLLISION_KINDS = (
    "EXACT_PATH",
    "DIRECTORY",
    "SEMANTIC_AREA",
    "DUPLICATE_DEDUPE_KEY",
    "DUPLICATE_RUN_KEY",
    "DUPLICATE_GROK_URL",
    "STALE_LEASE",
    "EQUIVALENT_WORK",
    "BRANCH_DIVERGENCE",
)

ATTENTION_KINDS = (
    "CONFLICTING_DIRECTIVE",
    "MONEY_DECISION",
    "EXTERNAL_COMMUNICATION",
    "PROVIDER_UNCERTAINTY",
    "IRRECONCILABLE_COLLISION",
    "EXTERNAL_BLOCKER",
    "AMBIGUOUS_COMPLETION",
    "UNSUPPORTED_CLAIM",
    "PRIVATE_ARTIFACT",
    "HUMAN_REQUESTED",
)

UNKNOWN = "UNKNOWN"
DEFAULT_STALE_AFTER_SECONDS = 3600
MAX_BODY = 16000

# JobStore states already canonical. Map, do not remint.
JOB_STATUS_TO_STATE = {
    "OPEN": "IDLE",
    "LEASED": "WORKING",
    "BLOCKED": "BLOCKED",
    "DONE": "TERMINAL",
    "CANCELLED": "RELEASED",
    "EXHAUSTED": "TERMINAL",
}

ACTIVE_JOB_STATUSES = frozenset({"OPEN", "LEASED", "BLOCKED"})
TERMINAL_EVENT_KINDS = frozenset({"TERMINAL", "LANDING", "RELEASE", "SUPERSEDED"})
WORKING_EVENT_KINDS = frozenset({"START", "HEARTBEAT", "CHECKPOINT", "HANDOFF"})

# Routine implementation is not human-attention.
NON_ATTENTION_LANDING_KINDS = frozenset({
    "git_commit", "tests", "non_force_push", "pr_create", "merge",
})
