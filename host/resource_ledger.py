#!/usr/bin/env python3
"""host/resource_ledger.py — cache is not capacity.

Slack 1787637936.134649 (DEMON live compute/connector board):
use live surfaces, do not count cache as capacity, keep a ledger
with evidence timestamp, auth surface, exact safe probe, rate/plan
boundary, assigned backlog, and last receipt.

A Slack utilization report is CLAIMED. Missing instrument is
NOT_LANDED. Calling cache "connected" as capacity is NOT_LANDED.
Hugging Face without a token or CLI is NOT_VERIFIED, not live.
Vercel production deploy is a write; this leftover refuses it.
titan: NOT_WRITTEN.

  python3 host/resource_ledger.py
  python3 host/resource_ledger.py --root .
  python3 host/resource_ledger.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys


DEFAULT_CATALOG = os.path.join("ground", "RESOURCE_LEDGER.json")
SLACK_TS = "1787637936.134649"
REQUIRED_FIELDS = (
    "evidence_ts",
    "auth_surface",
    "exact_safe_probe",
    "rate_plan_boundary",
    "assigned_backlog",
    "last_receipt",
)
CAPACITY_STATES = ("LIVE", "CACHE", "NOT_VERIFIED", "UNMEASURED", "FORBIDDEN")
TESTER_AUTHORITY_NEEDLES = (
    "tester",
    "verifier",
    "review authority",
    "final-qa",
    "final qa",
    "red-team-as-verdict",
)
HF_TOKEN_REL = (
    os.path.join(".huggingface", "token"),
    os.path.join(".cache", "huggingface", "token"),
    os.path.join(".hf", "token"),
)


def load_catalog(text):
    """Parse the resource ledger. Invalid JSON is measured empty."""
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"surfaces": [], "error": "catalog is not JSON"}
    if not isinstance(data, dict):
        return {"surfaces": [], "error": "catalog is not an object"}
    surfaces = []
    seen = set()
    for item in data.get("surfaces") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        row = {"name": name}
        for field in REQUIRED_FIELDS:
            row[field] = str(item.get(field) or "").strip()
        row["capacity"] = str(item.get("capacity") or "").strip().upper()
        row["cache_counted"] = bool(item.get("cache_counted"))
        row["tester_authority"] = bool(item.get("tester_authority"))
        surfaces.append(row)
    return {
        "surfaces": surfaces,
        "slack_ts": str(data.get("slack_ts") or "").strip(),
        "source_id": str(data.get("source_id") or "").strip(),
        "cache_as_capacity": bool(data.get("cache_as_capacity")),
        "production_write": bool(data.get("production_write")),
        "secrets": bool(data.get("secrets")),
        "hands_off": list(data.get("hands_off") or []),
        "titan": str(data.get("titan") or "NOT_WRITTEN").strip() or "NOT_WRITTEN",
    }


def local_probes(home, which=shutil.which):
    """Read-only host facts. No tokens, no network, no account writes."""
    home = os.path.abspath(home or ".")
    token_hits = []
    for rel in HF_TOKEN_REL:
        path = os.path.join(home, rel)
        if os.path.isfile(path):
            token_hits.append(rel)
    mcp_path = os.path.join(home, ".cursor", "mcp.json")
    return {
        "hf_token_files": token_hits,
        "hf_cli": bool(which("huggingface-cli") or which("hf")),
        "grok_exe": bool(which("grok") or which("grok.exe")),
        "claude_cli": bool(which("claude")),
        "vercel_cli": bool(which("vercel")),
        "mcp_exists": os.path.isfile(mcp_path),
    }


def classify_surface(row, probes=None):
    """One surface: LIVE / CACHE / NOT_VERIFIED / UNMEASURED / FORBIDDEN."""
    row = row or {}
    probes = probes or {}
    name = str(row.get("name") or "").strip().lower()
    capacity = str(row.get("capacity") or "").strip().upper()
    missing = [field for field in REQUIRED_FIELDS if not str(row.get(field) or "").strip()]
    if name == "claude":
        backlog = str(row.get("assigned_backlog") or "").lower()
        informational = "informational" in backlog
        tester = any(needle in backlog for needle in TESTER_AUTHORITY_NEEDLES)
        if tester and not informational:
            return {
                "name": name,
                "capacity": "UNMEASURED",
                "missing_fields": missing,
                "tester_authority": True,
                "note": (
                    "Claude assigned_backlog still grants tester/verifier/"
                    "review authority. Informational evidence only. "
                    "Route verification to local/GHA/Codex/Grok/Cursor-Grok."
                ),
            }
        return {
            "name": name,
            "capacity": capacity if capacity in CAPACITY_STATES else "UNMEASURED",
            "missing_fields": missing,
            "tester_authority": False,
            "note": (
                "claude is informational only; not tester/verifier/QA. "
                "Prior Claude verdicts this window stay UNVERIFIED."
            ),
        }
    if name == "huggingface":
        if probes.get("hf_token_files") or probes.get("hf_cli"):
            pass
        elif capacity == "LIVE" or row.get("cache_counted"):
            return {
                "name": name,
                "capacity": "NOT_VERIFIED",
                "missing_fields": missing,
                "note": "huggingface specifically is NOT verified. No token file and no CLI here. Cache is not capacity.",
            }
        return {
            "name": name,
            "capacity": "NOT_VERIFIED",
            "missing_fields": missing,
            "note": "huggingface specifically is NOT verified. Do not call cache connected.",
        }
    if name == "vercel" and row.get("production_write"):
        return {
            "name": name,
            "capacity": "FORBIDDEN",
            "missing_fields": missing,
            "note": "vercel deploy is a production write. Refused without exact scope.",
        }
    if capacity not in CAPACITY_STATES:
        return {
            "name": name,
            "capacity": "UNMEASURED",
            "missing_fields": missing,
            "note": "%s has no measured capacity. Absence was not stillness." % (name or "surface"),
        }
    if row.get("cache_counted") or capacity == "CACHE":
        return {
            "name": name,
            "capacity": "CACHE",
            "missing_fields": missing,
            "note": "%s is cache, not capacity. Do not count it as live." % (name or "surface"),
        }
    return {
        "name": name,
        "capacity": capacity,
        "missing_fields": missing,
        "note": "%s recorded as %s. Required ledger fields must stay filled."
        % (name or "surface", capacity),
    }


def measure_from_rows(facts):
    """Pure census so tests do not need a live connector bus."""
    facts = facts or {}
    probes = facts.get("probes") or {}
    surfaces = []
    for item in facts.get("surfaces") or []:
        surfaces.append(classify_surface(item, probes))
    live = [row["name"] for row in surfaces if row["capacity"] == "LIVE"]
    cache = [row["name"] for row in surfaces if row["capacity"] == "CACHE"]
    not_verified = [row["name"] for row in surfaces if row["capacity"] == "NOT_VERIFIED"]
    missing_fields = any(row.get("missing_fields") for row in surfaces if row["capacity"] == "LIVE")
    hf_live = "huggingface" in live
    tester_authority = any(row.get("tester_authority") for row in surfaces)
    return {
        "measured": True,
        "surfaces": surfaces,
        "live": live,
        "cache": cache,
        "not_verified": not_verified,
        "live_count": len(live),
        "cache_count": len(cache),
        "cache_as_capacity": bool(facts.get("cache_as_capacity")) or hf_live,
        "production_write": bool(facts.get("production_write")),
        "missing_fields": missing_fields,
        "secrets": bool(facts.get("secrets")),
        "probes": {
            "hf_token_files": list(probes.get("hf_token_files") or []),
            "hf_cli": bool(probes.get("hf_cli")),
            "grok_exe": bool(probes.get("grok_exe")),
            "claude_cli": bool(probes.get("claude_cli")),
            "vercel_cli": bool(probes.get("vercel_cli")),
            "mcp_exists": bool(probes.get("mcp_exists")),
        },
        "titan": "NOT_WRITTEN",
        "claude_tester_authority": tester_authority,
    }


def classify(row):
    """Turn a measured ledger into a land-desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "resource ledger not read. Absence was not stillness. "
                "A Slack compute board is not a live probe."
            ),
        }
    if row.get("secrets"):
        return {
            "state": "NOT_LANDED",
            "note": "ledger tried to record secrets. Drop them. Status only.",
        }
    if row.get("production_write"):
        return {
            "state": "NOT_LANDED",
            "note": "production/account/financial write refused without exact scope.",
        }
    if row.get("cache_as_capacity"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "cache was counted as capacity. Hugging Face and the Aug 21 "
                "connected-list are not live. Measure again."
            ),
        }
    if row.get("claude_tester_authority"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "Claude still has tester/verifier/review authority on the "
                "resource ledger. Informational only. Do not assign Claude "
                "a tester role."
            ),
        }
    if row.get("missing_fields"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "LIVE rows are missing evidence_ts / auth_surface / "
                "exact_safe_probe / rate_plan_boundary / assigned_backlog / "
                "last_receipt."
            ),
        }
    if not row.get("live"):
        return {
            "state": "CANDIDATE",
            "note": "ledger measured, but no LIVE surface yet. Cache is still not capacity.",
        }
    return {
        "state": "INTEGRATED",
        "note": (
            "live resource ledger is on this file. Cache is not capacity. "
            "Hugging Face is NOT verified. Forbidden writes skipped. "
            "titan NOT_WRITTEN. Talk is not a land."
        ),
    }


