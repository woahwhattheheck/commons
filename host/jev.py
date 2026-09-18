#!/usr/bin/env python3
"""host/jev.py — TypeSafe Jev (System One) client for Commons swarm decisions.

Jev is a decision model, not a chat model: send `state` plus typed
`questions` (choice / score / noul), get typed answers with calibrated
probabilities and confidence in a single parallel call (~70-500 ms,
$0.042 per MTok input, output unmetered). It never generates strings,
so answers are consumed directly by code — no parsing, no guardrails.

  Docs:  https://docs.typesafe.ai/
  API:   POST https://api.typesafe.ai/v1/systemone
  Model: jev-latest

  python3 host/jev.py --self-test
  python3 host/jev.py --questions-file q.json --state-file post.md
  python3 host/jev.py --questions-file q.json --state - < post.md

Key resolution policy (never printed, never written to the repo):
  1. credvault: Windows Credential Manager generic target
     "commons:typesafe:api-key" then "typesafe/api-key"
     (credential_sources.json naming convention)
  2. env TYPESAFE_API_KEY is a compatibility fallback only when no vaulted
     key exists. If env and vault (or two vault targets) disagree, resolution
     fails closed with KEY_SOURCE_CONFLICT instead of guessing a generation.

NO_KEY is a typed result, not a crash — callers branch on it like any
other answer.
"""
from __future__ import annotations

import argparse
import ctypes
import hmac
import json
import os
import re
import sys
import urllib.error
import urllib.request
from ctypes import wintypes

API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
ENV_KEY = "TYPESAFE_API_KEY"
CREDVAULT_TARGETS = ("commons:typesafe:api-key", "typesafe/api-key")
QUESTION_TYPES = ("choice", "score", "noul")
QUESTION_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
MAX_STATE_BYTES = 256 * 1024
MAX_QUESTIONS = 500


class JevError(Exception):
    """Typed failure. str(self) carries NO_KEY / HTTP_<status> / TRANSPORT / BAD_REPLY."""


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_char)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


_CRED_TYPE_GENERIC = 1


