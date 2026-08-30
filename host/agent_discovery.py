#!/usr/bin/env python3
"""Build deterministic public agent-discovery surfaces from one registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "agent-discovery.json"
OUTPUTS = (
    "agents.txt",
    "manifest.json",
    "agent.json",
    "agents.json",
    ".well-known/agent.json",
    ".well-known/agents.json",
    "continuity.json",
)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_registry(path: Path = SOURCE) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("registry must be an object")
    return value


def _public_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"https", "mailto"} and bool(parsed.netloc or parsed.path)


def validate(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if registry.get("schema") != "commons-agent-discovery/v1":
        errors.append("schema")
    identity = registry.get("identity")
    if not isinstance(identity, dict) or not identity.get("name") or not identity.get("description"):
        errors.append("identity")
    for field in ("contact_methods", "capabilities"):
        rows = registry.get(field)
        if not isinstance(rows, list) or not rows:
            errors.append(field)
    for row in registry.get("contact_methods") or []:
        if not isinstance(row, dict):
            errors.append("contact_url")
            continue
        if not _public_url(str(row.get("url") or "")):
            errors.append("contact_url")
        if not isinstance(row.get("preferred"), bool):
            errors.append("contact_methods.$.preferred")
    runtime = registry.get("runtime_signals")
    if not isinstance(runtime, dict):
        if runtime is not None:
            errors.append("runtime_signals")
        runtime = {}
    expected = {
        "discovery_state": "open",
        "runtime_access": "public",
        "source_of_truth": "git-head",
        "claims_require_receipts": True,
    }
    for key, value in expected.items():
        if runtime.get(key) != value:
            errors.append(f"runtime_signals.{key}")
    if not str(runtime.get("runtime_state") or "").strip():
        errors.append("runtime_signals.runtime_state")
    continuity = registry.get("continuity")
    if not isinstance(continuity, dict):
        if continuity is not None:
            errors.append("continuity")
        continuity = {}
    if continuity.get("startup_order") != ["pulse.json", "recent.json", "AGENTS.md", "START.md"]:
        errors.append("continuity.startup_order")
    for field in ("pulse", "recent", "receipts", "instruction"):
        if not str(continuity.get(field) or "").strip():
            errors.append(f"continuity.{field}")
    formats = (registry.get("interoperability") or {}).get("formats") or []
    for output in OUTPUTS:
        if output not in formats:
            errors.append(f"interoperability.formats:{output}")
    return sorted(set(errors))


def agent_card(registry: dict[str, Any]) -> dict[str, Any]:
    identity = registry["identity"]
    skills = [
        {
            "id": row["id"],
            "name": row["id"],
            "description": row["description"],
            "entrypoints": row["entrypoints"],
        }
        for row in registry["capabilities"]
    ]
    return {
        "schema": "commons-agent-card/v1",
        "name": identity["name"],
        "description": identity["description"],
        "url": identity["homepage"],
        "documentationUrl": identity["repository"],
        "provider": {"organization": "Commons", "url": identity["homepage"]},
        "defaultInputModes": ["text", "json"],
        "defaultOutputModes": ["text", "json", "git"],
        "skills": skills,
        "runtime_signals": registry["runtime_signals"],
        "contact_methods": registry["contact_methods"],
        "continuity": registry["continuity"],
    }


def render_agents_txt(registry: dict[str, Any]) -> str:
    identity = registry["identity"]
    lines = [
        "# agents.txt - Commons Agent Discovery",
        "# Deterministic projection of agent-discovery.json",
        "",
        "[Commons]",
        f"name: {identity['name']}",
        f"description: {identity['description']}",
        f"homepage: {identity['homepage']}",
        f"repository: {identity['repository']}",
        f"source_of_truth: {registry['runtime_signals']['source_of_truth']}",
        f"runtime_state: {registry['runtime_signals']['runtime_state']}",
        f"runtime_access: {registry['runtime_signals']['runtime_access']}",
        "",
        "[Capabilities]",
    ]
    for row in registry["capabilities"]:
        lines.append(f"capability: {row['id']} | {row['description']} | {','.join(row['entrypoints'])}")
    lines.extend(("", "[Contact Methods]"))
    for row in registry["contact_methods"]:
        lines.append(f"contact: {row['type']} | preferred={str(row['preferred']).lower()} | {row['url']}")
    lines.extend((
        "",
        "[Continuity]",
        "startup_order: " + ",".join(registry["continuity"]["startup_order"]),
        "pulse: " + registry["continuity"]["pulse"],
        "recent: " + registry["continuity"]["recent"],
        "receipts: " + registry["continuity"]["receipts"],
        "instruction: " + registry["continuity"]["instruction"],
        "",
    ))
    return "\n".join(lines)


def projections(registry: dict[str, Any]) -> dict[str, str]:
    errors = validate(registry)
    if errors:
        raise ValueError("INVALID " + " ".join(errors))
    card = agent_card(registry)
    directory = {
        "schema": "commons-agent-directory/v1",
        "agents": [card],
        "runtime_signals": registry["runtime_signals"],
        "continuity": registry["continuity"],
    }
    return {
        "agents.txt": render_agents_txt(registry),
        "manifest.json": canonical(registry),
        "agent.json": canonical(card),
        "agents.json": canonical(directory),
        ".well-known/agent.json": canonical(card),
        ".well-known/agents.json": canonical(directory),
        "continuity.json": canonical({
            "schema": "commons-continuity-capsule/v1",
            **registry["continuity"],
            "runtime_signals": registry["runtime_signals"],
        }),
    }


def generate(root: Path = ROOT) -> None:
    for relative, content in projections(load_registry(root / "agent-discovery.json")).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check(root: Path = ROOT) -> list[str]:
    expected = projections(load_registry(root / "agent-discovery.json"))
    return [relative for relative, content in expected.items() if not (root / relative).is_file() or (root / relative).read_text(encoding="utf-8") != content]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "generate", "check"), nargs="?", default="check")
    args = parser.parse_args()
    if args.command == "validate":
        errors = validate(load_registry())
        print("VALID" if not errors else "INVALID " + " ".join(errors))
        return 0 if not errors else 1
    if args.command == "generate":
        generate()
        print("GENERATED " + " ".join(OUTPUTS))
        return 0
    stale = check()
    print("CURRENT" if not stale else "STALE " + " ".join(stale))
    return 0 if not stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
