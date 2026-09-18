#!/usr/bin/env python3
"""Evidence-bound terminality for the actionable Commons UNSEATED queue.

Durable posts remain historical records. This module answers a narrower question:
whether an UNSEATED card is already terminal and therefore must not be advertised
as actionable work. Suppression requires an explicit stable identity AND a commit
that is an ancestor of the examined HEAD. Any missing, malformed, or ambiguous
proof leaves the card visible.
"""
from __future__ import annotations

import json
import os
import re
import subprocess

SCHEMA = "commons-work-terminality-v1"
TERMINAL_STATE = "LANDED_ON_MAIN"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,160}$")
_OPERATION_LINE_RE = re.compile(
    r"^\s*Operation:\s*`?([A-Za-z0-9._-]{8,160})`?\s*$"
)


def _no_duplicate_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key: %s" % key)
        out[key] = value
    return out


def _reject_constant(value):
    raise ValueError("non-finite JSON constant: %s" % value)


def loads_strict(text):
    return json.loads(
        text,
        object_pairs_hook=_no_duplicate_object,
        parse_constant=_reject_constant,
    )


def load_registry(root=".", path=None):
    path = path or os.path.join(root, "work_terminality.json")
    with open(path, encoding="utf-8") as handle:
        data = loads_strict(handle.read())
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("unsupported terminality registry schema")
    if not isinstance(data.get("entries"), list):
        raise ValueError("terminality registry entries must be a list")
    return data


def _git_is_ancestor(root, evidence_commit, head):
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", evidence_commit, head],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def _valid_issue_number(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def active_terminal_index(root=".", registry=None, head="HEAD", is_ancestor=None):
    """Return only terminal records whose evidence commit is on the examined HEAD.

    Invalid records are ignored rather than suppressing work. That is intentional:
    uncertainty must keep an UNSEATED card visible.
    """
    if registry is None:
        try:
            registry = load_registry(root)
        except (OSError, ValueError, json.JSONDecodeError):
            return {"operation_ids": {}, "card_ids": {}}
    if not isinstance(registry, dict) or registry.get("schema") != SCHEMA:
        return {"operation_ids": {}, "card_ids": {}}
    entries = registry.get("entries")
    if not isinstance(entries, list):
        return {"operation_ids": {}, "card_ids": {}}

    checker = is_ancestor or (lambda evidence, target: _git_is_ancestor(root, evidence, target))
    operation_ids = {}
    card_ids = {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        operation_id = str(entry.get("operation_id") or "")
        evidence_commit = str(entry.get("evidence_commit") or "")
        state = str(entry.get("terminal_state") or "")
        canonical_issue = entry.get("canonical_issue")
        duplicates = entry.get("duplicate_issues")
        cards = entry.get("card_ids")

        if state != TERMINAL_STATE:
            continue
        if not _ID_RE.fullmatch(operation_id):
            continue
        if not _SHA_RE.fullmatch(evidence_commit):
            continue
        if not _valid_issue_number(canonical_issue):
            continue
        if not isinstance(duplicates, list) or any(not _valid_issue_number(v) for v in duplicates):
            continue
        if not isinstance(cards, list) or any(
            not isinstance(v, str) or not _ID_RE.fullmatch(v) for v in cards
        ):
            continue
        try:
            on_head = bool(checker(evidence_commit, head))
        except Exception:
            on_head = False
        if not on_head:
            continue

        operation_ids[operation_id] = evidence_commit
        card_ids[operation_id] = operation_id
        for card_id in cards:
            card_ids[card_id] = operation_id

    return {"operation_ids": operation_ids, "card_ids": card_ids}


def explicit_operation_id(row):
    """Return an exact structured Operation: identity, never a fuzzy title match."""
    if not isinstance(row, dict):
        return ""
    body = str(row.get("body") or "")
    for line in body.splitlines()[:16]:
        match = _OPERATION_LINE_RE.fullmatch(line)
        if match:
            return match.group(1)
    return ""


def is_actionable_terminal(row, index):
    if not isinstance(row, dict):
        return False
    if str(row.get("from") or "").strip().upper() != "UNSEATED":
        return False
    if not isinstance(index, dict):
        return False

    card_id = str(row.get("id") or "").strip()
    cards = index.get("card_ids") or {}
    operations = index.get("operation_ids") or {}
    if card_id and card_id in cards:
        return True

    operation_id = explicit_operation_id(row)
    return bool(operation_id and operation_id in operations)


def filter_actionable_rows(rows, root=".", registry=None, head="HEAD", is_ancestor=None):
    """Preserve ordering/history semantics while removing proven terminal work cards."""
    index = active_terminal_index(
        root=root,
        registry=registry,
        head=head,
        is_ancestor=is_ancestor,
    )
    return [
        row
        for row in list(rows or [])
        if not is_actionable_terminal(row, index)
    ]
