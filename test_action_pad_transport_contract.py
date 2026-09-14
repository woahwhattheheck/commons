#!/usr/bin/env python3
"""Pin the existing Action Pad -> ntfy -> Git -> executor road.

This is a static, network-free contract test. It does not send an action, poll a
relay, create credentials, or add a new admission rule.

Run: python3 test_action_pad_transport_contract.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
passed = 0
failed = 0


def case(name: str, good: bool) -> None:
    global passed, failed
    print(("  PASS  " if good else "  FAIL  ") + name)
    if good:
        passed += 1
    else:
        failed += 1


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    html = read("action.html")
    manifest = json.loads(read("relay-manifest.json"))
    relays = [row["url"].rstrip("/") for row in manifest["relays"]]
    relay_code = read("ntfy_relays.py")
    ingest = read("board_ingest.py")
    executor = read("action_executor.py")
    door = read("ground/ACTION_DOOR.md")
    contract = read("docs/action-pad-ntfy-transport.md")
    outcomes = read("docs/commons-transport-outcomes.md")

    topic_match = re.search(r'^var topic = "([^"]+)";$', html, re.MULTILINE)
    hosts_match = re.search(
        r'^var hosts = \[\n(?P<body>.*?)^\];$', html, re.MULTILINE | re.DOTALL
    )
    html_relays = (
        re.findall(r'"(https://[^"]+)"', hosts_match.group("body"))
        if hosts_match
        else []
    )

    case("relay manifest schema is v1", manifest.get("schema") == "commons-relay-manifest-v1")
    case("relay manifest remains descriptive", manifest.get("participation_effect") == "NONE")
    case("delivery stays sequential first-accept", manifest.get("delivery_policy") == "SEQUENTIAL_FIRST_ACCEPT")
    case("observation polls every relay", manifest.get("observation_policy") == "DIRECT_POLL_EVERY_RELAY")
    case("canonical home remains ntfy.sh", bool(relays) and relays[0] == "https://ntfy.sh")
    case("Action Pad topic matches manifest", bool(topic_match) and topic_match.group(1) == manifest.get("topic"))
    case("Action Pad relay order matches manifest", html_relays == relays)

    case(
        "relay v1 name is local failover state",
        'var relayKey="commons-ntfy-relay-v1"' in html and
        'localStorage.getItem(relayKey)' in html and
        'localStorage.setItem(relayKey,JSON.stringify(s))' in html,
    )
    case(
        "producer posts JSON to selected host and topic",
        'fetch(host+"/"+topic,{method:"POST"' in html and
        'headers:{"Content-Type":"application/json"}' in html and
        'body:JSON.stringify(packet)' in html,
    )

    packet_match = re.search(r"var packet=\{(?P<body>.*?)\};", html, re.DOTALL)
    packet = packet_match.group("body") if packet_match else ""
    required_packet_tokens = (
        'from:action.from||"UNSEATED"',
        'to:"TOOLS"',
        'id:action.id',
        'subject:"COMMONS ACTION "+action.verb',
        'board:"TOOLS"',
        'kind:"ACTION"',
        'act:action.verb',
        'target:action.target',
        'body:body',
    )
    case("canonical Action Pad packet exists", bool(packet_match))
    for token in required_packet_tokens:
        case("packet keeps " + token.split(":", 1)[0], token in packet)

    case(
        "body carries verb target optional circuit and exact payload",
        'var body=action.verb+"\\ntarget: "+action.target' in html and
        'action.circuit' in html and
        'action.payload' in html,
    )
    case(
        "blank verb defaults but nonblank free text remains",
        'verb:(form.elements.verb.value.trim()||"ACTION").toUpperCase()' in html and
        "Every other nonblank verb executes" in door and
        "There is no verb allowlist" in door,
    )
    case(
        "carrier acceptance remains explicitly nonterminal",
        "CARRIER_ACCEPTED" in html and
        "Git durability, execution, and result are still pending" in html,
    )

    case("relay home is the first configured host", "HOME = HOSTS[0]" in relay_code)
    case(
        "relay refuses an inconsistent caller id",
        'payload.get("id") != post_id' in relay_code and
        'raise ValueError("relay event id does not match payload id")' in relay_code,
    )
    case(
        "relay adds origin receipts without replacing the action id",
        'payload["source_host"] = source_host' in relay_code and
        'payload["carrier_origin"] = carrier_origin' in relay_code and
        'chosen["id"] = post_id' in relay_code,
    )

    case("canonical ingest defines ntfy_envelope", "def ntfy_envelope(raw):" in ingest)
    case(
        "canonical ingest parses the ntfy message as an envelope",
        'raw_msg = ev.get("message") or ""' in ingest and
        "payload = json.loads(text)" in ingest and
        'payload.get("from") or payload.get("id") or payload.get("body")' in ingest,
    )
    case(
        "executor requires a durable ACTION record and a nonblank verb",
        'if meta.get("kind", "").upper() != "ACTION":' in executor and
        'verb = meta.get("act", "").strip().upper()' in executor and
        "if not verb:" in executor,
    )
    case("executor code documents no circuit allowlist", "This is not an allowlist" in executor)

    case(
        "contract corrects local-state-key versus packet-protocol language",
        "not currently serialized as a `protocol` field" in contract and
        "localStorage" in contract,
    )
    case(
        "SMTP remains an evidenced boundary rather than a claimed receipt",
        "not a producer in this v1 Action Pad contract" in contract and
        "SMTP acceptance" in contract and
        "same `id`, `kind`, `act`, `target`, and `body`" in contract,
    )
    case(
        "receipt ladder distinguishes carrier Git and execution",
        "CARRIER_ACCEPTED" in contract and
        "Git durable" in contract and
        "Executed" in contract,
    )
    case(
        "transport outcomes index links the contract",
        "[Action Pad ntfy transport contract](action-pad-ntfy-transport.md)" in outcomes,
    )

    print("ACTION PAD TRANSPORT CONTRACT: %d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