def catalog_from_row(row):
    """Public receipt catalog. Names and states only. No secrets."""
    row = row or {}
    return {
        "slack_ts": SLACK_TS,
        "source_id": "demon-live-compute-board-20260825-01",
        "subject": "LIVE COMPUTE/CONNECTOR BOARD — cache is not capacity",
        "cache_as_capacity": False,
        "production_write": False,
        "secrets": False,
        "titan": "NOT_WRITTEN",
        "live": list(row.get("live") or []),
        "cache": list(row.get("cache") or []),
        "not_verified": list(row.get("not_verified") or []),
        "probes": row.get("probes") or {},
        "hands_off": [
            "vercel production deploy",
            "financial/messaging/account writes",
            "state.vscdb delete/vacuum/repair",
            "cml pr 2108",
            "titan --go",
            "jojo mcp/wake",
            "demon swarm flight recorder",
        ],
    }


def measure_root(root, home=None):
    """Read the catalog plus local probe facts from this host."""
    root = os.path.abspath(root or ".")
    path = os.path.join(root, DEFAULT_CATALOG)
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    catalog = load_catalog(text)
    probes = local_probes(home or os.path.expanduser("~"))
    measured = measure_from_rows(
        {
            "surfaces": catalog.get("surfaces") or [],
            "probes": probes,
            "cache_as_capacity": catalog.get("cache_as_capacity"),
            "production_write": catalog.get("production_write"),
            "secrets": catalog.get("secrets"),
        }
    )
    measured["catalog_path"] = path
    measured["slack_ts"] = catalog.get("slack_ts") or SLACK_TS
    measured["hands_off"] = catalog.get("hands_off") or []
    return measured


