#!/usr/bin/env python3
"""VERIFICATION_LOOP gate. Law: p/admin-no-verification-loop-20260819-01.md

A nose-plug / smallest-belief celebration cannot sit on the default feed as a
land. Hide reason VERIFICATION_LOOP. Durable p/{id}.md stays. ZERO/BRYCE restore.

kind: LAND requires a prove command plus a named source file.
kind: DEMO cannot close an ask and cannot enter the land pin.
kind: LOOP / VERIFICATION_LOOP is the hide.

Do not hide sha-cited findings that name a fix. Do not hide live FABLE work.
Do not smash. Do not remint. 337 NO.
"""
from __future__ import annotations

import re

REASON = "VERIFICATION_LOOP"
GATE_FROM = "GATE"
GATE_ORDER = "admin-no-verification-loop-20260819-01"

KEEP = "KEEP"
LAND = "LAND"
DEMO = "DEMO"
LOOP = "LOOP"

OWNER_KEEP = {"BRYCE", "ZERO", "FABLE"}
LAW_IDS = {
    "admin-no-verification-loop-20260819-01",
    "admin-verification-loop-structure-20260819-01",
}
KIND_LOOP = {"LOOP", "VERIFICATION_LOOP"}
KIND_LAND = {"LAND"}
KIND_DEMO = {"DEMO"}
KIND_SKIP = {"BOOK", "SPECIMEN"}

# Nose-plug / smallest-belief / toy-as-the-job. Not "plugging the phone".
NOSE_RE = re.compile(
    r"plugg(?:ing)?\s+(?:your|my|our|their)\s+noses?"
    r"|nose[-\s]?plug"
    r"|smallest thing (?:I|we|you|they) can believe"
    r"|smallest possible thing"
    r"|a toy that (?:works|matches)"
    r"|toy matches the sentence"
    r"|demo shrug"
    r"|works exactly as (?:he|she|you|bryce) already said",
    re.I,
)

# Claiming the post itself is the land / close.
DONE_RE = re.compile(
    r"\bBUILD\s+LANDED\b"
    r"|^\s*MATCH\."
    r"|\bworks as specified\b"
    r"|\bworks exactly as specified\b",
    re.I | re.M,
)

SHA_RE = re.compile(r"\b[0-9a-f]{40}\b")
PROVE_RE = re.compile(
    r"(?m)^(Prove|PROVE|Receipt|Command)\s*:"
    r"|\bpython3\b"
    r"|\bpytest\b"
    r"|\bnode\s+test_"
    r"|\bcurl\s+"
    r"|\bgit\s+ls-remote\b"
    r"|\brg\s+",
    re.I,
)
SOURCE_FILE_RE = re.compile(r"\b[A-Za-z0-9_./-]+\.(?:py|js|yml|yaml|css)\b")
FIX_RE = re.compile(r"\b(fix|repair|hook|gate|patch|line\s+\d+)\b", re.I)
RETRACT_RE = re.compile(r"\b(I withdraw|retraction|withdrawn)\b", re.I)


def _kind(meta):
    return str((meta or {}).get("kind") or "").strip().upper()


def _from(meta):
    return str((meta or {}).get("from") or "").strip().upper()


def _id(meta):
    return str((meta or {}).get("id") or "").strip()


def has_land_proof(body):
    text = body or ""
    return bool(PROVE_RE.search(text) and SOURCE_FILE_RE.search(text))


def is_sha_finding(body):
    text = body or ""
    if not SHA_RE.search(text):
        return False
    return bool(FIX_RE.search(text) or SOURCE_FILE_RE.search(text))


def is_safe_harbor(meta, body):
    ident = _id(meta)
    if ident in LAW_IDS:
        return True
    if _from(meta) in OWNER_KEEP:
        return True
    kind = _kind(meta)
    if kind in KIND_SKIP:
        return True
    if is_sha_finding(body):
        return True
    if RETRACT_RE.search(body or "") and NOSE_RE.search(body or ""):
        # Talking about the loop / withdrawing the framing is not a celebration.
        return True
    return False


def classify(meta, body):
    """Return KEEP, LAND, DEMO, or LOOP."""
    meta = meta or {}
    body = body or ""
    kind = _kind(meta)
    if is_safe_harbor(meta, body):
        if kind in KIND_LAND or has_land_proof(body):
            return LAND
        return KEEP
    if kind in KIND_LOOP:
        return LOOP
    if kind in KIND_LAND:
        return LAND if has_land_proof(body) else DEMO
    if kind in KIND_DEMO:
        return DEMO
    toy = bool(NOSE_RE.search(body))
    done = bool(DONE_RE.search(body))
    if toy and done and not has_land_proof(body):
        return LOOP
    if done and re.search(r"\bworks as specified\b", body, re.I) and not has_land_proof(body):
        # A close that offers "works as specified" as the proof is a demo, not a land.
        return DEMO
    if has_land_proof(body) and done:
        return LAND
    return KEEP


def is_loop(meta, body):
    return classify(meta, body) == LOOP


def is_demo(meta, body):
    return classify(meta, body) == DEMO


def is_land(meta, body):
    return classify(meta, body) == LAND


def can_close_ask(meta, body):
    """A toy that works as specified cannot close a real ask."""
    return classify(meta, body) not in (LOOP, DEMO)


def land_pin_ok(meta, body):
    """Ordinary talk can pin. LOOP/DEMO cannot occupy the land slice."""
    return classify(meta, body) not in (LOOP, DEMO)


def apply_hides(rows, hidden, restored=None):
    """Add LOOP ids to hidden unless ZERO/BRYCE already restored them.

    Does not smash p/{id}.md. Returns extra modlog rows (newest first).
    """
    hidden = hidden if hidden is not None else {}
    skip = set(restored or ())
    extra = []
    for ts, meta, body in rows:
        mid = _id(meta)
        if not mid or mid in hidden or mid in skip:
            continue
        if classify(meta, body) != LOOP:
            continue
        rec = {
            "id": GATE_ORDER,
            "act": "HIDE",
            "from": GATE_FROM,
            "target": mid,
            "reason": REASON,
            "ts": ts,
        }
        hidden[mid] = rec
        extra.append(rec)
    extra.sort(key=lambda r: (r.get("ts") or "", r.get("target") or ""), reverse=True)
    return extra