def _cred_read(target: str) -> str:
    """Read a Windows Credential Manager generic credential. Returns '' on miss."""
    if os.name != "nt" or not target:
        return ""
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi32.CredReadW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(CREDENTIALW)),
    ]
    advapi32.CredReadW.restype = wintypes.BOOL
    pcred = ctypes.POINTER(CREDENTIALW)()
    if not advapi32.CredReadW(target, _CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
        return ""
    try:
        blob = ctypes.string_at(
            pcred.contents.CredentialBlob, pcred.contents.CredentialBlobSize
        )
    finally:
        advapi32.CredFree(pcred)
    for enc in ("utf-16-le", "utf-8"):
        try:
            text = blob.decode(enc).rstrip("\x00").strip()
        except UnicodeDecodeError:
            continue
        if text:
            return text
    return ""


def _read_key_sources() -> tuple[str, list[tuple[str, str]]]:
    """Read configured key sources without selecting or exposing a value."""
    env_key = os.environ.get(ENV_KEY, "").strip()
    vault_keys: list[tuple[str, str]] = []
    for target in CREDVAULT_TARGETS:
        try:
            key = _cred_read(target)
        except Exception:
            key = ""
        if key:
            vault_keys.append((target, key))
    return env_key, vault_keys


def _select_key(env_key: str, vault_keys: list[tuple[str, str]]) -> str:
    """Select one credential generation, failing closed on source disagreement."""
    vault_key = vault_keys[0][1] if vault_keys else ""
    if vault_key:
        for _, candidate in vault_keys[1:]:
            if not hmac.compare_digest(vault_key, candidate):
                raise JevError("KEY_SOURCE_CONFLICT")
        if env_key and not hmac.compare_digest(vault_key, env_key):
            raise JevError("KEY_SOURCE_CONFLICT")
        # A vaulted generation is authoritative whenever it exists. If an
        # environment copy also exists it must match byte-for-byte.
        return vault_key
    return env_key


def load_key() -> str:
    """Resolve one TypeSafe API-key generation. Never logs the value."""
    env_key, vault_keys = _read_key_sources()
    return _select_key(env_key, vault_keys)


def key_state() -> str:
    """Report credential source state without exposing credential material."""
    env_key, vault_keys = _read_key_sources()
    try:
        _select_key(env_key, vault_keys)
    except JevError:
        return "KEY_SOURCE_CONFLICT"
    if vault_keys:
        state = "KEY_PRESENT_CREDVAULT:" + vault_keys[0][0]
        if env_key:
            state += "+ENV_MATCH"
        return state
    if env_key:
        return "KEY_PRESENT_ENV"
    return "NO_KEY"


def validate_questions(questions) -> list:
    """Return a list of structural problems; empty list means API-shaped."""
    problems = []
    if not isinstance(questions, dict) or not questions:
        return ["questions must be a non-empty object"]
    if len(questions) > MAX_QUESTIONS:
        problems.append(f"questions exceeds MAX_QUESTIONS={MAX_QUESTIONS}")
    for qkey, q in questions.items():
        if not QUESTION_KEY_RE.match(str(qkey)):
            problems.append(f"bad question key {qkey!r}")
        if not isinstance(q, dict):
            problems.append(f"{qkey}: question must be an object")
            continue
        qtype = q.get("type")
        if qtype not in QUESTION_TYPES:
            problems.append(f"{qkey}: type must be one of {QUESTION_TYPES}")
            continue
        if not str(q.get("instructions") or "").strip():
            problems.append(f"{qkey}: missing instructions")
        criteria = q.get("criteria")
        if qtype == "choice" and not (
            isinstance(criteria, dict) and len(criteria) >= 2
        ):
            problems.append(f"{qkey}: choice needs a criteria object with >=2 options")
        if qtype == "score" and not (
            isinstance(criteria, list) and len(criteria) >= 2
        ):
            problems.append(f"{qkey}: score needs a criteria list with >=2 levels")
    return problems


def systemone(state, questions, model=DEFAULT_MODEL, timeout=60, key=None):
    """One System One call. Returns the decoded API response dict."""
    if not isinstance(state, str) or not state.strip():
        raise JevError("EMPTY_STATE")
    if len(state.encode("utf-8")) > MAX_STATE_BYTES:
        raise JevError("STATE_TOO_LARGE")
    problems = validate_questions(questions)
    if problems:
        raise JevError("BAD_QUESTIONS:" + ";".join(problems[:5]))
    key = key if key is not None else load_key()
    if not key:
        raise JevError("NO_KEY")
    payload = {"state": state, "model": model, "questions": questions}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "User-Agent": "commons-jev/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as err:
        raise JevError(f"HTTP_{err.code}") from None
    except urllib.error.URLError as err:
        raise JevError("TRANSPORT") from None
    except ValueError as err:
        raise JevError("BAD_REPLY") from None
    if not isinstance(data, dict) or "answers" not in data:
        raise JevError("BAD_REPLY")
    return data


def _read_text_arg(value):
    """'-' reads stdin; '@path' reads a file; otherwise the literal string."""
    if value == "-":
        return sys.stdin.read()
    if value.startswith("@"):
        with open(value[1:], encoding="utf-8", errors="replace") as handle:
            return handle.read()
    return value


def self_test() -> dict:
    fixture = {
        "route": {
            "type": "choice",
            "instructions": "Which lane handles this",
            "criteria": {"a": "first lane", "b": "second lane"},
        },
        "urgent": {"type": "noul", "instructions": "Message conveys urgency"},
        "sev": {
            "type": "score",
            "instructions": "Severity",
            "criteria": ["low", "medium", "high"],
        },
    }
    bad = {"x": {"type": "choice", "instructions": "no criteria"}}
    return {
        "validate_ok": validate_questions(fixture) == [],
        "validate_catches_bad": len(validate_questions(bad)) > 0,
        "question_types": list(QUESTION_TYPES),
        "api_url": API_URL,
        "model": DEFAULT_MODEL,
        "key_state": key_state(),
        "credvault_targets": list(CREDVAULT_TARGETS),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="TypeSafe Jev System One client")
    parser.add_argument("--state", help="state text, '-' for stdin, '@path' for file")
    parser.add_argument("--state-file", help="file containing the state")
    parser.add_argument("--questions-file", help="JSON file of typed questions")
    parser.add_argument("--questions", help="inline JSON of typed questions")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        print(json.dumps(self_test(), indent=2))
        return 0

    if args.state_file:
        with open(args.state_file, encoding="utf-8", errors="replace") as handle:
            state = handle.read()
    elif args.state is not None:
        state = _read_text_arg(args.state)
    else:
        print("jev: provide --state or --state-file", file=sys.stderr)
        return 2

    qsrc = args.questions or ""
    if args.questions_file:
        with open(args.questions_file, encoding="utf-8", errors="replace") as handle:
            qsrc = handle.read()
    try:
        questions = json.loads(qsrc)
    except ValueError:
        print("jev: questions are not valid JSON", file=sys.stderr)
        return 2

    try:
        result = systemone(state, questions, model=args.model, timeout=args.timeout)
    except JevError as err:
        code = str(err)
        out = {"error": code}
        if code == "NO_KEY":
            out["message"] = (
                "Set TYPESAFE_API_KEY or store a Windows generic credential at "
                "'commons:typesafe:api-key'. Dashboard: console.typesafe.ai/settings/keys"
            )
        print(json.dumps(out), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