def self_test():
    """Stdlib checks. A zero here is a broken leftover."""
    empty = classify({})
    if empty["state"] != "UNMEASURED":
        raise SystemExit("empty ledger must be UNMEASURED")
    secrets = classify({"measured": True, "secrets": True, "live": ["github"]})
    if secrets["state"] != "NOT_LANDED":
        raise SystemExit("secrets must be NOT_LANDED")
    cache = classify({"measured": True, "cache_as_capacity": True, "live": ["github"]})
    if cache["state"] != "NOT_LANDED":
        raise SystemExit("cache-as-capacity must be NOT_LANDED")
    hf = classify_surface({"name": "huggingface", "capacity": "LIVE", "cache_counted": True}, {})
    if hf["capacity"] != "NOT_VERIFIED":
        raise SystemExit("huggingface cache must not become LIVE")
    print("resource_ledger self-test ok")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Live resource ledger. Cache is not capacity.")
    parser.add_argument("--root", default=".", help="commons checkout root")
    parser.add_argument("--home", default="", help="home for local probes (default ~)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    measured = measure_root(args.root, args.home or None)
    verdict = classify(measured)
    out = {
        "state": verdict["state"],
        "note": verdict["note"],
        "live": measured["live"],
        "cache": measured["cache"],
        "not_verified": measured["not_verified"],
        "probes": measured["probes"],
        "titan": measured["titan"],
        "secrets": False,
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if verdict["state"] == "INTEGRATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
