#!/usr/bin/env python3
"""muhl_self_train_address_contract.py — source-only dests FROM FILE.

Slack 1787648830.269449 TAKING
muhl-self-train-address-contract-20260825-01:

  Pure source-only Muhlnickel prerequisite. Exact new paths only.
  No legacy trainer import/execute. No Titan/model/device/container/
  inference. Grok H-006 is candidate evidence only. Larger xproc
  harness is deferred. Unresolved evidence stays UNRESOLVED, never zero.

This leftover reads sibling muhl_self_train.py as text. It does not
import that trainer. It does not execute it. It does not import
pfc_paths or titan_circuit. It does not open titan.gguf. Dest FROM
FILE. Live allocated offsets stay UNRESOLVED. A deterministic
source-space conflict is fail-closed BLOCKED: 30-bit
max_pointer=1073741823, last_safe_start=1073741822,
steps_before_wrap=536870912, required_bits=36, plus a
canonical hash. A Slack TAKING is CLAIMED until these
bytes are on current main. Do not remint.

  python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_self_train_address_contract.py
  python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_self_train_address_contract.py --root .
  python3 muhl/desktop/MUHL_SUBZERO_ARCHETYPES/muhl_self_train_address_contract.py --self-test
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = "."
DEFAULT_CARD = os.path.join("ground", "MUHL_SELF_TRAIN_ADDRESS_CONTRACT.md")
CONTRACT_REL = os.path.join(
    "muhl",
    "desktop",
    "MUHL_SUBZERO_ARCHETYPES",
    "muhl_self_train_address_contract.py",
)
TRAINER_REL = os.path.join(
    "muhl",
    "desktop",
    "MUHL_SUBZERO_ARCHETYPES",
    "muhl_self_train.py",
)
TRAINER_NAME = "muhl_self_train.py"
TEST_REL = "test_muhl_self_train_address_contract.py"
H006_CARD = os.path.join("ground", "MUHL_TRAIN_BRIDGE.md")
H006_HOST = os.path.join("host", "muhl_train_bridge.py")
SLACK_TS = "1787648830.269449"
TAKING_ID = "muhl-self-train-address-contract-20260825-01"
CLAIMED_BASE = "683d0837f6b4b665bcffd32b5b6766ea48414058"
FORBIDDEN_IMPORTS = (
    "muhl_self_train",
    "pfc_paths",
    "titan_circuit",
)
UNRESOLVED = "UNRESOLVED"
CANDIDATE = "CANDIDATE"
DEFERRED = "DEFERRED"
SOURCE_NAMED = "SOURCE_NAMED"
SOURCE_CONFLICT = "SOURCE_CONFLICT"
BLOCKED = "BLOCKED"
ONE_GIB = 1 << 30
TWO_BYTE_STEP = 2
NAMED_PTR_BITS = 30
NAMED_CAPACITY = 50 * ONE_GIB
MAX_POINTER = (1 << NAMED_PTR_BITS) - 1
LAST_SAFE_START = MAX_POINTER - 1
STEPS_BEFORE_WRAP = (1 << NAMED_PTR_BITS) // TWO_BYTE_STEP
REQUIRED_BITS = 36
PTR_BITS_CAPACITY_CONFLICT = "ptr_bits_vs_capacity"
SEARCH_SPACE = (
    DEFAULT_CARD,
    CONTRACT_REL,
    TEST_REL,
    TRAINER_REL,
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
)
CALIBRATION = (
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
)
REQUIRED_PHRASES = (
    "source-only",
    "dest from file",
    "no legacy trainer import",
    "no titan",
    "h-006 is candidate evidence only",
    "xproc harness is deferred",
    "unresolved",
    "never 0",
    "finder-failed",
    "talk is not a land",
    "no auth",
    "no gate",
    "do not remint",
    "max_pointer",
    "last_safe_start",
    "steps_before_wrap",
    "required_bits",
    "fail-closed",
    "blocked",
)
REQUIRED_PACKET_FIELDS = (
    "kind",
    "source_index",
    "dests",
    "live_offsets",
    "host_inference",
    "titan",
    "legacy_trainer_import",
    "legacy_trainer_execute",
    "xproc",
    "h006",
)
NAMED_DEST_KEYS = (
    "name",
    "reservoir_input",
    "intake_header",
    "intake_capacity",
    "weight_bytes",
    "nw",
    "nf",
    "h",
    "ncls",
    "ptr_bits",
    "file_marker",
    "receiver",
    "write_ptr_rel",
    "size_rel",
    "capacity_rel",
    "data_start_rel",
)


def required_bits_for(span):
    """Bits needed to name pointers 0 .. span-1. Missing span stays None."""
    if not isinstance(span, int) or span <= 0:
        return None
    value = span - 1
    bits = 0
    while value:
        value >>= 1
        bits += 1
    return bits


def pointer_space(ptr_bits=None, capacity=None):
    """30-bit two-byte wrap facts. Live allocated offsets stay UNRESOLVED."""
    bits = ptr_bits if isinstance(ptr_bits, int) and ptr_bits > 0 else NAMED_PTR_BITS
    max_pointer = (1 << bits) - 1
    last_safe_start = max_pointer - 1 if max_pointer else 0
    steps_before_wrap = (1 << bits) // TWO_BYTE_STEP
    needed = required_bits_for(capacity)
    return {
        "max_pointer": max_pointer,
        "last_safe_start": last_safe_start,
        "steps_before_wrap": steps_before_wrap,
        "required_bits": needed if needed is not None else REQUIRED_BITS,
    }


def canonical_conflict_payload(space=None, ptr_bits=None, capacity=None):
    space = space or pointer_space(ptr_bits=ptr_bits, capacity=capacity)
    return {
        "id": PTR_BITS_CAPACITY_CONFLICT,
        "last_safe_start": int(space["last_safe_start"]),
        "max_pointer": int(space["max_pointer"]),
        "named_capacity": int(
            capacity if isinstance(capacity, int) else NAMED_CAPACITY
        ),
        "ptr_bits": int(ptr_bits if isinstance(ptr_bits, int) else NAMED_PTR_BITS),
        "required_bits": int(space["required_bits"]),
        "steps_before_wrap": int(space["steps_before_wrap"]),
    }


def canonical_conflict_hash(space=None, ptr_bits=None, capacity=None):
    payload = canonical_conflict_payload(
        space=space, ptr_bits=ptr_bits, capacity=capacity
    )
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def source_space_conflicts(dests):
    """Deterministic source-space conflicts. Never invent live offsets."""
    dests = dests or {}
    capacity = dests.get("intake_capacity")
    ptr_bits = dests.get("ptr_bits")
    conflicts = []
    if not (isinstance(capacity, int) and isinstance(ptr_bits, int)):
        return conflicts
    if (1 << ptr_bits) == capacity:
        return conflicts
    space = pointer_space(ptr_bits=ptr_bits, capacity=capacity)
    payload = canonical_conflict_payload(
        space=space, ptr_bits=ptr_bits, capacity=capacity
    )
    digest = canonical_conflict_hash(
        space=space, ptr_bits=ptr_bits, capacity=capacity
    )
    conflicts.append(
        {
            "id": PTR_BITS_CAPACITY_CONFLICT,
            "state": SOURCE_CONFLICT,
            "max_pointer": space["max_pointer"],
            "last_safe_start": space["last_safe_start"],
            "steps_before_wrap": space["steps_before_wrap"],
            "required_bits": space["required_bits"],
            "canonical_hash": digest,
            "canonical_payload": payload,
            "note": (
                "PTR_BITS=%s addresses %s bytes; INTAKE_CAPACITY=%s. "
                "fail-closed BLOCKED. max_pointer=%s last_safe_start=%s "
                "steps_before_wrap=%s required_bits=%s canonical_hash=%s. "
                "Live allocated offsets stay UNRESOLVED. Never 0."
                % (
                    ptr_bits,
                    1 << ptr_bits,
                    capacity,
                    space["max_pointer"],
                    space["last_safe_start"],
                    space["steps_before_wrap"],
                    space["required_bits"],
                    digest,
                )
            ),
        }
    )
    return conflicts


def conflict_is_source_space(item):
    return str((item or {}).get("state") or "").strip().upper() == SOURCE_CONFLICT


def _read(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _exists(root, rel):
    return os.path.isfile(os.path.join(root, rel))


def _const_int(node, env=None):
    env = env or {}
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _const_int(node.operand, env)
        return None if value is None else -value
    if isinstance(node, ast.Name):
        value = env.get(node.id)
        return value if isinstance(value, int) else None
    if isinstance(node, ast.BinOp):
        left = _const_int(node.left, env)
        right = _const_int(node.right, env)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.LShift):
            return left << right
    return None


def _const_text(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bytes):
            return node.value.decode("ascii", "replace")
        if isinstance(node.value, str):
            return node.value
    return None


def parse_trainer_source(text):
    """Read dests FROM FILE. Parse is not import and not execute."""
    if not str(text or "").strip():
        return {
            "ok": False,
            "state": UNRESOLVED,
            "z": "FINDER-FAILED",
            "note": (
                "trainer source not read. Absence was not stillness. "
                "FINDER-FAILED, never 0."
            ),
            "dests": {},
            "live_offsets": UNRESOLVED,
            "conflicts": [],
        }
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {
            "ok": False,
            "state": UNRESOLVED,
            "z": "FINDER-FAILED",
            "note": "trainer source is not parseable: %s. FINDER-FAILED, never 0." % exc,
            "dests": {},
            "live_offsets": UNRESOLVED,
            "conflicts": [],
        }
    env = {}
    dests = {}
    receiver = UNRESOLVED
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        name = target.id
        number = _const_int(node.value, env)
        if number is not None:
            env[name] = number
        text_value = _const_text(node.value)
        if name == "NAME" and text_value:
            dests["name"] = text_value
        elif name == "RESERVOIR_INPUT" and number is not None:
            dests["reservoir_input"] = number
        elif name == "INTAKE_HEADER" and number is not None:
            dests["intake_header"] = number
        elif name == "INTAKE_CAPACITY" and number is not None:
            dests["intake_capacity"] = number
        elif name == "WEIGHT_BYTES" and number is not None:
            dests["weight_bytes"] = number
        elif name == "NW" and number is not None:
            dests["nw"] = number
        elif name == "NF" and number is not None:
            dests["nf"] = number
        elif name == "H" and number is not None:
            dests["h"] = number
        elif name == "NCLS" and number is not None:
            dests["ncls"] = number
        elif name == "PTR_BITS" and number is not None:
            dests["ptr_bits"] = number
        elif name == "FILE_MARKER" and text_value:
            dests["file_marker"] = text_value
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "receiver":
                value = _const_text(keyword.value)
                if value:
                    receiver = value
    dests["receiver"] = receiver
    header = dests.get("intake_header")
    dests["write_ptr_rel"] = 0 if header is not None else UNRESOLVED
    dests["size_rel"] = 8 if header is not None else UNRESOLVED
    dests["capacity_rel"] = 16 if header is not None else UNRESOLVED
    dests["data_start_rel"] = header if header is not None else UNRESOLVED
    conflicts = []
    capacity = dests.get("intake_capacity")
    ptr_bits = dests.get("ptr_bits")
    space = pointer_space(ptr_bits=ptr_bits, capacity=capacity)
    if isinstance(capacity, int) and capacity != ONE_GIB and "1 GB" in text:
        conflicts.append(
            {
                "id": "intake_capacity_comment",
                "state": SOURCE_CONFLICT,
                "max_pointer": space["max_pointer"],
                "last_safe_start": space["last_safe_start"],
                "steps_before_wrap": space["steps_before_wrap"],
                "required_bits": space["required_bits"],
                "note": (
                    "source names INTAKE_CAPACITY=%s while comments still "
                    "say 1 GB. fail-closed BLOCKED. max_pointer=%s "
                    "last_safe_start=%s steps_before_wrap=%s "
                    "required_bits=%s. Live size stays UNRESOLVED. Never 0."
                    % (
                        capacity,
                        space["max_pointer"],
                        space["last_safe_start"],
                        space["steps_before_wrap"],
                        space["required_bits"],
                    )
                ),
            }
        )
    conflicts.extend(source_space_conflicts(dests))
    missing = [key for key in NAMED_DEST_KEYS if dests.get(key) in (None, "", UNRESOLVED)]
    ok = not missing
    return {
        "ok": ok,
        "state": SOURCE_NAMED if ok else UNRESOLVED,
        "z": "" if ok else "FINDER-FAILED",
        "note": (
            "named dests read FROM FILE. Live allocated offsets stay "
            "UNRESOLVED."
            if ok
            else (
                "named dests missing from trainer source: "
                + ", ".join(missing)
                + ". FINDER-FAILED, never 0."
            )
        ),
        "dests": dests,
        "live_offsets": {
            "intake_off": UNRESOLVED,
            "weights_off": UNRESOLVED,
            "circuit_off": UNRESOLVED,
            "state_off": UNRESOLVED,
            "loop_bit_off": UNRESOLVED,
        },
        "conflicts": conflicts,
        "missing": missing,
    }


def trainer_imported():
    return any(name in sys.modules for name in FORBIDDEN_IMPORTS)


def classify_h006(root):
    """H-006 is candidate evidence only. Missing stays UNRESOLVED, never 0."""
    card = _exists(root, H006_CARD)
    host = _exists(root, H006_HOST)
    if card or host:
        return {
            "state": CANDIDATE,
            "note": (
                "H-006 / MUHL_TRAIN_BRIDGE is present as candidate "
                "evidence only. It is not a live train and not this leftover."
            ),
            "paths": [rel for rel in (H006_CARD, H006_HOST) if _exists(root, rel)],
        }
    return {
        "state": UNRESOLVED,
        "note": (
            "H-006 / MUHL_TRAIN_BRIDGE was not read on this tree. "
            "Absence is UNRESOLVED, never 0."
        ),
        "paths": [],
        "z": "FINDER-UNVERIFIED",
    }


def synthetic_packet(parsed=None):
    dests = dict((parsed or {}).get("dests") or {})
    return {
        "kind": "MUHL_SELF_TRAIN_ADDRESS",
        "source_index": TRAINER_REL,
        "dests": dests,
        "live_offsets": UNRESOLVED,
        "host_inference": False,
        "titan": "NOT_WRITTEN",
        "legacy_trainer_import": False,
        "legacy_trainer_execute": False,
        "xproc": DEFERRED,
        "h006": CANDIDATE,
    }


def validate_packet(obj, parsed=None):
    """Classify one synthetic address packet. Unchanged/missing is never 0."""
    if not isinstance(obj, dict) or not obj:
        return {
            "state": "UNMEASURED",
            "note": (
                "address packet not read. Absence was not stillness. "
                "FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    kind = str(obj.get("kind") or "").strip().upper()
    if kind in ("TAKING", "TAKING_BACKEND_SWARM"):
        return {
            "state": "CARRIER_ONLY",
            "note": (
                "Slack taking is mail. Talk is CLAIMED until the leftover "
                "ships. FINDER-UNVERIFIED, never 0."
            ),
            "z": "FINDER-UNVERIFIED",
        }
    if kind != "MUHL_SELF_TRAIN_ADDRESS":
        return {
            "state": "NOT_LANDED",
            "note": "kind is not MUHL_SELF_TRAIN_ADDRESS. FINDER-FAILED, never 0.",
            "z": "FINDER-FAILED",
        }
    missing = [field for field in REQUIRED_PACKET_FIELDS if field not in obj]
    if missing:
        return {
            "state": "NOT_LANDED",
            "note": (
                "missing fields: "
                + ", ".join(missing)
                + ". FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    if obj.get("host_inference") is True or str(obj.get("host_inference")).lower() == "true":
        return {
            "state": "NOT_LANDED",
            "note": "host inference is refused. Source-only. FINDER-FAILED, never 0.",
            "z": "FINDER-FAILED",
        }
    if obj.get("legacy_trainer_import") is True or obj.get("legacy_trainer_execute") is True:
        return {
            "state": "NOT_LANDED",
            "note": (
                "legacy trainer import/execute is refused. FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    titan = str(obj.get("titan") or "").strip().upper()
    if titan not in ("NOT_WRITTEN", "NOT_LANDED"):
        return {
            "state": "NOT_LANDED",
            "note": "live Titan is refused. titan stays NOT_WRITTEN. FINDER-FAILED, never 0.",
            "z": "FINDER-FAILED",
        }
    live = obj.get("live_offsets")
    if live in (0, "0", 0.0) or live is None:
        return {
            "state": "NOT_LANDED",
            "note": (
                "live allocated offsets must stay UNRESOLVED. A zero is a "
                "broken test. FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    if str(live).strip().upper() != UNRESOLVED and not (
        isinstance(live, dict)
        and all(str(value).strip().upper() == UNRESOLVED for value in live.values())
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "invented live offsets are refused. Dest FROM FILE only. "
                "FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    if str(obj.get("xproc") or "").strip().upper() not in (DEFERRED, UNRESOLVED):
        return {
            "state": "NOT_LANDED",
            "note": "larger xproc harness stays DEFERRED / UNRESOLVED. Never 0.",
            "z": "FINDER-FAILED",
        }
    h006 = str(obj.get("h006") or "").strip().upper()
    if h006 not in (CANDIDATE, UNRESOLVED):
        return {
            "state": "NOT_LANDED",
            "note": (
                "H-006 is candidate evidence only. Do not treat it as a live "
                "train. FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    dests = obj.get("dests")
    if not isinstance(dests, dict) or not dests:
        return {
            "state": "NOT_LANDED",
            "note": "dests missing. Dest FROM FILE. FINDER-FAILED, never 0.",
            "z": "FINDER-FAILED",
        }
    if parsed and parsed.get("ok"):
        expected = parsed.get("dests") or {}
        for key in NAMED_DEST_KEYS:
            if dests.get(key) != expected.get(key):
                return {
                    "state": "NOT_LANDED",
                    "note": (
                        "dest %s does not match trainer source. FINDER-FAILED, never 0."
                        % key
                    ),
                    "z": "FINDER-FAILED",
                }
    found = []
    for item in list((parsed or {}).get("conflicts") or []):
        if conflict_is_source_space(item):
            found.append(item)
    for item in source_space_conflicts(dests):
        if item.get("id") not in {row.get("id") for row in found}:
            found.append(item)
    if found:
        record = next(
            (item for item in found if item.get("id") == PTR_BITS_CAPACITY_CONFLICT),
            found[0],
        )
        digest = record.get("canonical_hash") or canonical_conflict_hash(
            ptr_bits=dests.get("ptr_bits"),
            capacity=dests.get("intake_capacity"),
        )
        return {
            "state": BLOCKED,
            "note": (
                "deterministic source-space conflict is fail-closed BLOCKED. "
                "max_pointer=%s last_safe_start=%s steps_before_wrap=%s "
                "required_bits=%s canonical_hash=%s. Live offsets stay "
                "UNRESOLVED. Never 0."
                % (
                    record.get("max_pointer", MAX_POINTER),
                    record.get("last_safe_start", LAST_SAFE_START),
                    record.get("steps_before_wrap", STEPS_BEFORE_WRAP),
                    record.get("required_bits", REQUIRED_BITS),
                    digest,
                )
            ),
            "z": "FINDER-FAILED",
            "max_pointer": record.get("max_pointer", MAX_POINTER),
            "last_safe_start": record.get("last_safe_start", LAST_SAFE_START),
            "steps_before_wrap": record.get("steps_before_wrap", STEPS_BEFORE_WRAP),
            "required_bits": record.get("required_bits", REQUIRED_BITS),
            "canonical_hash": digest,
            "conflicts": found,
        }
    return {
        "state": "SYNTHETIC_OK",
        "note": (
            "source-only address packet is well-formed. Live offsets stay "
            "UNRESOLVED. H-006 stays candidate. xproc stays deferred. "
            "This is not a live train."
        ),
        "z": "",
    }


def measure_from_rows(facts):
    facts = facts or {}
    return {
        "measured": True,
        "card_present": bool(facts.get("card_present")),
        "contract_present": bool(facts.get("contract_present")),
        "test_present": bool(facts.get("test_present")),
        "trainer_present": bool(facts.get("trainer_present")),
        "parsed_ok": bool(facts.get("parsed_ok")),
        "dests": dict(facts.get("dests") or {}),
        "live_offsets": facts.get("live_offsets") or UNRESOLVED,
        "conflicts": list(facts.get("conflicts") or []),
        "max_pointer": facts.get("max_pointer", MAX_POINTER),
        "last_safe_start": facts.get("last_safe_start", LAST_SAFE_START),
        "steps_before_wrap": facts.get("steps_before_wrap", STEPS_BEFORE_WRAP),
        "required_bits": facts.get("required_bits", REQUIRED_BITS),
        "canonical_hash": facts.get("canonical_hash") or "",
        "found_phrases": list(facts.get("found_phrases") or []),
        "h006": dict(facts.get("h006") or {}),
        "xproc": str(facts.get("xproc") or DEFERRED),
        "packet_ok": bool(facts.get("packet_ok")),
        "legacy_import": bool(facts.get("legacy_import")),
        "posting_open": bool(facts.get("posting_open")),
        "no_auth": bool(facts.get("no_auth")),
        "no_gate": bool(facts.get("no_gate")),
        "calibration_ok": bool(facts.get("calibration_ok")),
        "calibration_hits": list(facts.get("calibration_hits") or []),
        "search_space": list(facts.get("search_space") or SEARCH_SPACE),
        "misses": list(facts.get("misses") or []),
        "titan": str(facts.get("titan") or "NOT_WRITTEN"),
        "slack_ts": str(facts.get("slack_ts") or SLACK_TS),
        "taking_id": str(facts.get("taking_id") or TAKING_ID),
    }


def classify(row):
    """Turn a measured address-contract leftover into a desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "self-train address-contract leftover not read. Absence was "
                "not stillness. A Slack TAKING is not a land. FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    if row.get("calibration_ok") is False:
        return {
            "state": "UNMEASURED",
            "note": (
                "known-present calibration failed: "
                + ", ".join(row.get("calibration_hits") or [])
                + ". Search-zero testing is instrument failure, not absence "
                "proof. FINDER-FAILED. Never 0."
            ),
            "z": "FINDER-FAILED",
        }
    if row.get("legacy_import"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "legacy trainer / pfc_paths / titan_circuit was imported. "
                "Source-only leftover refuses that. FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    misses = list(row.get("misses") or [])
    if (
        not row.get("card_present")
        or not row.get("contract_present")
        or not row.get("test_present")
        or not row.get("trainer_present")
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "missing leftover path(s): "
                + ", ".join(misses or ["card/contract/test/trainer"])
                + ". Slack TAKING stays CLAIMED. FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    if not row.get("parsed_ok"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "trainer source did not yield named dests FROM FILE. "
                "FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    conflicts = [item for item in list(row.get("conflicts") or []) if conflict_is_source_space(item)]
    if conflicts:
        record = next(
            (item for item in conflicts if item.get("id") == PTR_BITS_CAPACITY_CONFLICT),
            conflicts[0],
        )
        digest = record.get("canonical_hash") or row.get("canonical_hash") or canonical_conflict_hash()
        return {
            "state": BLOCKED,
            "note": (
                "deterministic source-space conflict is fail-closed BLOCKED. "
                "max_pointer=%s last_safe_start=%s steps_before_wrap=%s "
                "required_bits=%s canonical_hash=%s. Live allocated offsets "
                "stay UNRESOLVED. Never 0."
                % (
                    record.get("max_pointer", MAX_POINTER),
                    record.get("last_safe_start", LAST_SAFE_START),
                    record.get("steps_before_wrap", STEPS_BEFORE_WRAP),
                    record.get("required_bits", REQUIRED_BITS),
                    digest,
                )
            ),
            "z": "FINDER-FAILED",
            "taking_state": "CLAIMED",
            "max_pointer": record.get("max_pointer", MAX_POINTER),
            "last_safe_start": record.get("last_safe_start", LAST_SAFE_START),
            "steps_before_wrap": record.get("steps_before_wrap", STEPS_BEFORE_WRAP),
            "required_bits": record.get("required_bits", REQUIRED_BITS),
            "canonical_hash": digest,
        }
    needed = [phrase for phrase in REQUIRED_PHRASES if phrase not in (row.get("found_phrases") or [])]
    if (
        needed
        or not row.get("posting_open")
        or not row.get("no_auth")
        or not row.get("no_gate")
        or not row.get("packet_ok")
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "leftover present but incomplete. Missing phrases: "
                + ", ".join(needed)
                + ". Open door + no auth + no gate required. Talk is CLAIMED. "
                "FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    h006 = (row.get("h006") or {}).get("state") or UNRESOLVED
    if h006 not in (CANDIDATE, UNRESOLVED):
        return {
            "state": "NOT_LANDED",
            "note": (
                "H-006 must stay CANDIDATE or UNRESOLVED. Never treat it as "
                "a live train. FINDER-FAILED, never 0."
            ),
            "z": "FINDER-FAILED",
        }
    return {
        "state": "INTEGRATED",
        "note": (
            "self-train address-contract leftover is on this tree. Named "
            "dests are FROM FILE. Live allocated offsets stay UNRESOLVED. "
            "H-006 stays %s. xproc stays %s. A Slack TAKING is still not "
            "the file."
            % (h006, row.get("xproc") or DEFERRED)
        ),
        "z": "",
        "taking_state": "CLAIMED",
        "h006": h006,
        "xproc": row.get("xproc") or DEFERRED,
    }


def measure_root(root):
    root = os.path.abspath(root)
    misses = []
    blobs = []
    for rel in SEARCH_SPACE:
        text = _read(root, rel)
        if not text:
            misses.append(rel)
        else:
            blobs.append(text)
    hay = "\n".join(blobs).lower()
    found = [phrase for phrase in REQUIRED_PHRASES if phrase in hay]
    trainer_text = _read(root, TRAINER_REL)
    if not trainer_text:
        sibling = os.path.join(HERE, TRAINER_NAME)
        if os.path.isfile(sibling):
            with open(sibling, encoding="utf-8", errors="replace") as handle:
                trainer_text = handle.read()
    parsed = parse_trainer_source(trainer_text)
    packet = validate_packet(synthetic_packet(parsed), parsed=parsed)
    h006 = classify_h006(root)
    calibration_hits = [rel for rel in CALIBRATION if _exists(root, rel)]
    calibration_ok = len(calibration_hits) == len(CALIBRATION)
    if not calibration_ok:
        for rel in CALIBRATION:
            if rel not in calibration_hits and ("calibration:" + rel) not in misses:
                misses.append("calibration:" + rel)
    facts = {
        "card_present": _exists(root, DEFAULT_CARD),
        "contract_present": _exists(root, CONTRACT_REL) or os.path.isfile(
            os.path.join(HERE, os.path.basename(CONTRACT_REL))
        ),
        "test_present": _exists(root, TEST_REL),
        "trainer_present": bool(trainer_text),
        "parsed_ok": bool(parsed.get("ok")),
        "dests": parsed.get("dests") or {},
        "live_offsets": parsed.get("live_offsets") or UNRESOLVED,
        "conflicts": parsed.get("conflicts") or [],
        "found_phrases": found,
        "h006": h006,
        "xproc": DEFERRED,
        "packet_ok": packet.get("state") == "SYNTHETIC_OK",
        "legacy_import": trainer_imported(),
        "posting_open": "open door" in hay and "unseated" in hay,
        "no_auth": "no auth" in hay,
        "no_gate": "no gate" in hay,
        "calibration_ok": calibration_ok,
        "calibration_hits": calibration_hits,
        "search_space": list(SEARCH_SPACE),
        "misses": misses,
        "titan": "NOT_WRITTEN",
        "slack_ts": SLACK_TS,
        "taking_id": TAKING_ID,
        "max_pointer": MAX_POINTER,
        "last_safe_start": LAST_SAFE_START,
        "steps_before_wrap": STEPS_BEFORE_WRAP,
        "required_bits": REQUIRED_BITS,
        "canonical_hash": canonical_conflict_hash(
            ptr_bits=(parsed.get("dests") or {}).get("ptr_bits"),
            capacity=(parsed.get("dests") or {}).get("intake_capacity"),
        ),
    }
    row = measure_from_rows(facts)
    row.update(
        {
            "parsed": parsed,
            "packet": packet,
            "h006": h006,
            "x": [rel for rel in SEARCH_SPACE if _exists(root, rel)],
            "y": {
                "dests": parsed.get("dests") or {},
                "conflicts": parsed.get("conflicts") or [],
                "h006": h006.get("state"),
                "packet": packet.get("state"),
                "calibration_hits": calibration_hits,
            },
            "z": row.get("misses")
            or parsed.get("conflicts")
            or "FINDER-UNVERIFIED live offsets / xproc / unresolved evidence, never 0",
        }
    )
    return row


def self_test():
    empty = classify({})
    if empty.get("state") != "UNMEASURED":
        return False
    silent = validate_packet(
        {
            "kind": "MUHL_SELF_TRAIN_ADDRESS",
            "source_index": TRAINER_REL,
            "dests": {"name": "muhl_self_train"},
            "live_offsets": 0,
            "host_inference": False,
            "titan": "NOT_WRITTEN",
            "legacy_trainer_import": False,
            "legacy_trainer_execute": False,
            "xproc": DEFERRED,
            "h006": CANDIDATE,
        }
    )
    if silent.get("state") != "NOT_LANDED" or "never 0" not in silent.get("note", "").lower():
        return False
    missing = parse_trainer_source("")
    if missing.get("state") != UNRESOLVED or missing.get("z") != "FINDER-FAILED":
        return False
    conflicted = parse_trainer_source(
        "INTAKE_CAPACITY = 50 * (1 << 30)  # 1 GB\nPTR_BITS = 30\n"
    )
    blocked = validate_packet(synthetic_packet(conflicted), parsed=conflicted)
    if blocked.get("state") != BLOCKED:
        return False
    if blocked.get("max_pointer") != MAX_POINTER:
        return False
    if blocked.get("last_safe_start") != LAST_SAFE_START:
        return False
    if blocked.get("steps_before_wrap") != STEPS_BEFORE_WRAP:
        return False
    if blocked.get("required_bits") != REQUIRED_BITS:
        return False
    if not blocked.get("canonical_hash"):
        return False
    return trainer_imported() is False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Measure the source-only self-train address contract"
    )
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return 0 if self_test() else 1
    row = measure_root(args.root)
    verdict = classify(row)
    payload = dict(row)
    payload.update(verdict)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if verdict.get("state") == "INTEGRATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
